# Enterprise RPA Integration Plan for GTT Platform

## Executive Summary

This document outlines the comprehensive integration plan for enterprise RPA features into the Voice AI Assistant's GTT (GreaterTouchTool) platform. The integration will leverage the sophisticated automation infrastructure already present in the system, including the custom hotkey system, kernclip-bus message bus, and extensive application databases.

---

## 1. Architecture Decision: Page Structure

### 1.1 Current State Analysis

**Current GTT Page** (`/home/craig/new-projects/voice_ai/src/ui/pages/gtt_page.py`):
- 2039 lines of code
- Contains: Window management, script builder, NLP command bar, voice control
- Already includes basic hotkey registration commands
- Has execution log panel (limited)

### 1.2 Recommended Structure

**DECISION: Hybrid Approach**

| Feature Category | Location | Rationale |
|-----------------|----------|-----------|
| **Script Builder & Execution** | GTT Page (existing) | Core automation workflow, already established |
| **Console Output Panel** | GTT Page (new) | Real-time feedback for script execution |
| **Dry Run Preview** | GTT Page (new) | Part of execution flow |
| **Hotkey Manager UI** | **NEW: `hotkey_manager_page.py`** | Complex UI deserves dedicated space |
| **Key Remapping Interface** | **NEW: `hotkey_manager_page.py`** | Related to hotkey management |
| **Context Awareness Settings** | **NEW: `automation_rules_page.py`** | Complex configuration with multiple dimensions |
| **CRON Job Scheduler** | **NEW: `automation_rules_page.py`** | Time-based automation pairs with context rules |
| **kernclip-bus Integration** | Both GTT + Service Layer | Message bus is infrastructure, used everywhere |
| **Script Library/Repository** | **NEW: `script_library_page.py`** | Centralized script management |

### 1.3 New Files to Create

```
src/ui/pages/
├── gtt_page.py (existing - enhanced)
├── hotkey_manager_page.py (NEW)
├── automation_rules_page.py (NEW)
└── script_library_page.py (NEW)

src/services/
├── hotkey_service.py (NEW)
├── cron_service.py (NEW)
├── context_awareness_service.py (NEW)
├── kernclip_bus_service.py (NEW)
└── script_execution_service.py (NEW)

src/models/
├── hotkey_rule.py (NEW)
├── cron_job.py (NEW)
├── context_rule.py (NEW)
└── automation_script.py (NEW)
```

---

## 2. Feature Breakdown & UI Components

### 2.1 Console Output Panel (GTT Page Enhancement)

**Location**: `src/ui/pages/gtt_page.py` - Right panel, below execution log

**UI Components**:
```python
class ConsoleOutputPanel(QWidget):
    """Real-time console output for GTT command execution"""
    
    Components:
    - QTextEdit (read-only, monospace font)
      * ANSI color code parsing
      * Auto-scroll to bottom
      * Copy to clipboard action
      * Clear console button
      * Filter by level (INFO, ERROR, DEBUG, SUCCESS)
    
    - QToolBar
      * Clear button
      * Save to file button
      * Filter dropdown
      * Word wrap toggle
      * Font size slider
    
    Features:
    - Real-time streaming output
    - Color-coded messages (green=success, red=error, yellow=warning, blue=info)
    - Timestamp prefix for each line
    - Command echo (show what's being executed)
    - Exit code display
    - Execution duration timing
```

**Integration Points**:
- Connect to `script_execution_service.py` via Qt signals/slots
- Use `QProcess` for command execution with `readyReadStandardOutput` and `readyReadStandardError`
- Implement ANSI escape code parser for colored output

**File**: `src/ui/widgets/console_output_panel.py` (NEW)

---

### 2.2 Dry Run Capability

**Location**: `src/ui/pages/gtt_page.py` - Script execution controls

**UI Components**:
```python
class DryRunPreviewDialog(QWidget):
    """Preview script execution before running"""
    
    Components:
    - QTreeWidget (command sequence preview)
      * Shows each command with icon
      * Estimated execution time per command
      * Dependencies highlighted
    
    - QTextEdit (simulation output)
      * What would happen
      * Files that would be created/modified
      * Windows that would be affected
    
    - QPushButton Group
      * "Execute Dry Run" (simulated)
      * "Execute for Real" (actual)
      * "Export Plan" (save as markdown/PDF)
    
    Features:
    - Static analysis of script commands
    - Dependency graph visualization
    - Risk assessment (low/medium/high)
    - Estimated total execution time
    - Rollback plan generation
```

**Service Integration**:
```python
class DryRunService:
    """Analyzes scripts without execution"""
    
    Methods:
    - analyze_script(commands: List[Dict]) -> DryRunReport
    - estimate_duration(commands: List[Dict]) -> timedelta
    - assess_risk(commands: List[Dict]) -> RiskLevel
    - generate_rollback_plan(commands: List[Dict]) -> List[Dict]
```

**File**: `src/services/dry_run_service.py` (NEW)

---

### 2.3 Script Save & Hotkey Binding

**Location**: `src/ui/pages/gtt_page.py` + `src/ui/pages/hotkey_manager_page.py`

**UI Components**:
```python
class ScriptSaveDialog(QWidget):
    """Save script and optionally bind to hotkey"""
    
    Components:
    - LineEdit (script name)
    - QTextEdit (description)
    - QComboBox (category/tags)
    - QCheckBox ("Bind to hotkey")
      - Conditional: Key sequence input
      - Conflict detection warning
    - QCheckBox ("Save to script library")
    - QPushButton (Save & Close)
```

**Service Integration**:
```python
class ScriptLibraryService:
    """Manages script persistence and retrieval"""
    
    Methods:
    - save_script(name: str, commands: List[Dict], metadata: Dict) -> str
    - load_script(script_id: str) -> AutomationScript
    - list_scripts(category: str = None) -> List[AutomationScript]
    - delete_script(script_id: str) -> bool
    - bind_hotkey(script_id: str, key_combo: str) -> bool
```

**Storage Format**:
```json
{
  "id": "uuid",
  "name": "Morning Standup Automation",
  "description": "Opens browser, calendar, and notes for standup",
  "category": "productivity",
  "commands": [
    {"type": "Launch App", "params": {"app_name": "Firefox"}},
    {"type": "Wait", "params": {"duration": 2000}},
    {"type": "Type Text", "params": {"text": "calendar.google.com"}}
  ],
  "metadata": {
    "created": "2026-03-13T10:00:00Z",
    "modified": "2026-03-13T10:00:00Z",
    "author": "craig",
    "version": "1.0.0"
  },
  "hotkey": "Ctrl+Alt+M",
  "context_rules": [],
  "cron_schedule": null
}
```

**File**: `src/services/script_library_service.py` (NEW)

---

### 2.4 Hotkey Manager UI

**Location**: `src/ui/pages/hotkey_manager_page.py` (NEW PAGE)

**UI Components**:
```python
class HotkeyManagerPage(QWidget):
    """Comprehensive hotkey management interface"""
    
    Sections:
    
    1. Hotkey List Panel (Left)
       - QTreeWidget with categories
         * Global hotkeys
         * App-specific hotkeys
         * Context-aware hotkeys
         * System hotkeys
       - Search/filter bar
       - Import/Export buttons
    
    2. Hotkey Editor Panel (Center)
       - QFormLayout for editing:
         * Key sequence input (with recorder)
         * Action type dropdown (script/command/input)
         * Target selection (script path or command)
         * Context rules (app/window filters)
         * Description field
       * Conflict detection (real-time)
       * Test button (try hotkey immediately)
    
    3. Preview & Stats Panel (Right)
       - List of all registered hotkeys
       - Usage statistics (most used, never used)
       - Conflicts visualization
       - Export options (JSON, YAML)
    
    Features:
    - Drag-and-drop reordering
    - Bulk operations (enable/disable/delete)
    - Profile switching (work/personal/gaming)
    - Backup/restore functionality
    - Key conflict detection with system hotkeys
```

**Service Integration**:
```python
class HotkeyService:
    """Manages hotkey registration and lifecycle"""
    
    Methods:
    - register_hotkey(key_combo: str, action: Callable, context: ContextRule) -> bool
    - unregister_hotkey(key_combo: str) -> bool
    - list_hotkeys() -> List[HotkeyRule]
    - test_hotkey(key_combo: str) -> TestResult
    - export_hotkeys(format: str) -> str
    - import_hotkeys(data: str, format: str) -> List[HotkeyRule]
    - detect_conflicts(key_combo: str) -> List[Conflict]
```

**Model**:
```python
@dataclass
class HotkeyRule:
    id: str
    key_combo: str  # e.g., "Ctrl+Alt+T"
    action_type: str  # "script", "command", "input"
    action_target: str  # script path or command string
    description: str
    context_rules: List[ContextRule]
    enabled: bool
    profile: str  # "global", "work", "personal"
    created: datetime
    modified: datetime
```

**File**: `src/services/hotkey_service.py` (NEW)

---

### 2.5 Key Remapping Interface

**Location**: `src/ui/pages/hotkey_manager_page.py` (tab within page)

**UI Components**:
```python
class KeyRemappingTab(QWidget):
    """Key remapping configuration"""
    
    Components:
    - QTableWidget (remapping rules)
      * Source key column (with recorder)
      * Target key column (with recorder)
      * Context column (app-specific)
      * Enable/disable toggle
      * Delete button
    
    - Key Recorder Widget (custom)
      * Visual keyboard display
      * Press key to capture
      * Modifier key visualization (Ctrl/Alt/Shift/Super)
    
    - Profile Manager
      * Create/delete profiles
      * Switch between profiles
      * Import/export profiles
    
    Features:
    - Layer support (multiple remapping layers)
    - App-specific remapping (different in VS Code vs browser)
    - Combo key support (Ctrl+C → Super+X)
    - Macro support (single key → sequence)
    - Passthrough rules (disable remapping for specific keys)
```

**Service Integration**:
```python
class KeyRemappingService:
    """Manages key remapping rules"""
    
    Methods:
    - add_remap(source: str, target: str, context: ContextRule) -> bool
    - remove_remap(source: str) -> bool
    - list_remaps() -> List[RemapRule]
    - apply_profile(profile_name: str) -> bool
    - export_profile(profile_name: str) -> str
```

**File**: `src/services/key_remapping_service.py` (NEW)

---

### 2.6 Context Awareness Settings

**Location**: `src/ui/pages/automation_rules_page.py` (NEW PAGE)

**UI Components**:
```python
class ContextAwarenessPage(QWidget):
    """Configure context-aware automation rules"""
    
    Tabs:
    
    1. App-Specific Rules Tab
       - QTreeWidget (application hierarchy)
       - Rule editor for each app:
         * Enable/disable automation
         * App-specific hotkeys
         * Window title patterns (regex)
         * Time-based activation
    
    2. Window Context Tab
       - Window class filter input
       - Title pattern matching (regex builder)
       - Window state conditions (focused, minimized, etc.)
       - Pin-to-back rules
    
    3. Time-Based Rules Tab
       - Weekly calendar view
       - Time range selectors
       - Date-specific rules (holidays, etc.)
       - Sunrise/sunset triggers
    
    4. Location/Environment Tab (future)
       - Workspace detection
       - Monitor configuration triggers
       - Network-based triggers (WiFi SSID)
    
    Rule Builder Widget:
    - Visual rule composer (drag-and-drop conditions)
    - AND/OR/NOT logic gates
    - Nested condition support
    - Test rule button (evaluate against current state)
```

**Service Integration**:
```python
class ContextAwarenessService:
    """Evaluates and manages context rules"""
    
    Methods:
    - create_rule(name: str, conditions: List[Condition]) -> ContextRule
    - evaluate_rule(rule: ContextRule) -> bool
    - get_active_rules() -> List[ContextRule]
    - test_against_current(rule: ContextRule) -> EvaluationResult
    - import_rules(file_path: str) -> List[ContextRule]
```

**Model**:
```python
@dataclass
class ContextRule:
    id: str
    name: str
    conditions: List[Condition]
    logic_operator: str  # "AND", "OR"
    actions: List[Action]
    priority: int
    enabled: bool
    
@dataclass
class Condition:
    type: str  # "app", "window", "time", "workspace"
    operator: str  # "equals", "contains", "regex", "between"
    value: Any
    negated: bool
```

**File**: `src/services/context_awareness_service.py` (NEW)

---

### 2.7 CRON Job Scheduler

**Location**: `src/ui/pages/automation_rules_page.py` (tab within page)

**UI Components**:
```python
class CronSchedulerTab(QWidget):
    """CRON job management interface"""
    
    Components:
    
    1. Job List Panel (Left)
       - QListWidget with job summaries
       - Filter by status (active, paused, failed)
       - Search by name/script
       - Next run time display
    
    2. Job Editor Panel (Center)
       - QFormLayout:
         * Job name input
         * Script/command selector
         * Schedule type dropdown:
           - One-time (datetime picker)
           - Daily (time picker)
           - Weekly (day + time)
           - Monthly (date + time)
           - Custom CRON (cron expression builder)
         * CRON expression visual builder:
           - 5 row interface (minute, hour, day, month, weekday)
           - Preset buttons (@hourly, @daily, @weekly)
           - Expression preview
         * Context rules (optional)
         * Notification settings
         * Retry policy (on failure)
    
    3. Execution History Panel (Right)
       - QTableWidget (last runs)
         * Timestamp
         * Duration
         * Exit code
         * Output preview
       * Log viewer (click to expand)
       * Re-run button
    
    Features:
    - Visual CRON expression builder
    - Next 10 run times preview
    - Timezone selector
    - Pause/resume individual jobs
    - Manual trigger button
    - Email/notification on failure
    - Dependency between jobs (Job B runs after Job A succeeds)
```

**Service Integration**:
```python
class CronService:
    """Manages scheduled automation jobs"""
    
    Methods:
    - create_job(name: str, schedule: str, script: str, context: ContextRule) -> CronJob
    - delete_job(job_id: str) -> bool
    - pause_job(job_id: str) -> bool
    - resume_job(job_id: str) -> bool
    - trigger_job(job_id: str) -> ExecutionResult
    - list_jobs(status: str = None) -> List[CronJob]
    - get_next_runs(job_id: str, count: int = 10) -> List[datetime]
    - get_execution_history(job_id: str, limit: int = 50) -> List[ExecutionLog]
```

**Model**:
```python
@dataclass
class CronJob:
    id: str
    name: str
    cron_expression: str  # "0 9 * * 1-5"
    script_id: str  # Reference to AutomationScript
    context_rules: List[ContextRule]
    enabled: bool
    timezone: str
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    retry_policy: RetryPolicy
    notification_settings: NotificationSettings
    created: datetime
```

**Implementation Notes**:
- Use `APScheduler` (Advanced Python Scheduler) as backend
- Persist jobs to SQLite database
- Run scheduler in background thread
- Integrate with kernclip-bus for job execution events

**File**: `src/services/cron_service.py` (NEW)

---

### 2.8 kernclip-bus Integration

**Location**: Service layer + GTT Page enhancements

**Architecture**:
```python
class KernclipBusService:
    """High-performance message bus integration"""
    
    Connection:
    - Unix domain socket: /tmp/kernclip-bus.sock
    - Protocol: Custom binary protocol (89k ops/sec capable)
    - Topics: automation, hotkey, cron, context, script
    
    Methods:
    - connect() -> bool
    - disconnect() -> bool
    - publish(topic: str, message: Dict) -> bool
    - subscribe(topic: str, callback: Callable) -> Subscription
    - request_response(topic: str, message: Dict, timeout_ms: int) -> Dict
    
    Events Published:
    - automation.script.started
    - automation.script.completed
    - automation.script.failed
    - hotkey.triggered
    - cron.job.executed
    - context.rule.activated
    - window.focus.changed
    - app.launched
```

**UI Integration Points**:

1. **Console Output Panel**: Subscribe to `automation.*` events for real-time logging
2. **Hotkey Manager**: Subscribe to `hotkey.triggered` for usage statistics
3. **CRON Scheduler**: Publish job execution commands, subscribe to results
4. **Context Awareness**: Subscribe to `window.*` and `app.*` events for state tracking

**Message Format**:
```json
{
  "event": "automation.script.started",
  "timestamp": "2026-03-13T10:00:00.000Z",
  "source": "gtt-page",
  "data": {
    "script_id": "uuid",
    "script_name": "Morning Standup",
    "triggered_by": "hotkey",
    "hotkey": "Ctrl+Alt+M",
    "context": {
      "active_app": "Firefox",
      "window_title": "Google Calendar",
      "workspace": 1
    }
  }
}
```

**File**: `src/services/kernclip_bus_service.py` (NEW)

---

## 3. Implementation Phases

### Phase 1: Foundation (Week 1-2)

**Goal**: Establish service layer and basic infrastructure

**Tasks**:
1. Create service layer directory structure
2. Implement `kernclip_bus_service.py` with basic pub/sub
3. Implement `script_library_service.py` with JSON storage
4. Create data models (`HotkeyRule`, `CronJob`, `ContextRule`, `AutomationScript`)
5. Add console output panel to GTT page
6. Implement dry run service and UI

**Deliverables**:
- Working message bus integration
- Script save/load functionality
- Real-time console output
- Dry run preview dialog

---

### Phase 2: Hotkey Management (Week 3-4)

**Goal**: Complete hotkey manager UI and service

**Tasks**:
1. Create `hotkey_manager_page.py` with full UI
2. Implement `hotkey_service.py` with registration/unregistration
3. Add key recorder widget (visual keyboard)
4. Implement conflict detection system
5. Add profile management (work/personal/gaming)
6. Integrate with existing GTT hotkey commands
7. Add import/export functionality

**Deliverables**:
- Fully functional hotkey manager page
- Key remapping interface
- Profile switching
- Conflict detection and resolution

---

### Phase 3: Context Awareness (Week 5-6)

**Goal**: Implement context-aware automation

**Tasks**:
1. Create `automation_rules_page.py`
2. Implement `context_awareness_service.py`
3. Build visual rule composer UI
4. Add app/window detection integration
5. Implement time-based rules with calendar UI
6. Add rule testing/debugging tools
7. Integrate with GTT daemon for event subscriptions

**Deliverables**:
- Context rule builder
- App-specific automation
- Time-based triggers
- Rule evaluation engine

---

### Phase 4: CRON Scheduler (Week 7-8)

**Goal**: Complete scheduled automation system

**Tasks**:
1. Add CRON tab to `automation_rules_page.py`
2. Implement `cron_service.py` with APScheduler
3. Build visual CRON expression builder
4. Add job execution history UI
5. Implement retry policies and notifications
6. Add job dependency system
7. Integrate with kernclip-bus for job execution

**Deliverables**:
- Full CRON job scheduler
- Visual cron builder
- Execution history and logging
- Notification system

---

### Phase 5: Integration & Polish (Week 9-10)

**Goal**: Tie everything together, testing, documentation

**Tasks**:
1. Cross-feature integration testing
2. Performance optimization (message bus throughput)
3. Error handling and recovery
4. User documentation and tooltips
5. Settings persistence (save all configurations)
6. Backup/restore system
7. Migration path for existing GTT scripts

**Deliverables**:
- Fully integrated RPA platform
- Documentation
- Backup/restore functionality
- Performance benchmarks

---

## 4. Technical Specifications

### 4.1 File Structure

```
/home/craig/new-projects/voice_ai/
├── src/
│   ├── ui/
│   │   ├── pages/
│   │   │   ├── gtt_page.py (enhanced)
│   │   │   ├── hotkey_manager_page.py (NEW)
│   │   │   ├── automation_rules_page.py (NEW)
│   │   │   └── script_library_page.py (NEW)
│   │   └── widgets/
│   │       ├── console_output_panel.py (NEW)
│   │       ├── key_recorder_widget.py (NEW)
│   │       ├── cron_expression_builder.py (NEW)
│   │       ├── rule_composer_widget.py (NEW)
│   │       └── script_tree_widget.py (NEW)
│   ├── services/
│   │   ├── hotkey_service.py (NEW)
│   │   ├── cron_service.py (NEW)
│   │   ├── context_awareness_service.py (NEW)
│   │   ├── kernclip_bus_service.py (NEW)
│   │   ├── script_library_service.py (NEW)
│   │   ├── script_execution_service.py (NEW)
│   │   ├── dry_run_service.py (NEW)
│   │   └── key_remapping_service.py (NEW)
│   └── models/
│       ├── hotkey_rule.py (NEW)
│       ├── cron_job.py (NEW)
│       ├── context_rule.py (NEW)
│       ├── automation_script.py (NEW)
│       └── remap_rule.py (NEW)
├── data/
│   ├── scripts/ (saved automation scripts)
│   ├── hotkey_profiles/ (hotkey configurations)
│   ├── cron_jobs.json (scheduled jobs)
│   └── context_rules.json (context configurations)
└── tests/
    ├── test_hotkey_service.py
    ├── test_cron_service.py
    ├── test_context_awareness.py
    └── test_kernclip_bus.py
```

### 4.2 Dependencies

Add to `requirements.txt`:
```
APScheduler>=3.10.0  # CRON scheduling
croniter>=2.0.0      # CRON expression parsing
pyzmq>=25.0.0        # ZeroMQ for message bus (if needed)
psutil>=5.9.0        # Process and system monitoring
```

### 4.3 Integration with Existing Systems

**GTT Daemon Integration**:
- Use existing `gttuni --daemon` for window management
- Subscribe to GTT events via `sub-window`, `sub-application` topics
- Publish automation events to kernclip-bus

**Settings Manager Integration**:
- Extend `settings_manager.py` to support new RPA settings
- Add methods for saving/loading hotkey profiles, cron jobs, context rules
- Maintain backward compatibility with existing settings

**Main Window Integration**:
- Add new pages to main window tab bar
- Update `main_window.py` to instantiate new pages
- Add navigation between GTT, Hotkey Manager, and Automation Rules

---

## 5. UI Mockups & Wireframes

### 5.1 GTT Page Enhanced Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│  GTT Automation                                                         │
├──────────────┬──────────────────────────┬───────────────────────────────┤
│              │                          │                               │
│ GTT Status   │  Script Builder          │  Console Output Panel (NEW)   │
│ [Running]    │  ┌────────────────────┐  │  ┌─────────────────────────┐  │
│              │  │ Command: [▼]       │  │  │ ▶ Execute  ⏸ Dry Run   │  │
│ Window List  │  │                    │  │  ├─────────────────────────┤  │
│ - Window 1   │  │ Parameters:        │  │  │ [10:00:01] Starting...  │  │
│ - Window 2   │  │ - App: Firefox     │  │  │ [10:00:02] Launching... │  │
│              │  │                    │  │  │ [10:00:03] ✓ Success    │  │
│ Quick Actions│  │ [Add Command]      │  │  │                         │  │
│ [Focus]      │  │                    │  │  └─────────────────────────┘  │
│ [Close]      │  │ Script Commands:   │  │                               │
│ [Maximize]   │  │ 1. Launch Firefox  │  │  Execution Log (existing)     │
│              │  │ 2. Wait 2s         │  │  - Command history            │
│ Macros       │  │ 3. Type URL        │  │  - Error messages             │
│ [Macro 1]    │  │                    │  │                               │
│ [Macro 2]    │  │ [▶ Execute Script] │  │                               │
│              │  │ [💾 Save] [📝 Dry] │  │                               │
└──────────────┴──────────────────────────┴───────────────────────────────┘
```

### 5.2 Hotkey Manager Page

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Hotkey Manager                                                         │
├──────────────┬──────────────────────────┬───────────────────────────────┤
│              │                          │                               │
│ Hotkey List  │  Hotkey Editor           │  Preview & Stats              │
│ (Search)     │                          │                               │
│ ┌──────────┐ │  Name: [Morning Standup]│  Registered Hotkeys: 47       │
│ ▼ Global   │ │                          │                               │
│   Ctrl+M   │ │  Key: [Ctrl+Alt+M] [🎤]│  ┌─────────────────────────┐  │
│   Ctrl+T   │ │                          │  │ Ctrl+M    Morning...  │  │
│            │ │  Action: [▼ Run Script] │  │ Ctrl+T    New Term... │  │
│ ▼ App-Spec │ │                          │  │ Ctrl+Shift+S Screenshot│ │
│   VS Code  │ │  Script: [select...]    │  │                         │  │
│   Firefox  │ │                          │  └─────────────────────────┘  │
│            │ │  Context Rules:          │                               │
│ ▼ Context  │ │  - App: Firefox         │  ⚠️ Conflicts: 0              │
│   Work     │ │  - Time: 9AM-5PM        │  ✓ All hotkeys valid          │
│   Gaming   │ │                          │                               │
│            │ │  [Test] [Save] [Cancel] │  [Export] [Import] [Backup]   │
└──────────────┴──────────────────────────┴───────────────────────────────┘
```

### 5.3 Automation Rules Page

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Automation Rules                                    [+ New Rule]       │
├─────────────────────────────────────────────────────────────────────────┤
│  [Context Rules] [CRON Scheduler] [Key Remapping]                       │
├──────────────┬──────────────────────────┬───────────────────────────────┤
│              │                          │                               │
│ Rule List    │  Rule Editor             │  Preview & Test               │
│              │                          │                               │
│ ✓ Work Hours │  Name: [Work Hours Mode]│  Current Context:              │
│   9AM-5PM    │                          │  - App: Firefox               │
│ ✓ Home App   │  Conditions:             │  - Window: Google Calendar    │
│   Firefox    │  ┌────────────────────┐  │  - Time: 10:30 AM             │
│   Calendar   │  │ IF App = Firefox   │  │  - Workspace: 1               │
│              │  │ AND Time 9AM-5PM   │  │                               │
│ ✗ Disabled   │  │ AND Window contains│  │  Rule Evaluation:             │
│   Gaming     │  │   "Calendar"       │  │  ✓ Condition 1: TRUE          │
│              │  └────────────────────┘  │  ✓ Condition 2: TRUE          │
│              │                          │  ✓ Condition 3: TRUE          │
│              │  Actions:                │                               │
│              │  - Enable hotkeys       │  Result: ✓ RULE ACTIVE         │
│              │  - Run script: standup  │                               │
│              │                          │  [Test Rule] [Save] [Cancel]  │
└──────────────┴──────────────────────────┴───────────────────────────────┘
```

### 5.4 CRON Scheduler Tab

```
┌─────────────────────────────────────────────────────────────────────────┐
│  CRON Scheduler                                       [+ New Job]       │
├──────────────┬──────────────────────────┬───────────────────────────────┤
│              │                          │                               │
│ Job List     │  Job Editor              │  Next Runs & History          │
│ (Search)     │                          │                               │
│ ● Daily      │  Name: [Daily Standup]   │  Next 10 Runs:                │
│   9:00 AM    │                          │  - Mon Mar 16, 9:00 AM        │
│   Active     │  Schedule:               │  - Tue Mar 17, 9:00 AM        │
│              │  ○ One time             │  - Wed Mar 18, 9:00 AM        │
│ ○ Weekly     │  ● Daily at: [09:00]    │                               │
│   Mon 8AM    │  ○ Weekly: [Mon] [08:00]│  Execution History:            │
│   Paused     │  ○ Monthly: [1st] [09:00]│ ┌─────────────────────────┐  │
│              │  ○ Custom CRON           │  │ Mar 13 09:00 ✓ 2.3s    │  │
│ ○ Failed     │                          │  │ Mar 12 09:00 ✓ 2.1s    │  │
│   Backup     │  CRON: [0 9 * * 1-5]     │  │ Mar 11 09:00 ✗ Error   │  │
│              │                          │  │ Mar 10 09:00 ✓ 2.5s    │  │
│              │  Script: [standup.json]  │  └─────────────────────────┘  │
│              │                          │                               │
│              │  Context: [Work Hours]   │  [View Logs] [Re-run]         │
│              │                          │                               │
│              │  [Save] [Test] [Cancel]  │                               │
└──────────────┴──────────────────────────┴───────────────────────────────┘
```

---

## 6. Risk Assessment & Mitigation

### 6.1 Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| kernclip-bus protocol changes | High | Low | Version negotiation, fallback to subprocess |
| GTT daemon API instability | High | Medium | Wrap all calls in try/catch, implement retry logic |
| CRON job execution conflicts | Medium | Medium | Job queue with locking, dependency resolution |
| Hotkey conflicts with system | Medium | High | Pre-registration conflict detection, user warnings |
| Context rule evaluation performance | Low | Medium | Cache evaluations, debounce rapid changes |

### 6.2 User Experience Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| UI complexity overwhelming users | High | Medium | Progressive disclosure, tooltips, documentation |
| Accidental automation execution | High | Low | Dry run required for new scripts, confirmation dialogs |
| Configuration loss | High | Low | Auto-save, backup/restore, version control integration |
| Performance degradation | Medium | Medium | Background threads, lazy loading, pagination |

---

## 7. Testing Strategy

### 7.1 Unit Tests

```python
# tests/test_hotkey_service.py
def test_register_hotkey():
    service = HotkeyService()
    result = service.register_hotkey("Ctrl+Alt+T", lambda: None)
    assert result.success == True

def test_detect_conflict():
    service = HotkeyService()
    service.register_hotkey("Ctrl+Alt+T", lambda: None)
    conflicts = service.detect_conflicts("Ctrl+Alt+T")
    assert len(conflicts) == 1

# tests/test_cron_service.py
def test_create_job():
    service = CronService()
    job = service.create_job("Test", "0 9 * * *", "script.json")
    assert job.next_run is not None

def test_get_next_runs():
    service = CronService()
    runs = service.get_next_runs("job_id", count=10)
    assert len(runs) == 10
```

### 7.2 Integration Tests

```python
# tests/test_kernclip_bus_integration.py
def test_publish_subscribe():
    bus = KernclipBusService()
    bus.connect()
    
    received = []
    def callback(msg): received.append(msg)
    
    bus.subscribe("test.topic", callback)
    bus.publish("test.topic", {"data": "test"})
    
    assert len(received) == 1
    assert received[0]["data"] == "test"
```

### 7.3 UI Tests

```python
# tests/ui/test_hotkey_manager_page.py
def test_hotkey_recorder(qtbot):
    page = HotkeyManagerPage()
    page.show()
    
    # Simulate key press
    qtbot.keyClick(page, Qt.Key_T, Qt.ControlModifier | Qt.AltModifier)
    
    assert page.key_input.text() == "Ctrl+Alt+T"
```

---

## 8. Documentation Requirements

### 8.1 User Documentation

- **Getting Started Guide**: Quick start for basic automation
- **Hotkey Manager Manual**: Complete hotkey configuration guide
- **CRON Scheduler Tutorial**: Scheduling automation examples
- **Context Rules Cookbook**: Common context-aware automation patterns
- **Troubleshooting Guide**: Common issues and solutions

### 8.2 Developer Documentation

- **API Reference**: Service layer API documentation
- **Architecture Overview**: System design and data flow
- **Extension Guide**: How to add new command types
- **Testing Guide**: Running and writing tests

---

## 9. Success Metrics

### 9.1 Functional Metrics

- [ ] All 8 features implemented and functional
- [ ] Console output panel shows real-time execution logs
- [ ] Dry run accurately predicts script behavior
- [ ] Scripts can be saved and bound to hotkeys
- [ ] Hotkey manager can register, edit, delete hotkeys
- [ ] Key remapping works across applications
- [ ] Context rules correctly evaluate conditions
- [ ] CRON jobs execute on schedule
- [ ] kernclip-bus integration handles 1000+ messages/sec

### 9.2 Performance Metrics

- [ ] Hotkey registration < 100ms
- [ ] Context rule evaluation < 50ms
- [ ] CRON job trigger latency < 1 second
- [ ] Console output rendering < 10ms per line
- [ ] Message bus throughput > 10,000 ops/sec

### 9.3 User Experience Metrics

- [ ] New user can create first automation in < 5 minutes
- [ ] Hotkey conflicts detected 100% of the time
- [ ] Zero data loss incidents
- [ ] UI responsive at 60 FPS during automation execution

---

## 10. Appendix: Command Reference

### 10.1 GTT Commands (Existing)

```
Window: focus, close, maximize, minimize, unmaximize, unminimize, activate, move-window, resize-window
Apps: launch
Input: type, key, mouse-move, mouse-click
Clipboard: cb, cb-set, cb-paste
Screenshot/OCR: sc, ocr, ocr-file
Layout: sl, rl, snap
Hotkeys: hotkey-script, hotkey-input, list-hotkeys, clear-hotkeys
Macros: macro-add, macro-remove, macro-list
GNOME: eval, notify, open-file
Vision: vision-scan, vision-map, vision-click
Subscriptions: sub-mouse, sub-window, sub-workspace, sub-application, sub-input, sub-menu, sub-workflow, sub-settings, sub-all
Utility: get-active, list
```

### 10.2 New Commands (Proposed)

```
Script Management:
- script-save <name> <path>
- script-load <name>
- script-list [category]
- script-delete <name>

Hotkey Management:
- hotkey-list --format json
- hotkey-export <path>
- hotkey-import <path>
- hotkey-test <key-combo>

Context Awareness:
- context-evaluate <rule-name>
- context-list --active
- context-test <rule-name>

CRON:
- cron-add <name> <expression> <script>
- cron-list [--status active|paused|failed]
- cron-delete <name>
- cron-trigger <name>
- cron-history <name> [--limit N]

Message Bus:
- bus-publish <topic> <message>
- bus-subscribe <topic> [--duration ms]
- bus-request <topic> <message> [--timeout ms]
```

---

## 11. Next Steps

1. **Review this plan** with stakeholders
2. **Prioritize features** based on user needs
3. **Set up development environment** with new dependencies
4. **Begin Phase 1 implementation** (Foundation)
5. **Weekly check-ins** to review progress and adjust plan

---

**Document Version**: 1.0  
**Created**: 2026-03-13  
**Author**: Enterprise RPA Integration Planning  
**Status**: Ready for Review
