# Tasks: Fix Headless Mode in EXPERIMENTAL Subproject

**Input**: Design documents from `/specs/001-fix-headless-mode/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/

## Execution Flow (main)
```
1. Load plan.md from feature directory ✓
   → Found: Python 3.12, Selenium WebDriver, EXPERIMENTAL subproject
   → Extract: tech stack, libraries, structure
2. Load optional design documents: ✓
   → data-model.md: Extract entities → model tasks
   → contracts/: Each file → contract test task  
   → research.md: Extract decisions → setup tasks
3. Generate tasks by category: ✓
   → Setup: environment, linting
   → Tests: contract tests, integration tests
   → Core: configuration models, browser manager updates
   → Integration: interactive setup, process workers
   → Polish: unit tests, validation
4. Apply task rules: ✓
   → Different files = mark [P] for parallel
   → Same file = sequential (no [P])
   → Tests before implementation (TDD)
5. Number tasks sequentially (T001, T002...) ✓
6. Generate dependency graph ✓
7. Create parallel execution examples ✓
8. Validate task completeness: ✓
   → All contracts have tests ✓
   → All entities have models ✓
   → All browser points addressed ✓
9. Return: SUCCESS (tasks ready for execution)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
EXPERIMENTAL subproject structure:
- **Core files**: `EXPERIMENTAL/core/main.py`, `EXPERIMENTAL/corelib/browser.py`
- **Tests**: `tests/unit/`, `tests/integration/`, `tests/browser_automation/`
- **Configuration**: `EXPERIMENTAL/corelib/config.py`

## Phase 3.1: Setup
- [x] T001 Verify development environment (Python 3.12, Poetry, Edge browser) and create test directories
- [x] T002 [P] Configure pytest for EXPERIMENTAL subproject testing in tests/pytest.ini
- [x] T003 [P] Set up test fixtures for browser automation in tests/conftest.py

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**
- [x] T004 [P] Contract test BrowserManager.initialize_driver() headless parameter in tests/unit/test_browser_manager_contract.py
- [x] T005 [P] Contract test InteractiveSetup._interactive_setup() headless collection in tests/unit/test_interactive_setup_contract.py  
- [x] T006 [P] Contract test ProcessWorker.process_po_worker() headless config in tests/unit/test_process_worker_contract.py
- [x] T007 [P] Integration test full headless flow (setup → browser → processing) in tests/integration/test_headless_flow.py
- [x] T008 [P] Integration test headless failure handling (retry → prompt → choice) in tests/integration/test_headless_failure_handling.py
- [x] T009 [P] Integration test process pool mode with headless configuration in tests/integration/test_headless_process_pool.py

## Phase 3.3: Core Implementation (ONLY after tests are failing)
- [x] T010 [P] HeadlessConfiguration data model in EXPERIMENTAL/corelib/models.py
- [x] T011 [P] BrowserInstance data model in EXPERIMENTAL/corelib/models.py  
- [x] T012 [P] InteractiveSetupSession data model in EXPERIMENTAL/corelib/models.py
- [x] T013 Update BrowserManager.initialize_driver() to honor headless parameter in EXPERIMENTAL/corelib/browser.py
- [x] T014 Update BrowserManager._create_browser_options() to apply headless arguments in EXPERIMENTAL/corelib/browser.py
- [x] T015 Update BrowserManager.start() method headless parameter propagation in EXPERIMENTAL/corelib/browser.py
- [x] T016 Implement headless retry and user prompt logic in EXPERIMENTAL/corelib/browser.py
- [x] T017 Update interactive setup to collect and pass headless preference in EXPERIMENTAL/core/main.py
- [x] T018 Remove environment variable HEADLESS dependencies in EXPERIMENTAL/corelib/config.py

## Phase 3.4: Integration
- [x] T019 Update MainApp.process_single_po() to pass headless configuration in EXPERIMENTAL/core/main.py
- [x] T020 Update process_po_worker() to receive and use headless configuration in EXPERIMENTAL/core/main.py
- [x] T021 Add headless mode logging and user feedback in EXPERIMENTAL/core/main.py
- [x] T022 Ensure headless configuration propagates to all browser initialization points in EXPERIMENTAL/core/main.py

## Phase 3.5: Polish
- [x] T023 [P] Unit tests for HeadlessConfiguration state transitions in tests/unit/test_headless_configuration.py
- [x] T024 [P] Unit tests for browser option validation in tests/unit/test_browser_options.py
- [x] T025 [P] End-to-end validation tests per quickstart.md scenarios in tests/browser_automation/test_headless_e2e.py
- [x] T026 Performance test: browser initialization < 10 seconds in tests/performance/test_initialization_speed.py
- [x] T027 Update EXPERIMENTAL/docs/ with headless mode configuration guidance
- [x] T028 Remove debugging code and finalize error handling messages

## Dependencies
- Setup (T001-T003) before everything
- Tests (T004-T009) before implementation (T010-T022)
- Data models (T010-T012) before browser manager updates (T013-T016) 
- Browser manager updates (T013-T016) before interactive setup changes (T017-T018)
- Core implementation (T010-T018) before integration (T019-T022)
- All implementation before polish (T023-T028)

## Parallel Example
```
# Launch contract tests together (T004-T006):
Task: "Contract test BrowserManager.initialize_driver() headless parameter in tests/unit/test_browser_manager_contract.py"
Task: "Contract test InteractiveSetup._interactive_setup() headless collection in tests/unit/test_interactive_setup_contract.py"  
Task: "Contract test ProcessWorker.process_po_worker() headless config in tests/unit/test_process_worker_contract.py"

# Launch data models together (T010-T012):
Task: "HeadlessConfiguration data model in EXPERIMENTAL/corelib/models.py"
Task: "BrowserInstance data model in EXPERIMENTAL/corelib/models.py"
Task: "InteractiveSetupSession data model in EXPERIMENTAL/corelib/models.py"
```

## Notes
- [P] tasks = different files, no dependencies
- Verify all tests fail before implementing (TDD principle)
- EXPERIMENTAL/corelib/browser.py changes must be sequential (same file)
- EXPERIMENTAL/core/main.py changes must be sequential (same file)
- Commit after each task completion
- Validate with quickstart.md scenarios after completion

## Task Generation Rules
*Applied during main() execution*

1. **From Contracts**:
   - BrowserManager API → contract test task [P] 
   - Interactive setup → contract test task [P]
   - Process worker → contract test task [P]
   
2. **From Data Model**:
   - HeadlessConfiguration → model creation task [P]
   - BrowserInstance → model creation task [P] 
   - InteractiveSetupSession → model creation task [P]
   
3. **From User Stories**:
   - Headless mode selection → integration test [P]
   - Failure handling → integration test [P]
   - Process pool mode → integration test [P]

4. **Ordering**:
   - Setup → Tests → Models → Browser Manager → Interactive Setup → Integration → Polish
   - Same file dependencies prevent parallel execution

## Validation Checklist
*GATE: Checked by main() before returning*

- [x] All contracts have corresponding tests (T004-T006)
- [x] All entities have model tasks (T010-T012)
- [x] All tests come before implementation (T004-T009 before T010+)
- [x] Parallel tasks truly independent (different files marked [P])
- [x] Each task specifies exact file path
- [x] No task modifies same file as another [P] task
- [x] Browser initialization points covered (T013-T016, T019-T022)
- [x] Quickstart scenarios addressed (T025, T027)
- [x] TDD principle enforced (tests must fail first)