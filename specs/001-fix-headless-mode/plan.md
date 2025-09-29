
# Implementation Plan: Fix Headless Mode in EXPERIMENTAL Subproject

**Branch**: `001-fix-headless-mode` | **Date**: 2025-09-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-fix-headless-mode/spec.md`

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
Fix headless mode functionality in the EXPERIMENTAL subproject where user selection in interactive setup doesn't affect browser behavior. Solution involves ensuring headless configuration is properly propagated from interactive setup to all browser initialization points, with fallback handling for initialization failures.

## Technical Context
**Language/Version**: Python 3.12  
**Primary Dependencies**: Selenium WebDriver, Microsoft Edge, Poetry package management  
**Storage**: Configuration state in memory/environment (no persistent storage required)  
**Testing**: pytest for unit tests, end-to-end browser automation testing  
**Target Platform**: Cross-platform (Windows, macOS, Linux) with Edge browser support
**Project Type**: single - Python automation project with subproject structure  
**Performance Goals**: Consistent browser initialization < 10 seconds regardless of headless mode  
**Constraints**: Must maintain backward compatibility, no breaking changes to CLI interfaces  
**Scale/Scope**: EXPERIMENTAL subproject only, affecting browser configuration and process workers

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Documentation-Driven Development
- [x] **PASS**: Following Proposal → Design → Implementation → Report workflow
- [x] **PASS**: ADRs will be created if architectural decisions emerge
- [x] **PASS**: Documentation maintains English technical interfaces

### II. Automation Reliability  
- [x] **PASS**: Fix directly addresses configuration propagation consistency requirement
- [x] **PASS**: Maintains deterministic, resumable browser automation workflows
- [x] **PASS**: Handles failures gracefully with retry and user choice fallback

### III. Security by Design
- [x] **PASS**: No credential handling in scope
- [x] **PASS**: Maintains existing browser profile isolation security
- [x] **PASS**: No sensitive data exposure

### IV. Human-in-the-Loop Validation
- [x] **PASS**: Does not affect existing human review workflows
- [x] **PASS**: Maintains audit trail capabilities
- [x] **NOT APPLICABLE**: Configuration fix only

### V. Quality Assurance Standards
- [x] **PASS**: Will follow PEP 8 with type hints
- [x] **PASS**: End-to-end testing required for browser automation changes
- [x] **PASS**: No breaking changes to public contracts

**Initial Constitution Check**: ✅ PASS - No violations detected

**Post-Design Constitution Check**: ✅ PASS
- All constitutional principles maintained in design
- Explicit parameter passing enhances reliability (Principle II)
- Clear contracts support quality assurance (Principle V)
- No new security concerns introduced (Principle III)

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
EXPERIMENTAL/
├── core/
│   └── main.py          # Interactive setup and execution flow
├── corelib/
│   ├── browser.py       # Browser management and configuration
│   ├── config.py        # Configuration handling
│   └── downloader.py    # Download automation
└── docs/

tests/
├── unit/
├── integration/
└── browser_automation/

src/                     # Main project (for reference)
├── core/
│   ├── browser.py       # Similar browser management
│   └── config.py        # Main config
└── utils/
```

**Structure Decision**: Single project with EXPERIMENTAL subproject. Focus on EXPERIMENTAL/corelib/browser.py and EXPERIMENTAL/core/main.py for headless mode configuration propagation. No new directories needed - this is a configuration fix within existing structure.

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
- Each contract → contract test task [P]
- Each entity → model creation task [P] 
- Each user story → integration test task
- Implementation tasks to make tests pass

**Ordering Strategy**:
- TDD order: Tests before implementation 
- Dependency order: Models before services before UI
- Mark [P] for parallel execution (independent files)

**Estimated Output**: 25-30 numbered, ordered tasks in tasks.md

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
- [x] Complexity deviations documented (none required)

---
*Based on Constitution v1.0.0 - See `.specify/memory/constitution.md`*
