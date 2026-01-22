# Tasks: Refactor Core Interfaces for UI Integration

**Input**: Design documents from `/specs/001-refactor-core-interfaces/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Unit and integration tests included as required by success criteria

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Paths follow existing project structure

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project structure and basic setup for interface development

- [x] T001 Create src/core/ directory structure
- [x] T002 Create tests/ directory structure for interface tests
- [x] T003 [P] Verify existing EXPERIMENTAL/core/main.py accessibility

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Analyze existing MainApp class structure and interfaces
- [x] T005 [P] Create base interface contracts and type definitions
- [x] T006 Setup test infrastructure for interface testing

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Extract Clean Configuration Interface (Priority: P1) 🎯 MVP

**Goal**: Provide clean configuration management without exposing internal complexity

**Independent Test**: Create ConfigurationManager instance, get/save/validate config, verify persistence works

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T007 [P] [US1] Contract test for ConfigurationManager in tests/test_config_interface.py
- [ ] T008 [P] [US1] Integration test with existing config system in tests/test_config_integration.py

### Implementation for User Story 1

- [x] T009 [US1] Create ConfigurationManager class in src/core/config_interface.py
- [x] T010 [US1] Implement get_config() method with dict serialization
- [x] T011 [US1] Implement save_config() method with validation and persistence
- [x] T012 [US1] Implement validate_config() method with comprehensive error reporting
- [x] T013 [US1] Add configuration file management and default handling

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Extract Processing Control Interface (Priority: P2)

**Goal**: Provide clean start/stop/status operations for processing workflows

**Independent Test**: Create ProcessingController, start processing, check status, stop processing

### Tests for User Story 2 ⚠️

- [x] T014 [P] [US2] Contract test for ProcessingController in tests/test_processing_controller.py
- [x] T015 [P] [US2] Integration test with MainApp processing in tests/test_processing_integration.py

### Implementation for User Story 2

- [x] T016 [US2] Create ProcessingController class in src/core/processing_controller.py
- [x] T017 [US2] Implement start_processing() with session ID generation (UUID4)
- [x] T018 [US2] Implement stop_processing() with graceful shutdown
- [x] T019 [US2] Implement get_status() with comprehensive status reporting
- [x] T020 [US2] Add single-session constraint enforcement
- [x] T021 [US2] Integrate with StatusManager for notifications

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Extract Status Update System (Priority: P3)

**Goal**: Provide real-time status updates through subscription system

**Independent Test**: Subscribe to updates, trigger status changes, verify callbacks execute

### Tests for User Story 3 ⚠️

- [x] T022 [P] [US3] Contract test for StatusManager in tests/test_status_manager.py
- [x] T023 [P] [US3] Integration test with ProcessingController in tests/test_status_integration.py

### Implementation for User Story 3

- [x] T024 [US3] Create StatusManager class in src/core/status_manager.py
- [x] T025 [US3] Implement subscribe_to_updates() with callback registration
- [x] T026 [US3] Implement unsubscribe() with cleanup
- [x] T027 [US3] Add callback failure handling (3-strike unsubscribe rule)
- [x] T028 [US3] Implement notify_status_update() with thread safety
- [x] T029 [US3] Add status update formatting and event types

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Integration & Validation

**Purpose**: Cross-interface integration and comprehensive validation

- [x] T030 [P] Integration test all three interfaces together
- [ ] T031 [P] Backward compatibility verification with existing CLI
- [ ] T032 Performance testing against success criteria (<100ms config, <50ms status)
- [ ] T033 Thread safety validation for UI integration
- [ ] T034 Documentation updates and quickstart validation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User stories can proceed in parallel (P1 → P2 → P3 priority order recommended)
- **Integration (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational - May use US1 ConfigurationManager
- **User Story 3 (P3)**: Can start after Foundational - May integrate with US2 ProcessingController

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Interface class creation before method implementation
- Core functionality before integration features
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel
- Once Foundational completes, user stories can start in parallel
- All tests for a story marked [P] can run in parallel
- Different interface methods can be implemented in parallel

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1 (ConfigurationManager)
4. **STOP and VALIDATE**: Test configuration interface independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test ConfigurationManager → Validate
3. Add User Story 2 → Test ProcessingController → Validate
4. Add User Story 3 → Test StatusManager → Validate
5. Integration testing → Final validation

### Parallel Development Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once ready:
   - Developer A: ConfigurationManager (US1)
   - Developer B: ProcessingController (US2)
   - Developer C: StatusManager (US3)
3. Stories complete and integrate independently

---

## Success Criteria Validation

- **SC-001**: Interfaces import <1s (validate during Phase 1)
- **SC-002**: ConfigurationManager operations <100ms (test in T007)
- **SC-003**: ProcessingController maintains CLI compatibility (test in T015)
- **SC-004**: StatusManager updates <50ms (test in T022)
- **SC-005**: Built-in types only (validate in all tests)

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Maintain zero functional changes to existing codebase