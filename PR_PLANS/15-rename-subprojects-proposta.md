# PR 15 — Subproject renaming and structure clarification
- Status: draft
- Implementação: pending
- Data: 2025-09-23
- Responsáveis: TBD
- Observações: 


## Objective
Rename subprojects to clear, purpose-driven names and add top-level `apps/` layout to improve discoverability.

## Proposed new names (mapping)
- `MyScript/` → `apps/coupa_downloader_ui/`
  - Focus: Selenium/Edge automation + GUI for downloads
- `embeddinggemma_feasibility/` → `apps/ai_rag_lab/`
  - Focus: AI/NLP experiments (RAG, extractors, assessment)
- `src/` (core runtime) → keep as `src/` for now (entry CLI, core modules)

## Notes
- We will move folders and add import shims (small `__init__.py` with re-exports) where necessary to avoid breaking existing paths until all references are updated.
- Update docs, READMEs, and scripts to the new paths.

## Scope
- Create `apps/` and move subprojects under it with the names above.
- Add deprecation shims in old locations for one cycle (simple notice files and optional import redirects).
- Update references in docs and scripts (`README.md`, guides, examples).
- No behavior/code changes beyond path updates.

## Pseudodiff
```
+ apps/
+   coupa_downloader_ui/        # from MyScript/
+   ai_rag_lab/                 # from embeddinggemma_feasibility/
~ README.md                     # new map of apps
~ drivers/README.md             # adjusted usage paths
~ docs/*                        # path updates
```

## Acceptance
- New paths exist and contain the same content.
- Old paths contain a README.md with deprecation note and pointer to new location.
- No import/runtime breakages; command examples reflect new paths.

## Manual tests
- Navigate to each app and run the quick start examples.
- Verify that the interactive CLI and Core flows still run (after references are updated).

## Suggested branch and message
- Branch: `plan/15-rename-subprojects`
- Commit: `docs(pr-plan): PR 15 — rename subprojects and clarify structure`
