# Agent Guide (Codex) — Plan → Implement Workflow

This repository uses a lightweight, review‑first workflow for all non‑trivial changes. As the agent, always propose a Plan PR first, wait for approval, and only then implement the change exactly as approved.

## Scope and Principles
- This guide applies to the entire repository.
- The agent MUST:
  - Propose a plan in `PR_PLANS/NN-<slug>.md` (no code changes in this step).
  - Await human approval. Only implement after explicit approval.
  - Keep implementation strictly within the approved scope.
- Do not change global defaults, runtime behavior, or architecture without an approved plan.
- Follow PEP 8 and existing project conventions (types, names, import order, side effects only in entrypoints).
- Prefer additive, minimal, and reviewable diffs. Avoid drive‑by refactors.

## PR Conventions
- Plan files: `PR_PLANS/NN-<slug>.md`
  - Contents: Objective, Scope, Affected files, Pseudodiff, Acceptance criteria, Manual tests, Suggested commit message and branch.
  - Number `NN` is incremental (01, 02, 03…) and reflects implementation order.
- Branch naming:
  - Plan: `plan/NN-<slug>`
  - Implementation: `feat/NN-<slug>`, `fix/NN-<slug>`, `chore/NN-<slug>`, or `docs/NN-<slug>`
- Commit messages:
  - Plan: `docs(pr-plan): PR NN — <title>`
  - Implementation: `<type>(scope): PR NN — <title>` (e.g., `feat(downloader): PR 08 — attachment discovery`)

## Standard Operating Procedure (SOP)
1) Plan
   - Create `PR_PLANS/NN-<slug>.md` with all sections filled.
   - Do NOT modify code in this step.
2) Implement (after approval)
   - Implement only what the plan states. If scope changes are needed, submit a new plan.
   - Keep the PR small, focused, and testable.
   - After implementation move PR file into "Implemented" folder.

## Technical Rules for the Agent
### Language Policy (UI vs. Source)
- UI must be English: all user‑visible text in CLI/GUI (prompts, help, logs/messages, errors) is written and presented in English.
- Source may be pt‑BR: code, inline comments, and internal docs/comments may be written in Portuguese (pt‑BR).
- Debug logs: if printed by default, keep in English. Portuguese‑only debug notes are fine when suppressed by default.
- Do not alter runtime defaults or behavior; only reword UI strings as needed.

- Testing and runtime
  - Prefer fast checks; avoid launching heavy processes unless requested.
  - Respect environment variables and defaults; do not mutate user environment in code.
- Security
  - Do not commit secrets or OS‑specific absolute paths.
  - Do not download external binaries without an approved plan (e.g., driver updates).
- CSV/Excel IO
  - Preserve delimiter (auto‑detect), write as UTF‑8 BOM (`utf-8-sig`), `lineterminator="\n"`, `csv.QUOTE_MINIMAL`.
  - Keep hierarchy and column integrity.
- Concurrency / Browser
  - Be explicit in plans about process/thread model changes.
  - Avoid changing browser/profile defaults unless planned and approved.

## Required Checklist in Every Plan
- [ ] Objective and Scope are clear and limited.
- [ ] Affected files listed.
- [ ] Pseudodiff (small, readable, representative of the approach).
- [ ] Acceptance criteria and minimal manual tests.
- [ ] Suggested commit message and branch name.

## GitHub Labels (optional)
- Plan PRs: `plan`, add `plan-approved` on approval.
- Implementation PRs: `impl`, add `impl-approved` on approval.

## Notes
- If a plan depends on another, reference its number (e.g., “after PR 03”).
- For multi‑step refactors, prefer multiple small PRs over a single large PR.
