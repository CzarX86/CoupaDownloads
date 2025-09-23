# PR 16 — Align httpx with Ollama client (bump to ^0.27) and add ollama to ML group
- Status: draft
- Implementação: pending
- Data: 2025-09-23
- Responsáveis: TBD
- Observações: 


## Objective
Resolve Poetry resolver conflict when enabling ML extras with the Python `ollama` client by aligning `httpx` to a compatible version and declaring `ollama` in the ML dependency group. Ensure the advanced extractor (Option 4 in `rag-cli`) runs without dependency errors.

## Scope
- Update root `pyproject.toml`:
  - Bump `httpx` from `^0.25.0` to `^0.27.0` (compatible with `ollama>=0.5.4`).
  - Add `ollama` to `[tool.poetry.group.ml.dependencies]` as `>=0.5.4,<0.6.0`.
- No changes to application code or runtime behavior.
- Regenerate `poetry.lock` during implementation PR.

## Affected Files
- `pyproject.toml`
- `poetry.lock` (regenerated in implementation)

## Rationale
- The Python package `ollama (>=0.5.4,<0.6.0)` depends on `httpx (>=0.27)`.
- Current project pins `httpx = "^0.25.0"`, causing version solving to fail when adding `ollama`.
- `MyScript/async_downloader.py` uses `httpx` with APIs that remain available in `0.27.x` (`Timeout`, `AsyncClient`, `Limits`, and exceptions), so the risk of breakage is low.

## Pseudodiff
```diff
--- a/pyproject.toml
+++ b/pyproject.toml
@@ [tool.poetry.dependencies]
-httpx = "^0.25.0"
+httpx = "^0.27.0"
@@ [tool.poetry.group.ml.dependencies]
 # existing ML deps...
+pydantic = ">=2.5.0"        # already present above, kept for context
+ollama = ">=0.5.4,<0.6.0"
```

Notes:
- Exact ordering will follow existing file conventions during implementation.
- No other dependency changes planned.

## Acceptance Criteria
- `poetry install --with ml` completes with no dependency conflicts.
- `poetry run python -c "import ollama, json; print(bool(ollama.list()['models']))"` executes without `ModuleNotFoundError` and prints `True/False` (depending on local models).
- `poetry run rag-cli` → option `4) Executar Extrator Avançado (PDF → CSV)` initializes and logs Ollama availability (or attempts to start it) instead of aborting with dependency-related errors.
- Import of downloader remains functional: `poetry run python -c "import MyScript.async_downloader as m; print('ok')"` prints `ok`.

## Minimal Manual Tests
1) Fresh install with ML group:
   - `poetry lock && poetry install --with ml`
   - `poetry run python -c "import httpx; import ollama; print(httpx.__version__)"`
2) Verify Ollama connectivity inside venv:
   - Ensure server is running: `ollama list` (host configurable via `OLLAMA_HOST`)
   - `poetry run python -c "import ollama, json; print(json.dumps(ollama.list()))"`
3) Run advanced extractor from menu:
   - `poetry run rag-cli`
   - Choose `4`, accept defaults, answer prompts.
   - Expect log: `✅ Ollama disponível ...` or `🔄 Tentando iniciar Ollama...` followed by success.
4) Sanity import for downloader (httpx usage):
   - `poetry run python -c "import MyScript.async_downloader as m; print('ok')"`

## Out of Scope
- Making Ollama optional in the advanced extractor when disabled in the menu.
- Refactors to downloader or network stack.

## Suggested Commit Message and Branch
- Branch (plan): `plan/16-ollama-httpx-bump`
- Commit: `docs(pr-plan): PR 16 — align httpx with Ollama client and add ollama to ML group`

## Checklist
- [x] Objective and Scope are clear and limited.
- [x] Affected files listed.
- [x] Pseudodiff provided.
- [x] Acceptance criteria and minimal manual tests included.
- [x] Suggested commit message and branch name.

