# Repository Guidelines

## Project Structure & Module Organization
- Source: `src/` (core logic in `src/core/`, utilities in `src/utils/`, entrypoint `src/main.py`).
- Data: `data/input/` (CSV), outputs to `~/Downloads/CoupaDownloads` by default (see `Config`).
- Drivers: `drivers/` for pre-bundled EdgeDrivers (Windows release).
- Tests: root-level `test_*.py` and additional tests in `src/utils/GeminiTests/`.

## Build, Test, and Development Commands
- Create env (Poetry): `poetry install`
- Run app:
  - Poetry: `poetry run coupa-downloader` or `poetry run python -m src.main`
  - Windows venv: `venv\\Scripts\\activate && python src\\main.py`
- Run tests (fast): `poetry run pytest -q`
- Run tests (parallel + coverage): `poetry run pytest -n auto --cov=src --cov-report=term-missing`

## Coding Style & Naming Conventions
- Python 3.12+, follow PEP 8 with 4-space indents.
- Types: prefer type hints (as in `Config`) and clear return types.
- Names: modules/functions `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE_CASE`.
- Imports: standard library, third-party, local (grouped, blank lines between).
- Side effects only in entrypoints (e.g., `src/main.py`). Keep modules import-safe.

## Testing Guidelines
- Framework: `pytest` with `pytest-xdist`, `pytest-cov` available.
- Location/naming: files `test_*.py`, tests `test_*` functions/classes.
- Coverage: no hard threshold, but add tests for new code paths and bug fixes.
- Examples: `poetry run pytest test_simple_download.py -q` or node selection `::test_name`.

## Commit & Pull Request Guidelines
- Commits: imperative mood, concise subject; optional emoji prefix is used in history (e.g., "🔧 Fix driver path").
- PRs: include summary, rationale, linked issues, test plan/outputs, and screenshots/log snippets if relevant.
- Keep changes focused; update docs when behavior/config changes (README, RELEASE_NOTES, this file).

## Security & Configuration Tips
- Configuration via `src/core/config.py` and env vars (e.g., `EDGE_PROFILE_DIR`, `HEADLESS`, `RANDOM_SAMPLE_POS`).
- Avoid committing secrets or OS-specific absolute paths.
- Respect default output dir `~/Downloads/CoupaDownloads`; don’t write outside project/data without clear config.
