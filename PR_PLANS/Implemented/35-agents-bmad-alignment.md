# PR Plan 35 — Align AGENTS.md with the BMAD Method

## Objective
Refresh `AGENTS.md` so the agent workflow in this repository explicitly mirrors the BMAD-METHOD™ phases (Planning, Story Sharding, Dev/QA loop) while preserving the existing Plan → Implement guardrails already in place.

## Scope
- Reorganize `AGENTS.md` around BMAD’s two key pillars (Agentic Planning and Context-Engineered Development) and map them to our current SOP.
- Introduce subsections that describe the expectations for each BMAD role we rely on (PO/Plan author, Scrum Master/Story curator, Dev, QA) when operating inside this repo.
- Add pointers to BMAD reference material (notably the upstream `docs/user-guide.md`) so future contributors know where the canonical process is documented.

Out of scope:
- Changing runtime defaults, automation scripts, or adding new agent bundles.
- Altering repository workflow files outside of `AGENTS.md`.

## Affected Files
- `AGENTS.md`

## Approach
1. **Audit current guidance vs. BMAD** — Tag each existing AGENTS.md section with the closest BMAD phase so we know what content can be retained, updated, or merged.
2. **Restructure the document** — Introduce headings for "BMAD Overview", "Phase Mapping", and "Role Expectations". Keep existing mandates (plan files, mermaid diagrams, plain-language summaries) but nest them inside the relevant BMAD phase.
3. **Add BMAD visual + references** — Embed a Mermaid diagram that shows how Plan ➜ Shard ➜ Story ➜ Dev/QA matches our Plan ➜ Implement SOP, and link to the upstream BMAD user guide for deeper reading.
4. **Clarify language requirements plainly** — Provide a short, beginner-friendly summary of BMAD so newcomers understand why the structure matters before diving into the procedural checklist.

```mermaid
flowchart TD
    A[Plan Author (PO/Analyst)] --> B[BMAD Planning Artifacts]
    B --> C[Story Sharding (Scrum Master)]
    C --> D[Dev Agent Executes Story]
    D --> E[QA Agent Validates]
    E --> F[Feedback / Next Plan]
    F -->|Iterate| A
    style A fill:#DEE9FF,color:#1A237E
    style B fill:#E8F5E9,color:#1B5E20
    style C fill:#FFF8E1,color:#F57F17
    style D fill:#FCE4EC,color:#880E4F
    style E fill:#E0F2F1,color:#004D40
    style F fill:#F3E5F5,color:#4A148C
```

### Plain-language explainer
BMAD is a step-by-step rhythm for working with AI teammates: one person (or agent) writes a detailed plan, another breaks that plan into bite-sized stories, a developer agent builds exactly what each story says, and a QA agent double-checks the results before looping back. Updating `AGENTS.md` to speak this language helps every contributor know which hat they are wearing and what files or checklists keep the process on track.

## Pseudodiff (representative)
```diff
--- AGENTS.md
+++ AGENTS.md
@@
-# Agent Guide (Codex) — Plan → Implement Workflow
-...
+## BMAD Overview
+- Quick summary of Agentic Planning and Context-Engineered Development.
+- Link to upstream BMAD docs for deeper dives.
+
+## Phase Mapping to This Repo
+- Table: BMAD Phase | Local Artifact | Required Actions.
+- Restate Plan → Implement SOP within the Planning phase subsection.
+
+## Role Expectations
+- PO/Plan Author duties (plans, mermaid diagrams, checklists).
+- Scrum Master notes on sharding stories and maintaining context files.
+- Dev agent instructions (follow approved scope, respect language policy).
+- QA agent responsibilities (tests, gates, feedback loop).
+
+## Operational Checklists
+- Existing checklists preserved but grouped under the relevant role/phase.
+- Ensure the language policy and security rules stay prominent.
```

## Acceptance Criteria
- `AGENTS.md` introduces BMAD terminology and clearly maps each BMAD phase to the repository’s Plan → Implement workflow.
- The document contains at least one Mermaid diagram illustrating the BMAD flow as adapted for this project.
- Role responsibilities (Plan author, Scrum Master, Dev, QA) are spelled out with references to existing requirements (checklist, language policy, manual testing expectations).
- Links to upstream BMAD resources are provided without removing any existing guardrails or checklists.

## Manual Tests
- Open the updated Markdown in a preview to confirm the Mermaid diagram renders and headings form a coherent structure.
- Proofread to ensure all existing repository-specific mandates remain present and unchanged in meaning.

## Suggested commit message and branch
- Branch: `plan/35-agents-bmad-alignment`
- Commit: `docs(pr-plan): PR 35 — align agent guide with BMAD method`

## Checklist
- [ ] Objective and Scope are clear and limited.
- [ ] Affected files listed.
- [ ] Pseudodiff (small, readable, representative of the approach).
- [ ] Acceptance criteria and minimal manual tests.
- [ ] Suggested commit message and branch name.
