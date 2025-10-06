# Tasks: Incremental CSV Handler for CoupaDownloads

**Input**: Design documents from `/specs/007-fix-csv-handler/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/, quickstart.md

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → Tech stack: Python 3.12, pandas, multiprocessing, structlog, tenacity
   → Structure: Single project with src/csv/ module
2. Load design documents:
   → data-model.md: CSVRecord, ProcessingStatus, WriteOperation, BackupMetadata
   → contracts/interfaces.py: CSVHandlerInterface, WriteQueueInterface, BackupManagerInterface
   → research.md: Write queue serialization, pandas integration, backup strategy
   → quickstart.md: 4 test categories (Basic, Concurrent, Error, Recovery)
3. Generate tasks by category:
   → Setup: CSV module structure, dependencies
   → Tests: Interface tests, integration scenarios 
   → Core: Data models, CSV handler, write queue, backup manager
   → Integration: Worker pool modification, Core_main.py updates
   → Polish: Unit tests, performance validation, documentation
4. Applied task rules:
   → Different files = [P] parallel
   → Same file = sequential
   → Tests before implementation (TDD)
5. Generated 20 numbered tasks (T001-T020)
6. Dependencies: Tests → Models → Core → Integration → Polish
7. SUCCESS: Tasks ready for execution
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
Based on plan.md structure decision: Single project with `src/csv/` module

## Phase 3.1: Setup
- [x] T001 Create CSV module structure: `src/csv/__init__.py`, `src/csv/handler.py`, `src/csv/write_queue.py`, `src/csv/backup.py`
- [x] T002 Create test structure: `tests/unit/csv/`, `tests/integration/csv/` directories
- [x] T003 [P] Add CSV handler imports to `src/csv/__init__.py` for public API

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**
- [ ] T004 [P] Contract test CSVHandlerInterface in `tests/unit/csv/test_csv_handler_interface.py`
- [ ] T005 [P] Contract test WriteQueueInterface in `tests/unit/csv/test_write_queue_interface.py`
- [ ] T006 [P] Contract test BackupManagerInterface in `tests/unit/csv/test_backup_manager_interface.py`
- [ ] T007 [P] Integration test concurrent CSV writes in `tests/integration/csv/test_concurrent_writes.py`
- [ ] T008 [P] Integration test resume processing in `tests/integration/csv/test_resume_processing.py`
- [ ] T009 [P] Integration test backup and restore in `tests/integration/csv/test_backup_restore.py`
- [ ] T010 [P] Integration test error handling in `tests/integration/csv/test_error_handling.py`

## Phase 3.3: Core Implementation (ONLY after tests are failing)
- [ ] T011 [P] ProcessingStatus enum and CSVRecord dataclass in `src/csv/models.py`
- [ ] T012 [P] WriteOperation and BackupMetadata dataclasses in `src/csv/models.py`
- [ ] T013 [P] CSV exception classes in `src/csv/exceptions.py`
- [ ] T014 CSVHandler implementation with pandas integration in `src/csv/handler.py`
- [ ] T015 WriteQueue implementation with thread-safe operations in `src/csv/write_queue.py`
- [ ] T016 BackupManager implementation with retention policy in `src/csv/backup.py`

## Phase 3.4: Integration
- [X] T017 Modify WorkerPool to inject CSVHandler instance in existing `src/worker_pool.py`
- [X] T018 Update Core_main.py to initialize CSV handler and create session backups
- [X] T019 Add CSV handler result callbacks to worker completion logic

## Phase 3.5: Polish
- [X] T020 [P] Performance validation test for 10,000 PO CSV operations in `tests/integration/csv/test_performance.py`

## Dependencies
- Setup (T001-T003) before all other tasks
- Tests (T004-T010) before implementation (T011-T016)
- T011-T012 (models) before T014-T016 (implementations)
- T014 (CSVHandler) before T015 (WriteQueue requires CSVHandler)
- T014-T016 (core) before T017-T019 (integration)
- Integration (T017-T019) before T020 (performance testing)

## Parallel Execution Examples

### Phase 3.1 Setup (can run T003 in parallel)
```bash
# T001 and T002 run sequentially (directory creation)
# T003 can run in parallel after directories exist
Task: "Add CSV handler imports to src/csv/__init__.py for public API"
```

### Phase 3.2 Tests (all parallel - different files)
```bash
# Launch T004-T010 together:
Task: "Contract test CSVHandlerInterface in tests/unit/csv/test_csv_handler_interface.py"
Task: "Contract test WriteQueueInterface in tests/unit/csv/test_write_queue_interface.py" 
Task: "Contract test BackupManagerInterface in tests/unit/csv/test_backup_manager_interface.py"
Task: "Integration test concurrent CSV writes in tests/integration/csv/test_concurrent_writes.py"
Task: "Integration test resume processing in tests/integration/csv/test_resume_processing.py"
Task: "Integration test backup and restore in tests/integration/csv/test_backup_restore.py"
Task: "Integration test error handling in tests/integration/csv/test_error_handling.py"
```

### Phase 3.3 Core Models (parallel then sequential)
```bash
# T011-T013 parallel (different files):
Task: "ProcessingStatus enum and CSVRecord dataclass in src/csv/models.py"
Task: "WriteOperation and BackupMetadata dataclasses in src/csv/models.py" 
Task: "CSV exception classes in src/csv/exceptions.py"

# Then T014-T016 sequential (dependencies):
# T014 first (CSVHandler)
# T015 after T014 (WriteQueue needs CSVHandler)
# T016 parallel with T015 (BackupManager independent)
```

## Task Details

### T001: Create CSV module structure
- Create `src/csv/` directory
- Create empty files: `__init__.py`, `handler.py`, `write_queue.py`, `backup.py`
- Add basic module docstrings

### T004: Contract test CSVHandlerInterface
- Import CSVHandlerInterface from contracts/interfaces.py
- Test all abstract methods with mock implementations
- Verify method signatures match interface
- Test exception handling contracts

### T007: Integration test concurrent CSV writes
- Test 4 workers writing to same CSV simultaneously
- Verify no data corruption or lost writes
- Test write queue serialization under load
- Validate CSV integrity after concurrent operations

### T014: CSVHandler implementation
- Implement CSVHandlerInterface with pandas backend
- Add session backup creation before modifications
- Implement get_pending_records() with STATUS != COMPLETED filtering
- Add update_record() with immediate CSV persistence
- Include CSV validation and progress tracking

### T017: Modify WorkerPool integration
- Add csv_handler parameter to WorkerPool.__init__()
- Inject CSVHandler into worker instances
- Add result callback mechanism for CSV updates
- Maintain backward compatibility for non-CSV usage

### T020: Performance validation test
- Create test CSV with 10,000 PO records
- Measure write operation timing (<5 seconds requirement)
- Test memory usage during large CSV operations
- Validate performance under concurrent worker load

## Notes
- All tests must fail initially (TDD approach)
- CSV operations use semicolon delimiter and UTF-8 encoding
- Write queue prevents concurrent file corruption
- Backup retention set to 5 recent backups
- Integration preserves existing CoupaDownloads workflow

## Validation Checklist
*GATE: Checked before execution*

- [x] All interface contracts have corresponding tests (T004-T006)
- [x] All entities have model tasks (T011-T012) 
- [x] All tests come before implementation (T004-T010 before T011-T016)
- [x] Parallel tasks truly independent (different files, no shared state)
- [x] Each task specifies exact file path
- [x] No task modifies same file as another [P] task
- [x] Dependencies properly sequenced (models → implementations → integration)
- [x] Performance requirements testable (T020)
- [x] Integration maintains existing system compatibility
