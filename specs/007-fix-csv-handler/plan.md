
# Implementation Plan: Incremental CSV Handler for CoupaDownloads

**Branch**: `007-fix-csv-handler` | **Date**: 2025-10-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/007-fix-csv-handler/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from file system structure or context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Fill the Constitution Check section based on the content of the constitution document.
4. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file (e.g., `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, `GEMINI.md` for Gemini CLI, `QWEN.md` for Qwen Code or `AGENTS.md` for opencode).
7. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary
Implement incremental CSV persistence for CoupaDownloads to prevent data loss during PO processing. The current system only writes results at the end of batch processing, causing total data loss on interruptions. Solution requires immediate write-after-process with concurrent write safety via write queue serialization, automatic backup before sessions, and resume capability by checking STATUS ≠ COMPLETED.

## Technical Context
**Language/Version**: Python 3.12  
**Primary Dependencies**: pandas (CSV manipulation), multiprocessing (worker pools), structlog (structured logging), tenacity (retry logic)  
**Storage**: CSV files (semicolon-delimited, UTF-8 encoding)  
**Testing**: pytest with integration tests for concurrent CSV operations  
**Target Platform**: macOS/Linux desktop (Poetry-managed environment)
**Project Type**: single - Python automation script with worker pool architecture  
**Performance Goals**: <5 seconds per CSV write operation, support up to 10,000 PO records  
**Constraints**: Thread-safe CSV writes, fault tolerance, resume from interruption points  
**Scale/Scope**: Current 446 POs scaling to 10,000 POs, parallel worker processing

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**I. Documentation-Driven Development**: ✅ PASS - Following Proposal → Design → Implementation workflow with ADR for CSV serialization strategy  
**II. Automation Reliability**: ✅ PASS - Implementing resume capability, fault tolerance, and deterministic write operations  
**III. Security by Design**: ✅ PASS - No credentials involved, PII masking in logs, secure file operations  
**IV. Human-in-the-Loop Validation**: ✅ PASS - System provides progress tracking and error reporting for operator oversight  
**V. Quality Assurance Standards**: ✅ PASS - Will follow PEP 8, type hints, pytest coverage for critical CSV operations

## Project Structure

### Documentation (this feature)
```
specs/[###-feature]/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
src/
├── csv/
│   ├── __init__.py
│   ├── handler.py          # CSVHandler class with incremental persistence
│   ├── write_queue.py      # Serialized write queue for concurrent access
│   └── backup.py           # Backup management before sessions
├── worker_pool.py          # Existing worker pool integration
└── Core_main.py            # Main entry point integration

tests/
├── integration/
│   ├── test_csv_concurrent_writes.py
│   ├── test_csv_resume_processing.py
│   └── test_csv_backup_restore.py
└── unit/
    ├── test_csv_handler.py
    ├── test_write_queue.py
    └── test_backup.py

data/
├── input/
│   └── input.csv           # Target CSV file for persistence
└── backup/                 # Automatic backup storage
```

**Structure Decision**: Single project structure extending existing CoupaDownloads architecture. CSV handling will be implemented as a dedicated module under `src/csv/` with integration points to the existing worker pool system and main processing flow.

## Phase 0: Outline & Research
1. **Extract unknowns from Technical Context** above:
   - For each NEEDS CLARIFICATION → research task
   - For each dependency → best practices task
   - For each integration → patterns task

2. **Generate and dispatch research agents**:
   ```
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
   For each technology choice:
     Task: "Find best practices for {tech} in {domain}"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Extract entities from feature spec** → `data-model.md`:
   - Entity name, fields, relationships
   - Validation rules from requirements
   - State transitions if applicable

2. **Generate API contracts** from functional requirements:
   - For each user action → endpoint
   - Use standard REST/GraphQL patterns
   - Output OpenAPI/GraphQL schema to `/contracts/`

3. **Generate contract tests** from contracts:
   - One test file per endpoint
   - Assert request/response schemas
   - Tests must fail (no implementation yet)

4. **Extract test scenarios** from user stories:
   - Each story → integration test scenario
   - Quickstart test = story validation steps

5. **Update agent file incrementally** (O(1) operation):
   - Run `.specify/scripts/bash/update-agent-context.sh copilot`
     **IMPORTANT**: Execute it exactly as specified above. Do not add or remove any arguments.
   - If exists: Add only NEW tech from current plan
   - Preserve manual additions between markers
   - Update recent changes (keep last 3)
   - Keep under 150 lines for token efficiency
   - Output to repository root

**Output**: data-model.md, /contracts/*, failing tests, quickstart.md, agent-specific file

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Generate tasks from contracts/interfaces.py → Create abstract base classes and data models [P]
- Generate tasks from data-model.md → Implement CSVHandler, WriteQueue, BackupManager classes [P] 
- Generate tasks from acceptance scenarios → Create integration tests for concurrent writes, resume processing
- Generate tasks from quickstart.md → Create contract tests and validation scenarios
- Generate implementation tasks for Core_main.py integration

**Ordering Strategy**:
- TDD order: Interface definitions → Contract tests → Implementation → Integration tests
- Dependency order: Data models → CSV handler → Write queue → Worker integration → Main flow integration  
- Mark [P] for parallel execution where files are independent
- Sequential execution for integration tasks that modify existing code

**Specific Task Categories**:
1. **Foundation [P]**: Create data models (ProcessingStatus, CSVRecord, WriteOperation, BackupMetadata)
2. **Core Implementation [P]**: CSVHandler class with pandas integration and validation
3. **Concurrency [Sequential]**: WriteQueue implementation with thread-safe operations
4. **Backup System [P]**: BackupManager with retention policies
5. **Integration [Sequential]**: Worker pool modification, Core_main.py updates
6. **Testing**: Contract tests, concurrent write tests, recovery scenario tests
7. **Documentation**: Update existing docs with CSV handler usage

**Estimated Output**: 18-22 numbered, ordered tasks in tasks.md

**Key Dependencies Identified**:
- CSVHandler must be complete before WriteQueue integration
- WriteQueue must be tested before Worker pool integration  
- Backup system can be developed in parallel with core handler
- Integration tasks must be sequential to avoid merge conflicts

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |


## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [ ] Complexity deviations documented

---
*Based on Constitution v2.1.1 - See `/memory/constitution.md`*
