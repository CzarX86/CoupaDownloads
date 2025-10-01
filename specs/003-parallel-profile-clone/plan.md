
# Implementation Plan: Parallel Default Profile Loading & Cloning for Multiple Windows

**Branch**: `003-parallel-profile-clone` | **Date**: 2025-09-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-parallel-profile-clone/spec.md`

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
Fix parallel browser automation in the EXPERIMENTAL subproject where the default Edge profile fails to load correctly across multiple browser windows. Implement a profile cloning system where window A uses the default profile directly, while windows B, C, etc. use isolated temporary clones of the default profile. Include verification mechanisms to ensure each window loads the intended profile and implement per-worker remediation for profile loading failures without disrupting other workers.

## Technical Context
**Language/Version**: Python 3.12  
**Primary Dependencies**: Selenium WebDriver >=4.0.0, Microsoft Edge browser, multiprocessing, tenacity (retry logic), structlog (structured logging)  
**Storage**: File system (temporary browser profiles, download directories)  
**Testing**: pytest, pytest-asyncio, pytest-xdist (for parallel test execution)  
**Target Platform**: macOS and Windows desktop environments  
**Project Type**: single - EXPERIMENTAL subproject within larger automation tool  
**Performance Goals**: Profile clone creation < 5 seconds per clone on SSD, startup SLA met even with high concurrency (N >= 6 windows)  
**Constraints**: No corruption of base profile, isolated per-worker profile instances, cleanup on worker exit, bounded retry policies  
**Scale/Scope**: Support 1-10 concurrent browser windows, manage profile cloning overhead, maintain session authenticity across all workers

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**✅ I. Documentation-Driven Development**: Following Proposal → Design → Implementation workflow; this plan follows the spec.md feature specification; implementation will update AGENTS.md as needed.

**✅ II. Automation Reliability**: Profile cloning and verification ensures deterministic browser state; retry mechanisms and per-worker remediation provide fail-safe behavior; configuration changes will be properly propagated across execution modes.

**✅ III. Security by Design**: No credentials involved in profile cloning; browser profile isolation maintains security boundaries; existing security policies for browser automation are preserved.

**✅ IV. Human-in-the-Loop Validation**: This is infrastructure improvement; no business decision workflows affected; audit trails for profile verification maintained in structured logs.

**✅ V. Quality Assurance Standards**: Will follow PEP 8 with type hints; comprehensive test coverage for profile operations; end-to-end validation with actual browser instances; no breaking changes to public contracts.

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
EXPERIMENTAL/           # Parallel automation subproject
├── workers/
│   ├── profile_manager.py     # Core profile cloning and verification
│   ├── worker_pool.py         # Multi-worker management
│   ├── exceptions.py          # Profile-specific exceptions
│   └── resource_monitor.py    # Worker resource tracking
├── test_integration_validation.py  # End-to-end tests
└── test_integration_manual.py      # Manual testing scenarios

src/                    # Main project (unchanged)
├── models/
├── services/ 
├── cli/
└── lib/

tests/                  # Test structure
├── contract/           # Profile API contract tests
├── integration/        # Multi-worker integration tests
└── unit/              # Profile manager unit tests
```

**Structure Decision**: Single project with EXPERIMENTAL submodule focus. The existing EXPERIMENTAL/ directory contains the parallel automation system that needs profile management enhancement. Main src/ structure remains unchanged as this is focused on the EXPERIMENTAL subsystem.

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
- Load `.specify/templates/tasks-template.md` as base
- Generate tasks from Phase 1 design docs (contracts, data model, quickstart)
- Profile management contract → contract test task [P]
- Worker integration contract → contract test task [P]
- Each data model entity (ProfileManager, WorkerProfile, etc.) → model creation task [P]
- Each verification method → verification implementation task
- Integration with existing worker_pool.py → integration task
- End-to-end test scenarios from quickstart.md → integration test tasks

**Ordering Strategy**:
- TDD order: Contract tests before implementation
- Dependency order: Core models before managers before integration
- Mark [P] for parallel execution (independent files)
- Profile cloning logic before verification logic before worker integration
- Unit tests before integration tests before end-to-end tests

**Estimated Output**: 35-40 numbered, ordered tasks in tasks.md

**Key Task Categories**:
1. **Contract Tests (5-6 tasks)**: Validate ProfileManager and WorkerPool contracts
2. **Core Implementation (8-10 tasks)**: ProfileManager, profile cloning, verification
3. **Integration Tasks (4-5 tasks)**: Worker pool integration, existing system compatibility  
4. **Testing Tasks (12-15 tasks)**: Unit tests, integration tests, end-to-end scenarios
5. **Configuration Tasks (3-4 tasks)**: Default configs, platform-specific paths
6. **Documentation Tasks (3-4 tasks)**: Update existing docs, add troubleshooting guides

**Parallel Execution Groups**:
- Contract definition files can be created in parallel [P]
- Model classes can be implemented in parallel [P] 
- Unit test files can be created in parallel [P]
- Platform-specific configuration can be developed in parallel [P]

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
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [ ] Complexity deviations documented

---
*Based on Constitution v2.1.1 - See `/memory/constitution.md`*
