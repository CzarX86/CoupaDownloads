
# Implementation Plan: Persistent Worker Pool with Tab-Based Processing

**Branch**: `005-persistent-worker-pool` | **Date**: September 30, 2025 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-persistent-worker-pool/spec.md`

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
Replace the current per-PO browser instantiation pattern with a persistent worker pool architecture. The system will maintain 1-8 long-lived browser sessions that process POs through tab-based operations, preserving session state and significantly reducing resource consumption. Implementation will be primarily in the EXPERIMENTAL subproject, leveraging existing browser automation infrastructure while introducing centralized state management and graceful shutdown capabilities.

## Technical Context
**Language/Version**: Python 3.12  
**Primary Dependencies**: Selenium WebDriver >=4.0.0, Microsoft Edge browser, multiprocessing, psutil (memory monitoring), structlog (logging)  
**Storage**: File system (browser profiles, temporary downloads, configuration files)  
**Testing**: pytest, integration tests with browser automation  
**Target Platform**: Windows/macOS/Linux desktop environments  
**Project Type**: Single project with EXPERIMENTAL submodule integration  
**Performance Goals**: Process 100+ POs with <30% memory overhead vs sequential, maintain session state across batch runs  
**Constraints**: 75% RAM threshold for worker restarts, 1 minute graceful shutdown timeout, 1-8 worker limit  
**Scale/Scope**: Support batch processing of 100-1000 POs, 1-8 concurrent browser sessions, profile isolation

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**I. Documentation-Driven Development**: ✅ PASS  
- Follows Proposal → Design → Implementation workflow (spec → plan → tasks → implementation)
- No architecture decisions requiring ADRs identified yet (will reassess in Phase 1)
- Documentation maintained in English for technical interfaces

**II. Automation Reliability**: ✅ PASS  
- Implements graceful failure handling (worker restart → redistribute → fail)
- Session state preservation across PO processing cycles
- Graceful shutdown with timeout handling (1 minute max)

**III. Security by Design**: ✅ PASS  
- No credentials involved in worker pool implementation
- Browser profile isolation between workers prevents data conflicts
- Leverages existing EXPERIMENTAL security patterns

**IV. Human-in-the-Loop Validation**: ✅ PASS  
- Worker pool is infrastructure change, no business decision automation
- Maintains existing user experience for configuration choices
- Preserves audit trails through observability levels

**V. Quality Assurance Standards**: ✅ PASS  
- Implementation in Python 3.12 with type hints (existing pattern)
- Integration tests planned for critical browser automation paths
- No breaking changes to public CLI interfaces (maintains existing UX)

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
EXPERIMENTAL/                    # Primary implementation location
├── workers/                     # Worker pool implementation
│   ├── persistent_pool.py      # Main worker pool orchestrator
│   ├── worker_process.py       # Individual worker implementation
│   ├── profile_manager.py      # Enhanced profile management (existing)
│   ├── task_queue.py           # Task distribution (existing, enhanced)
│   └── monitoring.py           # Memory and performance monitoring
├── corelib/                     # Shared browser automation (existing)
│   ├── browser.py              # Browser management utilities
│   ├── downloader.py           # PO download logic
│   └── models.py               # Data models
└── core/                        # Entry points and orchestration
    └── main.py                  # Updated main entry point

src/                            # Integration points
├── models/                     # Data models (if needed for integration)
└── services/                   # Service layer (if needed for integration)

tests/                          # Test structure
├── integration/                # Browser automation integration tests
│   ├── test_worker_pool.py    # Worker pool lifecycle tests
│   ├── test_session_persistence.py  # Session state tests
│   └── test_graceful_shutdown.py    # Shutdown behavior tests
├── unit/                       # Unit tests for components
└── contract/                   # Contract/interface tests
```

**Structure Decision**: Single project with EXPERIMENTAL submodule as primary implementation location. This leverages existing browser automation infrastructure in EXPERIMENTAL/ while maintaining integration points in the main src/ directory. The worker pool will be implemented primarily in EXPERIMENTAL/workers/ with enhanced existing components.

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
Based on the Phase 1 design artifacts (data-model.md, contracts/, quickstart.md), the /tasks command will generate implementation tasks following TDD principles:

1. **Contract Test Tasks** (Priority: P1, Parallelizable [P]):
   - One task per interface contract in `/contracts/`
   - `Task 001-003`: Generate failing contract tests for PersistentWorkerPool, Worker, and BrowserSession interfaces
   - Tests validate method signatures, preconditions, postconditions before implementation exists

2. **Data Model Tasks** (Priority: P1, Sequential dependencies):
   - `Task 004-008`: Create enhanced data models based on data-model.md
   - Worker, Profile, Tab, BrowserSession, POTask entities with validation rules
   - Build on existing src/models/ foundation, extend for worker pool requirements

3. **Core Worker Pool Implementation** (Priority: P2, Sequential):
   - `Task 009-012`: Implement PersistentWorkerPool orchestrator class
   - `Task 013-016`: Implement WorkerProcess with browser session management
   - `Task 017-020`: Implement BrowserSession with tab-based processing
   - Each task targets specific contract test making it pass

4. **Integration Adapter Tasks** (Priority: P2, Some parallelizable [P]):
   - `Task 021-023`: CSV to POTask conversion adapter [P]
   - `Task 024-026`: Result aggregation and reporting [P]
   - `Task 027-029`: Core_main.py integration points with backward compatibility

5. **Integration Test Tasks** (Priority: P3, Based on quickstart scenarios):
   - `Task 030-032`: Worker pool lifecycle tests (start → process → shutdown)
   - `Task 033-035`: Session persistence tests (auth → tabs → cleanup)
   - `Task 036-038`: Error recovery tests (crash → restart → redistribute)
   - `Task 039-041`: Performance and memory tests

**Ordering Strategy**:
- **TDD Flow**: Contract tests → Data models → Implementation → Integration tests
- **Dependency Management**: Models before services, services before orchestrators
- **Parallel Opportunities**: Contract tests can run in parallel [P], integration adapters independent [P]
- **Critical Path**: PersistentWorkerPool → WorkerProcess → BrowserSession → Integration

**Task Dependencies**:
```
Contract Tests (001-003) [P] → 
Data Models (004-008) → 
Worker Pool Core (009-020) → 
Integration Adapters (021-029) [P] → 
Integration Tests (030-041)
```

**Estimated Output**: 
- **Total Tasks**: 40-45 numbered tasks in tasks.md
- **Duration**: 4 weeks (10-12 tasks per week)
- **Critical Path**: ~25 sequential tasks
- **Parallel Opportunities**: ~15-20 parallelizable tasks [P]

**Task Template Structure**:
Each task will follow the standard format:
```markdown
### Task ###: [Brief Description]
**Type**: [Implementation|Test|Integration|Documentation]
**Priority**: [P1|P2|P3] **Parallel**: [Y|N] **Estimated**: [hours]
**Prerequisites**: [Dependencies on other tasks]
**Acceptance Criteria**: [Specific, testable outcomes]
**Implementation Notes**: [Technical guidance and patterns]
```

**Special Considerations**:
- **EXPERIMENTAL Integration**: All worker pool implementation in EXPERIMENTAL/ subproject
- **Backward Compatibility**: Integration tasks ensure existing CLI/config unchanged
- **Constitution Compliance**: Each task validates against quality, security, and human-in-loop principles
- **Error Handling**: Dedicated tasks for graceful degradation patterns
- **Memory Management**: Specific tasks for psutil integration and threshold monitoring

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
- [x] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS (no new violations after Phase 1)
- [x] All NEEDS CLARIFICATION resolved
- [x] No complexity deviations detected

---
*Based on Constitution v2.1.1 - See `/memory/constitution.md`*
