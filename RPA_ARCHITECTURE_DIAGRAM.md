# Enterprise RPA Architecture Diagram

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Voice AI Assistant                                   │
│                         (Main Window)                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │   Voice AI   │  │     GTT      │  │   Hotkey     │  │  Automation  │   │
│  │    Page      │  │    Page      │  │   Manager    │  │    Rules     │   │
│  │              │  │  (Enhanced)  │  │    Page      │  │    Page      │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
│         │                 │                 │                 │            │
│         └─────────────────┴────────┬────────┴─────────────────┘            │
│                                    │                                        │
│                          ┌─────────▼─────────┐                             │
│                          │   UI Widgets      │                             │
│                          │                   │                             │
│                          │ - ConsoleOutput   │                             │
│                          │ - KeyRecorder     │                             │
│                          │ - CronBuilder     │                             │
│                          │ - RuleComposer    │                             │
│                          └─────────┬─────────┘                             │
│                                    │                                        │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Service Layer                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐          │
│  │  ScriptExecution │  │   HotkeyService  │  │  ContextAwareness│          │
│  │     Service      │  │                  │  │     Service      │          │
│  │                  │  │  - register()    │  │                  │          │
│  │  - execute()     │  │  - unregister()  │  │  - create_rule() │          │
│  │  - dry_run()     │  │  - list()        │  │  - evaluate()    │          │
│  │  - cancel()      │  │  - test()        │  │  - test()        │          │
│  └─────────┬────────┘  └─────────┬────────┘  └─────────┬────────┘          │
│            │                     │                     │                    │
│  ┌─────────▼────────┐  ┌────────▼─────────┐  ┌────────▼────────┐          │
│  │ ScriptLibrary    │  │ KeyRemapping     │  │   CronService   │          │
│  │    Service       │  │    Service       │  │                 │          │
│  │                  │  │                  │  │  - create_job() │          │
│  │  - save()        │  │  - add_remap()   │  │  - delete_job() │          │
│  │  - load()        │  │  - remove_remap()│  │  - pause()      │          │
│  │  - list()        │  │  - list()        │  │  - trigger()    │          │
│  │  - delete()      │  │  - export()      │  │  - history()    │          │
│  └─────────┬────────┘  └──────────────────┘  └─────────┬───────┘          │
│            │                                           │                    │
│            └───────────────────┬───────────────────────┘                    │
│                                │                                            │
│                  ┌─────────────▼──────────────┐                            │
│                  │   KernclipBusService       │                            │
│                  │   (Message Bus)            │                            │
│                  │                            │                            │
│                  │  - connect()               │                            │
│                  │  - publish(topic, msg)     │                            │
│                  │  - subscribe(topic, cb)    │                            │
│                  │  - request_response()      │                            │
│                  └─────────────┬──────────────┘                            │
│                                │                                            │
└────────────────────────────────┼────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Data Layer                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐          │
│  │  data/scripts/   │  │data/hotkey_      │  │  data/cron_      │          │
│  │  (JSON files)    │  │profiles/         │  │  jobs.json       │          │
│  │                  │  │(JSON files)      │  │                  │          │
│  │  - script1.json  │  │  - work.json     │  │                  │          │
│  │  - script2.json  │  │  - personal.json │  │                  │          │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘          │
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐                                │
│  │data/context_     │  │  settings.json   │                                │
│  │rules.json        │  │  (existing)      │                                │
│  │                  │  │                  │                                │
│  │                  │  │  + RPA settings  │                                │
│  └──────────────────┘  └──────────────────┘                                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      External Systems                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  GTT Daemon  │  │  kernclip-   │  │   System     │  │    Apps &    │   │
│  │  (gttuni)    │  │  busd        │  │   Events     │  │   Windows    │   │
│  │              │  │              │  │              │  │              │   │
│  │  - Window    │  │  - Pub/Sub   │  │  - Time      │  │  - Focus     │   │
│  │    Mgmt      │  │  - 89k/s     │  │  - Schedule  │  │  - Launch    │   │
│  │  - Hotkeys   │  │  - Events    │  │  - Triggers  │  │  - Input     │   │
│  │  - Input     │  │              │  │              │  │              │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow: Script Execution

```
┌─────────────┐
│   User      │
│  Clicks     │
│  "Execute"  │
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│                      GTT Page                                     │
│                                                                   │
│  1. Get script commands from script_list_widget                  │
│  2. Call script_execution_service.execute(commands)              │
│  3. Connect output_signal to console_panel.append_output()       │
└──────┬───────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│                 ScriptExecutionService                            │
│                                                                   │
│  1. For each command in script:                                  │
│     a. Build GTT command (e.g., ["gtt", "--focus", "Firefox"])   │
│     b. Execute via QProcess                                      │
│     c. Capture stdout/stderr                                     │
│     d. Emit output_signal(line)                                  │
│  2. On completion:                                               │
│     a. Emit completion_signal(success, duration)                 │
│     b. Publish to kernclip-bus: automation.script.completed      │
└──────┬───────────────────────────────────────────────────────────┘
       │
       ├─────────────────────────┐
       │                         │
       ▼                         ▼
┌──────────────┐        ┌──────────────────┐
│ ConsoleOutput│        │  KernclipBus     │
│   Panel      │        │    Service       │
│              │        │                  │
│ [10:00:01]   │        │ Publish:         │
│ Starting...  │        │ automation.      │
│ [10:00:02]   │        │ script.completed │
│ Launching... │        │ {                │
│ [10:00:03]   │        │   "script_id":   │
│ ✓ Success    │        │   "uuid",        │
│              │        │   "duration": 3  │
│ Execution    │        │ }                │
│ time: 3.2s   │        │                  │
└──────────────┘        └──────────────────┘
```

## Data Flow: Hotkey Registration

```
┌─────────────┐
│   User      │
│  Enters     │
│  Ctrl+Alt+M │
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│                  HotkeyManagerPage                                │
│                                                                   │
│  1. User presses keys in KeyRecorderWidget                       │
│  2. Widget displays "Ctrl+Alt+M"                                 │
│  3. User selects action: "Run Script" → "morning_standup.json"   │
│  4. User clicks "Save"                                           │
│  5. Call hotkey_service.register_hotkey()                        │
└──────┬───────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│                   HotkeyService                                   │
│                                                                   │
│  1. Check for conflicts: detect_conflicts("Ctrl+Alt+M")          │
│  2. If conflict: return error                                    │
│  3. If clear:                                                    │
│     a. Create HotkeyRule object                                  │
│     b. Register with system (via GTT)                            │
│     c. Save to hotkey_profiles/current.json                      │
│     d. Publish to kernclip-bus: hotkey.registered                │
└──────┬───────────────────────────────────────────────────────────┘
       │
       ├─────────────────────────┐
       │                         │
       ▼                         ▼
┌──────────────┐        ┌──────────────────┐
│ Hotkey List  │        │  KernclipBus     │
│   Widget     │        │    Service       │
│              │        │                  │
│ Updated with │        │ Publish:         │
│ new hotkey   │        │ hotkey.registered│
│              │        │ {                │
│ Ctrl+Alt+M   │        │   "key":         │
│ → Morning    │        │   "Ctrl+Alt+M",  │
│   Standup    │        │   "action":      │
│              │        │   "script"       │
│              │        │ }                │
└──────────────┘        └──────────────────┘
```

## Data Flow: CRON Job Execution

```
┌──────────────────────────────────────────────────────────────────┐
│                    APScheduler (Background Thread)                │
│                                                                   │
│  1. Runs continuously, checking job schedules                    │
│  2. At 9:00 AM, triggers "Daily Standup" job                     │
│  3. Calls cron_service.execute_job(job_id)                       │
└──────┬───────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│                    CronService                                    │
│                                                                   │
│  1. Get job details from cron_jobs.json                          │
│  2. Evaluate context rules (if any)                              │
│  3. If context active:                                           │
│     a. Load script from script_library                           │
│     b. Call script_execution_service.execute()                   │
│     c. Record execution result                                   │
│     d. Update last_run, next_run                                 │
│     e. Save to cron_jobs.json                                    │
│     f. Publish to kernclip-bus: cron.job.executed                │
└──────┬───────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│                 ScriptExecutionService                            │
│                                                                   │
│  (Same flow as manual script execution)                          │
└──────┬───────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│                  KernclipBusService                               │
│                                                                   │
│  Publishes events:                                               │
│  - cron.job.started                                              │
│  - automation.script.started                                     │
│  - automation.script.completed                                   │
│  - cron.job.completed                                            │
└──────┬───────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│                   Subscribers                                    │
│                                                                   │
│  - ConsoleOutputPanel: Shows execution logs                      │
│  - AutomationRulesPage: Updates job history                      │
│  - NotificationService: Sends user notification                  │
└──────────────────────────────────────────────────────────────────┘
```

## Event Flow: Context Rule Evaluation

```
┌──────────────────────────────────────────────────────────────────┐
│                  GTT Daemon (gttuni)                              │
│                                                                   │
│  Window focus changes from VS Code to Firefox                    │
│  Publishes event: window.focus.changed                           │
└──────┬───────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│                 KernclipBusService                                │
│                                                                   │
│  Subscribed to: window.*                                         │
│  Receives event and forwards to:                                 │
│  - context_awareness_service                                     │
└──────┬───────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│               ContextAwarenessService                             │
│                                                                   │
│  1. Get all active context rules                                 │
│  2. For each rule:                                               │
│     a. Evaluate conditions against new state                     │
│        - App condition: Firefox ✓                                │
│        - Time condition: 9AM-5PM ✓                               │
│        - Window condition: contains "Calendar" ✓                 │
│     b. If rule activates:                                        │
│        - Execute associated actions                              │
│        - Enable hotkey profile: "work"                           │
│        - Trigger script: "morning_standup"                       │
│     c. Publish: context.rule.activated                           │
└──────┬───────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│                   Subscribers                                    │
│                                                                   │
│  - HotkeyService: Switches to "work" profile                     │
│  - ScriptLibrary: Executes "morning_standup" script              │
│  - AutomationRulesPage: Updates UI to show active rules          │
└──────────────────────────────────────────────────────────────────┘
```

## Component Interactions Matrix

```
┌─────────────────────┬──────┬──────┬──────┬──────┬──────┬──────┐
│                     │ GTT  │ Hotkey│ Auto │Script│Kerncl│ Data │
│                     │ Page │ Mgr  │ Rules│ Lib  │  ip   │      │
├─────────────────────┼──────┼──────┼──────┼──────┼──────┼──────┤
│ GTT Page            │  -   │  ✓   │  ✓   │  ✓   │  ✓   │  ✓   │
├─────────────────────┼──────┼──────┼──────┼──────┼──────┼──────┤
│ Hotkey Manager      │  ✓   │  -   │  ✓   │  ✓   │  ✓   │  ✓   │
├─────────────────────┼──────┼──────┼──────┼──────┼──────┼──────┤
│ Automation Rules    │  ✓   │  ✓   │  -   │  ✓   │  ✓   │  ✓   │
├─────────────────────┼──────┼──────┼──────┼──────┼──────┼──────┤
│ Script Library      │  ✓   │  ✓   │  ✓   │  -   │  ✓   │  ✓   │
├─────────────────────┼──────┼──────┼──────┼──────┼──────┼──────┤
│ KernclipBus         │  ✓   │  ✓   │  ✓   │  ✓   │  -   │  ✓   │
├─────────────────────┼──────┼──────┼──────┼──────┼──────┼──────┤
│ Data Layer          │  ✓   │  ✓   │  ✓   │  ✓   │  ✓   │  -   │
└─────────────────────┴──────┴──────┴──────┴──────┴──────┴──────┘

✓ = Direct interaction
```

## Message Bus Topics

```
kernclip-bus Topics:

automation.*
  - automation.script.started
  - automation.script.completed
  - automation.script.failed
  - automation.script.cancelled

hotkey.*
  - hotkey.registered
  - hotkey.unregistered
  - hotkey.triggered
  - hotkey.conflict

cron.*
  - cron.job.created
  - cron.job.deleted
  - cron.job.started
  - cron.job.completed
  - cron.job.failed

context.*
  - context.rule.created
  - context.rule.activated
  - context.rule.deactivated
  - context.rule.evaluated

window.*
  - window.focus.changed
  - window.created
  - window.destroyed
  - window.title.changed

app.*
  - app.launched
  - app.terminated
  - app.focused
```

## Thread Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                      Main Thread (UI)                             │
│                                                                   │
│  - All Qt widgets                                                │
│  - Event loop (QApplication.exec())                              │
│  - Signal/slot connections                                       │
│  - User input handling                                           │
└───────────────────────────────────────────────────────────────────┘
       │
       │ Qt Signals/Slots (thread-safe)
       ▼
┌──────────────────────────────────────────────────────────────────┐
│                   Background Threads                              │
│                                                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ ScriptExecution │  │  CronService    │  │  KernclipBus    │  │
│  │    Thread       │  │  (APScheduler)  │  │  Listener       │  │
│  │                 │  │                 │  │                 │  │
│  │ Runs scripts    │  │ Checks job      │  │ Listens for     │  │
│  │ asynchronously  │  │ schedules       │  │ bus events      │  │
│  │                 │  │                 │  │                 │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└───────────────────────────────────────────────────────────────────┘
```

---

**Document Version**: 1.0  
**Created**: 2026-03-13  
**Purpose**: Visual architecture reference for implementation
