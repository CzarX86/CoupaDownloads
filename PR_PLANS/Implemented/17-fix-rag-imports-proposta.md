# PR 17 — Standardize package imports for RAG and advanced extractor
- Status: draft
- Implementação: pending
- Data: 2025-09-23
- Responsáveis: TBD
- Observações: 


## Objective
Eliminate the “attempted relative import with no known parent package” warning and fully restore RAG-assisted functionality by making `embeddinggemma_feasibility` a clean Python package at runtime:
- Use package-relative imports within the package.
- Remove ad-hoc `sys.path` injection from the CLI.
- Ensure the package has an `__init__.py` for unambiguous package semantics.

## Scope
- Add `embeddinggemma_feasibility/__init__.py` (empty).
- In `embeddinggemma_feasibility/advanced_coupa_field_extractor.py`:
  - Change `from config import get_config` → `from .config import get_config`.
  - Keep existing relative import of `.rag_assisted_extraction` used during RAG path.
- In `embeddinggemma_feasibility/interactive_cli.py`:
  - Remove `sys.path` manipulation.
  - Import extractor with a relative package import: `from .advanced_coupa_field_extractor import AdvancedCoupaPDFFieldExtractor`.
- No behavioral changes beyond fixing import resolution; RAG stays optional via the prompt.

## Affected files
- `embeddinggemma_feasibility/__init__.py` (new)
- `embeddinggemma_feasibility/advanced_coupa_field_extractor.py`
- `embeddinggemma_feasibility/interactive_cli.py`

## Pseudodiff
```diff
+ embeddinggemma_feasibility/__init__.py  # new, empty
--- a/embeddinggemma_feasibility/advanced_coupa_field_extractor.py
+++ b/embeddinggemma_feasibility/advanced_coupa_field_extractor.py
- from config import get_config
+ from .config import get_config

--- a/embeddinggemma_feasibility/interactive_cli.py
+++ b/embeddinggemma_feasibility/interactive_cli.py
-    import sys as _sys
-    if str(SUBPROJECT_ROOT) not in _sys.path:
-        _sys.path.insert(0, str(SUBPROJECT_ROOT))
-
-    try:
-        from advanced_coupa_field_extractor import AdvancedCoupaPDFFieldExtractor
+    try:
+        from .advanced_coupa_field_extractor import AdvancedCoupaPDFFieldExtractor
```

## Acceptance criteria
- Running `poetry run rag-cli` and choosing option `4` with “Usar RAG …? y” shows no warning about relative imports; log shows either `🔎 RAG assistido: contexto reduzido` or proceeds without RAG only if user chose N.
- Import checks succeed:
  - `poetry run python -c "from embeddinggemma_feasibility.advanced_coupa_field_extractor import AdvancedCoupaPDFFieldExtractor; print('ok')"` prints `ok`.
  - `poetry run python -c "from embeddinggemma_feasibility.rag_assisted_extraction import retrieve_candidates_for_fields; print('ok')"` prints `ok`.
- No regression to other CLI options (1–3). Build/Query use the same package path and still work.

## Minimal manual tests
1) Import sanity (module load):
   - `poetry run python -c "from embeddinggemma_feasibility.advanced_coupa_field_extractor import AdvancedCoupaPDFFieldExtractor; print('ok')"`
   - `poetry run python -c "from embeddinggemma_feasibility.rag_assisted_extraction import retrieve_candidates_for_fields; print('ok')"`
2) CLI run:
   - `poetry run rag-cli` → option `4` → set “Usar RAG …?” to `y`.
   - Choose a sample docs folder; verify no import warning and that processing continues.
3) Non-RAG path works too: same flow but answer `N`.

## Suggested commit message and branch
- Branch (plan): `plan/17-fix-rag-imports`
- Commit: `docs(pr-plan): PR 17 — standardize package imports for RAG and extractor`

## Checklist
- [x] Objective and Scope are clear and limited.
- [x] Affected files listed.
- [x] Pseudodiff provided.
- [x] Acceptance criteria and minimal manual tests included.
- [x] Suggested commit message and branch name.

