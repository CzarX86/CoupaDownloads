# Tasks: Tkinter UI Implementation

**Input**: Design documents from `/specs/002-tkinter-ui/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are OPTIONAL for this feature - focusing on implementation with manual testing per user story acceptance criteria.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- GUI components in `src/ui/`
- Core integration in `src/core/`
- CLI integration in `src/cli/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create GUI module structure in src/ui/
- [x] T002 Configure Tkinter dependencies and imports
- [x] T003 [P] Setup basic test structure for GUI components

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 [P] Create ConfigurationSettings dataclass in src/core/config.py
- [x] T005 [P] Create UI State dataclass in src/ui/state.py
- [x] T006 [P] Create StatusMessage dataclass in src/core/status.py
- [x] T007 Implement configuration file handling with secure permissions in src/core/config_handler.py
- [x] T008 Create core system interface stubs in src/core/interfaces.py
- [x] T009 Setup thread-safe communication patterns for GUI-worker coordination

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Configure Download Settings via GUI (Priority: P1) 🎯 MVP

**Goal**: Provide a graphical interface for users to configure download parameters without using command-line options

**Independent Test**: Open GUI, modify configuration values, verify they are saved/loaded correctly - delivers value as configuration tool even without download functionality

### Implementation for User Story 1

- [x] T010 [US1] Create main GUI window class in src/ui/gui.py
- [x] T011 [US1] Implement configuration panel widget in src/ui/config_panel.py
- [x] T012 [US1] Add file/directory browse dialogs in src/ui/dialogs.py
- [x] T013 [US1] Integrate configuration loading/saving with core config handler
- [x] T014 [US1] Add configuration validation and error display in GUI
- [x] T015 [US1] Implement configuration persistence on GUI close

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Start and Stop Downloads from GUI (Priority: P2)

**Goal**: Provide intuitive GUI buttons for starting and stopping download operations

**Independent Test**: Click start/stop buttons and verify button states change appropriately - delivers value as control interface even if downloads don't execute yet

### Implementation for User Story 2

- [x] T016 [US2] Create control panel widget in src/ui/control_panel.py
- [x] T017 [US2] Implement start/stop button logic with state management
- [x] T018 [US2] Add configuration validation before allowing start
- [x] T019 [US2] Integrate with core operation control interfaces
- [x] T020 [US2] Handle operation state transitions and button updates

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Monitor Basic Download Status (Priority: P3)

**Goal**: Display real-time status information about download operations in the GUI

**Independent Test**: Trigger status updates and verify they appear in status bar - delivers value as monitoring interface even with simulated status

### Implementation for User Story 3

- [x] T021 [US3] Create status display widget in src/ui/status_display.py
- [x] T022 [US3] Implement status bar with real-time updates
- [x] T023 [US3] Setup thread-safe status message queue processing
- [x] T024 [US3] Add progress indication and status text formatting
- [x] T025 [US3] Integrate status updates with operation lifecycle

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T026 [P] Add --ui flag integration to existing CLI in src/cli/main.py
- [ ] T027 Implement GUI process isolation and error handling
- [ ] T028 [P] Add cross-platform GUI testing utilities
- [ ] T029 Create GUI launch script and documentation updates
- [ ] T030 Run quickstart.md validation and integration testing

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Builds on US1 but independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - May integrate with US1/US2 but independently testable

### Within Each User Story

- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch GUI component tasks together:
Task: "Create main GUI window class in src/ui/gui.py"
Task: "Implement configuration panel widget in src/ui/config_panel.py"
Task: "Add file/directory browse dialogs in src/ui/dialogs.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify acceptance criteria from spec.md for each story
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence