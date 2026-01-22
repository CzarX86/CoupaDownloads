# Tasks: Persistent Worker Pool with Tab-Based Processing

**Input**: Design - [x] T037 CLI argument parsing for worker pool settings
- [x] T038 Fallback logic for worker pool initialization failurecuments from `/specs/005-persistent-worker-pool/`
**Prerequisites**: plan.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

## Execution Flow
```
1. Load plan.md from feature directory → ✅ Python 3.12, Selenium WebDriver >=4.0.0, EXPERIMENTAL/ structure
2. Load design documents → ✅ 5 entities, 2 contract interfaces, integration scenarios
3. Generate tasks by category → Setup, Tests, Core, Integration, Polish
4. Apply task rules → Different files [P], Same file sequential, Tests before implementation (TDD)
5. Number tasks sequentially (T001, T002...) → 42 tasks total
6. Generate dependency graph → Clear phases with prerequisites
7. Create parallel execution examples → 18 parallelizable tasks [P]
8. Validate task completeness → All contracts tested, entities modeled, integration covered
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
**Project Structure**: Single project with EXPERIMENTAL/ submodule
- **Core Implementation**: `EXPERIMENTAL/workers/`, `EXPERIMENTAL/core/`
- **Integration**: `EXPERIMENTAL/integration/`, `src/` (existing)
- **Tests**: `tests/contract/`, `tests/integration/`, `tests/unit/`

## Phase 3.1: Setup
- [x] T001 Create worker pool directory structure in EXPERIMENTAL/workers/
- [x] T002 Install psutil dependency for memory monitoring in pyproject.toml
- [x] T003 [P] Configure pytest fixtures for browser automation testing in tests/conftest.py

## Phase 3.2: Contract Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**
- [x] T004 [P] Contract test PersistentWorkerPool interface in tests/contract/test_pool_interface.py
- [x] T005 [P] Contract test Worker process interface in tests/contract/test_worker_interface.py
- [x] T006 [P] Contract test BrowserSession interface in tests/contract/test_browser_session_interface.py
- [x] T007 [P] Contract test ProfileManager interface in tests/contract/test_profile_manager_interface.py
- [x] T008 [P] Contract test integration points in tests/contract/test_integration_contracts.py

### **Phase 3.3: Enhanced Data Models ✅ COMPLETE**
- [x] T009 [P] Enhanced Worker model with process management in EXPERIMENTAL/workers/models/worker.py
- [x] T010 [P] Enhanced Profile model with corruption detection in EXPERIMENTAL/workers/models/profile.py
- [x] **T011**: Tab model with lifecycle tracking
- [x] **T012**: BrowserSession model with state preservation
- [x] **T013**: POTask model with priority and retry logic
- [x] **T014**: PoolConfig and TaskHandle models

## Phase 3.4: Core Worker Pool Implementation ✅ COMPLETE
- [x] T015 PersistentWorkerPool orchestrator class in EXPERIMENTAL/workers/persistent_pool.py
- [x] T016 Worker process lifecycle management in EXPERIMENTAL/workers/worker_process.py
- [x] T017 BrowserSession tab-based processing in EXPERIMENTAL/workers/browser_session.py
- [x] T018 Enhanced ProfileManager with isolation in EXPERIMENTAL/workers/profile_manager.py
- [x] T019 Enhanced TaskQueue with priority handling in EXPERIMENTAL/workers/task_queue.py
- [x] T020 MemoryMonitor with psutil integration in EXPERIMENTAL/workers/memory_monitor.py
- [x] T021 GracefulShutdown signal handling in EXPERIMENTAL/workers/shutdown_handler.py

## Phase 3.5: Integration Adapters
- [x] T022 [P] CSV to POTask conversion adapter in EXPERIMENTAL/integration/csv_adapter.py
- [x] T023 [P] Result aggregation and reporting in EXPERIMENTAL/integration/result_collector.py
- [x] T024 [P] Progress tracking integration in EXPERIMENTAL/integration/progress_tracker.py
- [x] T025 Core_main.py integration with backward compatibility in EXPERIMENTAL/integration/main_adapter.py
- [x] T026 Configuration enhancement with pool settings in EXPERIMENTAL/integration/config_manager.py
- [x] T027 Error mapping from pool errors to existing codes in EXPERIMENTAL/integration/error_mapper.py

## Phase 3.6: Integration Tests (Based on quickstart scenarios)
- [x] T028 [P] Worker pool lifecycle test (start → process → shutdown) in tests/integration/test_worker_pool_lifecycle.py
- [x] T029 [P] Session persistence test (auth → tabs → cleanup) in tests/integration/test_session_persistence.py
- [x] T030 [P] Error recovery test (crash → restart → redistribute) in tests/integration/test_error_recovery.py
- [x] T031 [P] Memory management test with psutil monitoring in tests/integration/test_memory_management.py
- [x] T032 [P] Tab-based processing test with state preservation in tests/integration/test_tab_processing.py
- [x] T033 [P] Graceful shutdown test with timeout handling in tests/integration/test_graceful_shutdown.py
- [x] T034 [P] Profile isolation test with concurrent workers in tests/integration/test_profile_isolation.py

## Phase 3.7: Core_main.py Enhancement
- [x] T035 Add worker pool option to Core_main.py entry point
- [x] T036 Environment variable configuration for USE_PERSISTENT_POOL
- [x] T037 CLI argument parsing for worker pool settings
- [x] T038 Fallback logic for worker pool initialization failure

## Phase 3.8: Polish & Performance
- [x] T039 [P] Unit tests for worker pool components in tests/unit/test_worker_pool_units.py
- [ ] T040 [P] Performance benchmarking (memory usage <30% overhead) in tests/performance/test_pool_performance.py
- [ ] T041 [P] Update documentation with worker pool usage in docs/worker_pool.md
- [ ] T042 Manual testing scenarios from quickstart.md validation

## Dependencies
```
Setup (T001-T003) → 
Contract Tests (T004-T008) [P] → 
Data Models (T009-T014) [P] → 
Core Implementation (T015-T021) → 
Integration Adapters (T022-T027) [P] → 
Integration Tests (T028-T034) [P] → 
Core_main Enhancement (T035-T038) → 
Polish (T039-T042) [P]
```

## Critical Path Dependencies
- T015 (PersistentWorkerPool) blocks T016-T021
- T016 (WorkerProcess) blocks T017 (BrowserSession)
- T018 (ProfileManager) blocks T034 (Profile isolation test)
- T025 (main_adapter) blocks T035-T038 (Core_main enhancement)

## Parallel Execution Examples

### Phase 3.2: Contract Tests (All Parallel)
```bash
# Launch T004-T008 together:
Task: "Contract test PersistentWorkerPool interface in tests/contract/test_pool_interface.py"
Task: "Contract test Worker process interface in tests/contract/test_worker_interface.py"  
Task: "Contract test BrowserSession interface in tests/contract/test_browser_session_interface.py"
Task: "Contract test ProfileManager interface in tests/contract/test_profile_manager_interface.py"
Task: "Contract test integration points in tests/contract/test_integration_contracts.py"
```

### Phase 3.3: Data Models (All Parallel)
```bash
# Launch T009-T014 together:
Task: "Enhanced Worker model with process management in EXPERIMENTAL/workers/models/worker.py"
Task: "Enhanced Profile model with corruption detection in EXPERIMENTAL/workers/models/profile.py"
Task: "Enhanced Tab model with lifecycle tracking in EXPERIMENTAL/workers/models/tab.py"
Task: "Enhanced BrowserSession model with state preservation in EXPERIMENTAL/workers/models/browser_session.py"
Task: "POTask model with priority and retry logic in EXPERIMENTAL/workers/models/po_task.py"
Task: "PoolConfig and TaskHandle models in EXPERIMENTAL/workers/models/config.py"
```

### Phase 3.5: Integration Adapters (Mostly Parallel)
```bash
# Launch T022-T024, T026-T027 together:
Task: "CSV to POTask conversion adapter in EXPERIMENTAL/integration/csv_adapter.py"
Task: "Result aggregation and reporting in EXPERIMENTAL/integration/result_collector.py"
Task: "Progress tracking integration in EXPERIMENTAL/integration/progress_tracker.py"
Task: "Configuration enhancement with pool settings in EXPERIMENTAL/integration/config_manager.py"
Task: "Error mapping from pool errors to existing codes in EXPERIMENTAL/integration/error_mapper.py"
# T025 (main_adapter) sequential after T015-T021 complete
```

### Phase 3.6: Integration Tests (All Parallel)
```bash
# Launch T028-T034 together:
Task: "Worker pool lifecycle test in tests/integration/test_worker_pool_lifecycle.py"
Task: "Session persistence test in tests/integration/test_session_persistence.py"
Task: "Error recovery test in tests/integration/test_error_recovery.py"
Task: "Memory management test in tests/integration/test_memory_management.py"
Task: "Tab-based processing test in tests/integration/test_tab_processing.py"
Task: "Graceful shutdown test in tests/integration/test_graceful_shutdown.py"
Task: "Profile isolation test in tests/integration/test_profile_isolation.py"
```

## Task Generation Rules Applied

1. **From Contracts**: 2 interface files → 5 contract test tasks (T004-T008) [P]
2. **From Data Model**: 5 entities → 6 model creation tasks (T009-T014) [P]
3. **From Integration Contracts**: Core_main, CSV, Progress → 6 adapter tasks (T022-T027)
4. **From Quickstart Scenarios**: 7 test scenarios → 7 integration tests (T028-T034) [P]

## Validation Checklist ✅
- [x] All contracts have corresponding tests (T004-T008)
- [x] All entities have model tasks (T009-T014)
- [x] All tests come before implementation (Phase 3.2 before 3.3+)
- [x] Parallel tasks truly independent (different files, no dependencies)
- [x] Each task specifies exact file path
- [x] No task modifies same file as another [P] task
- [x] TDD flow: Tests → Models → Implementation → Integration
- [x] EXPERIMENTAL/ structure preserved for core implementation
- [x] Backward compatibility maintained in integration tasks

## Estimated Timeline
- **Total Tasks**: 42 tasks
- **Duration**: 4 weeks (10-12 tasks per week)
- **Critical Path**: 25 sequential tasks
- **Parallel Opportunities**: 17 parallelizable tasks [P]
- **Week 1**: Setup + Contract Tests + Data Models (T001-T014)
- **Week 2**: Core Implementation (T015-T021)
- **Week 3**: Integration Adapters + Tests (T022-T034)
- **Week 4**: Core_main Enhancement + Polish (T035-T042)

## Notes
- All worker pool implementation in EXPERIMENTAL/ subproject
- Integration with existing src/ models and services preserved
- Backward compatibility maintained throughout
- Memory monitoring with psutil integration
- Tab-based processing with session state preservation
- Graceful shutdown with 1-minute timeout
- Profile isolation between workers
- Error recovery and redistribution logic

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: `src/`, `tests/` at repository root (confirmed from plan.md)
- All file paths relative to `/Users/juliocezar/Dev/work/CoupaDownloads/`

## Phase 3.1: Setup & Infrastructure
- [x] T001 Create worker pool directory structure in src/models/, src/services/, src/lib/
- [x] T002 Install additional dependencies: psutil for memory monitoring, typing_extensions if needed
- [x] T003 [P] Configure import structure for persistent worker pool modules in src/__init__.py

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**
- [ ] T004 [P] Contract test for PersistentWorkerPoolInterface in tests/contract/test_worker_pool_interface.py
- [ ] T005 [P] Integration test for basic worker pool initialization in tests/integration/test_worker_lifecycle.py
- [ ] T006 [P] Integration test for PO processing flow in tests/integration/test_po_processing_flow.py
- [ ] T007 [P] Integration test for crash recovery scenarios in tests/integration/test_crash_recovery.py
- [ ] T008 [P] Integration test for graceful shutdown in tests/integration/test_graceful_shutdown.py
- [ ] T009 [P] Integration test for memory management thresholds in tests/integration/test_memory_management.py

## Phase 3.3: Core Models (ONLY after tests are failing)
- [ ] T010 [P] Profile entity model in src/models/profile.py with cloning and validation
- [ ] T011 [P] Tab entity model in src/models/tab.py with lifecycle management
- [ ] T012 [P] BrowserSession entity model in src/models/browser_session.py with WebDriver integration
- [ ] T013 [P] Worker entity model in src/models/worker.py with process management
- [ ] T014 PersistentWorkerPool entity model in src/models/worker_pool.py (depends on Worker)

## Phase 3.4: Core Services
- [ ] T015 [P] ProfileManager service in src/services/profile_manager.py for profile cloning and isolation
- [ ] T016 [P] MemoryMonitor service in src/services/memory_monitor.py for resource tracking
- [ ] T017 [P] TaskQueue service in src/services/task_queue.py for PO distribution
- [ ] T018 SignalHandler implementation in src/lib/signal_handler.py for main process coordination
- [ ] T019 GracefulShutdown coordination in src/lib/graceful_shutdown.py
- [ ] T020 Worker process lifecycle management in src/services/worker_manager.py

## Phase 3.5: Integration & Coordination
- [ ] T021 Worker pool initialization logic connecting all components
- [ ] T022 Tab lifecycle coordination within browser sessions
- [ ] T023 Cascading recovery implementation (restart → redistribute → fail)
- [ ] T024 Memory threshold monitoring and worker restart logic
- [ ] T025 Session state preservation across tab operations
- [ ] T026 Profile corruption detection and abort logic

## Phase 3.6: CLI Integration
- [ ] T027 Update existing CLI configuration in src/cli/worker_config.py for persistent pool options
- [ ] T028 Integration with Core_main.py entry point for worker pool initialization
- [ ] T029 Replace one-shot worker pattern with persistent pool in main processing loop

## Phase 3.7: Polish & Validation
- [ ] T030 [P] Unit tests for ProfileManager in tests/unit/test_profile_manager.py
- [ ] T031 [P] Unit tests for MemoryMonitor in tests/unit/test_memory_monitor.py
- [ ] T032 [P] Unit tests for WorkerPool coordination in tests/unit/test_persistent_worker_pool.py
- [ ] T033 [P] Unit tests for Worker lifecycle in tests/unit/test_worker.py
- [ ] T034 Performance validation: 50% improvement over one-shot workers
- [ ] T035 Memory usage validation: respect 75% threshold limits
- [ ] T036 End-to-end quickstart scenario validation
- [ ] T037 Cleanup temporary profiles and resources on shutdown
- [ ] T038 Update documentation and troubleshooting guides

## Dependencies
**Critical Dependencies (MUST RESPECT)**:
- Tests (T004-T009) MUST complete before any implementation (T010+)
- T014 (WorkerPool) blocks T021-T026 (integration logic)
- T015-T020 (services) block T021-T026 (integration)
- T021-T026 (integration) block T027-T029 (CLI integration)
- T027-T029 (CLI) block T030+ (validation)

**Parallel Safe Groups**:
- T004-T009: All different test files, no dependencies
- T010-T013: All different model files, no cross-dependencies
- T015-T017: Different service files, independent functionality
- T030-T033: Different unit test files, independent validation

## Parallel Execution Examples

### Phase 3.2 - Launch All Tests Together:
```bash
# All contract and integration tests can run in parallel:
Task: "Contract test for PersistentWorkerPoolInterface in tests/contract/test_worker_pool_interface.py"
Task: "Integration test for basic worker pool initialization in tests/integration/test_worker_lifecycle.py"
Task: "Integration test for PO processing flow in tests/integration/test_po_processing_flow.py"
Task: "Integration test for crash recovery scenarios in tests/integration/test_crash_recovery.py"
Task: "Integration test for graceful shutdown in tests/integration/test_graceful_shutdown.py"
Task: "Integration test for memory management thresholds in tests/integration/test_memory_management.py"
```

### Phase 3.3 - Launch Core Models Together:
```bash
# Independent model files can be created in parallel:
Task: "Profile entity model in src/models/profile.py with cloning and validation"
Task: "Tab entity model in src/models/tab.py with lifecycle management"
Task: "BrowserSession entity model in src/models/browser_session.py with WebDriver integration"
Task: "Worker entity model in src/models/worker.py with process management"
# Note: T014 (WorkerPool) must wait for T013 (Worker) to complete
```

### Phase 3.4 - Launch Independent Services:
```bash
# Services with no interdependencies:
Task: "ProfileManager service in src/services/profile_manager.py for profile cloning and isolation"
Task: "MemoryMonitor service in src/services/memory_monitor.py for resource tracking"
Task: "TaskQueue service in src/services/task_queue.py for PO distribution"
```

## Key Implementation Notes

### From Research Decisions:
- Use multiprocessing.Queue for task distribution (T017)
- Use psutil for memory monitoring (T016)  
- Implement tab switching with WebDriver.switch_to.window() (T012, T022)
- Profile cloning using temporary directories (T015)

### From Data Model:
- PersistentWorkerPool manages 1:N Workers (T014)
- Each Worker owns 1:1 BrowserSession (T013, T012)
- BrowserSession manages N:1 Tabs (T012, T011)
- Profile isolation per Worker (T010, T015)

### From Contracts:
- Implement all interface methods in worker_pool_interface.py (T004, T014)
- Support PoolConfiguration dataclass (T014, T027)
- Return ProcessingResult for each PO task (T014, T022)

### From Quickstart Scenarios:
- Test 2-worker initialization (T005)
- Validate tab lifecycle during processing (T006)
- Simulate worker crashes for recovery testing (T007)
- Test Ctrl+C graceful shutdown (T008)
- Monitor memory threshold behavior (T009)

## Validation Checklist
*GATE: Checked by main() before returning*

- [x] All contracts have corresponding tests (T004 covers worker_pool_interface.py)
- [x] All entities have model tasks (T010-T014 cover all 5 entities from data-model.md)
- [x] All tests come before implementation (T004-T009 before T010+)
- [x] Parallel tasks truly independent (verified file paths and dependencies)
- [x] Each task specifies exact file path (all tasks include specific file locations)
- [x] No task modifies same file as another [P] task (verified no conflicts)
- [x] All quickstart scenarios covered (T005-T009 map to 4 test scenarios plus memory management)

## Task Generation Rules Applied

1. **From Contracts**: worker_pool_interface.py → T004 contract test
2. **From Data Model**: 5 entities → T010-T014 model tasks [P where possible]
3. **From Quickstart**: 4 scenarios + memory → T005-T009 integration tests [P]
4. **From Research**: Technology decisions → T015-T020 service tasks
5. **Ordering**: Setup → Tests → Models → Services → Integration → CLI → Polish
6. **Dependencies**: Tests block implementation, models block integration

**Total Tasks**: 38 tasks across 7 phases
**Parallel Opportunities**: 18 tasks marked [P] for concurrent execution
**Critical Path**: T001 → T004-T009 → T014 → T021-T026 → T027-T029 → T036