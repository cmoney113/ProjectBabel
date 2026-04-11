# Project Modularization & Enhancement Plan (V1)

## 1. Executive Summary
**Objective:** Transition the Voice AI project to a fully modular, service-oriented architecture, resolve state fragmentation, and eliminate legacy components to improve maintainability and performance.

## 2. Codebase Audit Findings

### 2.1 State Fragmentation
- **Issue:** Conversation history is redundantly managed across multiple components: `VoiceAIWorker`, `VoicePipeline`, `VoiceAIPage`, and `ChatSessionManager`.
- **Impact:** Leads to synchronization bugs, inconsistent UI state, and increased complexity when adding context-aware features.
- **Status:** `ConversationContextManager` is implemented but not yet integrated as the primary state handler.

### 2.2 Component Redundancy
- **Issue:** Duplicate implementations exist for core logic:
    - `VoiceProcessor` (legacy) vs `EnhancedVoiceProcessor` (modern, FastAPI-based).
    - `voice_ai_page_original.py` vs `voice_ai_page_enhanced.py`.
- **Impact:** Maintenance overhead and confusion regarding the "current" implementation.

### 2.3 Code Duplication & Tight Coupling
- **Manager Logic:** `TTSManager` and `LLMManager` contain hardcoded model-specific logic, making them brittle and difficult to extend.
- **UI/Logic Coupling:** UI widgets (e.g., `waveform_widget`) are passed directly into processor classes, violating the separation of concerns and making automated testing difficult.

### 2.4 Decommissioned Models
- **Issue:** The `neutts` model has been decommissioned but remains referenced in `src/tts_manager.py`, `src/settings_manager.py`, and `servers/tts_server.py`.

## 3. Implementation Roadmap

### Phase 1: Legacy Removal & Core Cleanup
- **Task 1.1: Decommission `neutts` model.**
    - Remove all code paths and UI elements referencing `neutts-nano`.
    - Update `settings_manager.py` defaults to use supported models (e.g., `kani-tts` or `sopranotts`).
- **Task 1.2: Consolidate Voice Processors.**
    - Unify `EnhancedVoiceProcessor` and `VoiceProcessor` into a single, robust `VoiceProcessor` class.
    - Implement a signal-based interface for UI updates (e.g., waveforms) to remove direct widget dependencies.

### Phase 2: State Centralization
- **Task 2.1: Integrate `ConversationContextManager`.**
    - Set `ConversationContextManager` as the Single Source of Truth (SSOT) for conversation history.
    - Refactor `VoicePipeline` and `VoiceAIWorker` to delegate history management to this component.
    - Clean up redundant history variables in UI controllers.

### Phase 3: Architectural Refactoring
- **Task 3.1: Registry Pattern for Managers.**
    - Refactor `TTSManager` and `LLMManager` to use a dynamic registry for model engines.
    - Move model-specific logic to separate engine files (e.g., `src/tts_engines/kani_engine.py`).
- **Task 3.2: Introduction of `VoiceAIService`.**
    - Create a high-level `VoiceAIService` to manage the ASR -> LLM -> TTS pipeline.
    - Simplify the UI layer by providing a single entry point for voice interaction.

### Phase 4: UI Finalization & Validation
- **Task 4.1: Switch to Enhanced UI.**
    - Make `voice_ai_page_enhanced.py` the default interface.
    - Ensure all user settings and custom voice profiles are correctly mapped to the new architecture.

## 4. Verification & Testing
- **Unit Testing:** Validate `ConversationContextManager` windowing and summarization logic.
- **Integration Testing:** Verify the end-to-end pipeline (ASR -> LLM -> TTS) using the new service layer.
- **Regression Testing:** Ensure legacy features (Project Management, Settings) remain functional after refactoring.
