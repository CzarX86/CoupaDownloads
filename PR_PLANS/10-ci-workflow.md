# PR 10 — Minimal CI Workflow (GitHub Actions)

Objective
- Add a minimal, fast CI workflow to run basic checks on PRs and pushes so changes remain safe and reviewable.

Scope
- Repository automation only. No application code changes.
- Introduce a single GitHub Actions workflow that:
  - Runs on `pull_request` (targeting `main`) and `push` to `main`.
  - Sets up Python, installs deps (Poetry preferred, with fallback to pip), and runs a fast test command (`pytest -q`).

Affected files
- `.github/workflows/ci.yml` (new)

Pseudodiff (reference)
```
*** Add File: .github/workflows/ci.yml
+name: CI
+
+on:
+  push:
+    branches: [ main ]
+  pull_request:
+    branches: [ main ]
+
+jobs:
+  test:
+    runs-on: ubuntu-latest
+    steps:
+      - name: Checkout
+        uses: actions/checkout@v4
+
+      - name: Setup Python
+        uses: actions/setup-python@v5
+        with:
+          python-version: '3.12'
+
+      - name: Install Poetry
+        run: |
+          curl -sSL https://install.python-poetry.org | python3 -
+          echo "$HOME/.local/bin" >> $GITHUB_PATH
+
+      - name: Install dependencies (Poetry)
+        run: |
+          poetry --version
+          poetry install -n
+
+      - name: Run tests (pytest -q)
+        run: |
+          poetry run pytest -q
+        env:
+          PYTHONWARNINGS: default
```

Acceptance Criteria
- CI triggers on PRs targeting `main` and on pushes to `main`.
- Job completes with a clear pass/fail signal based on `pytest -q`.
- No secrets or external services required.

Manual Test Plan
- Open a test PR against `main` with a trivial doc update and verify the CI job runs and reports status.
- Push to `main` (when appropriate) and confirm CI runs.

Out of Scope
- Linting/formatting, coverage upload, multi-OS matrix.
- Any changes to application code.

Suggested commit message
- `ci: add minimal GitHub Actions workflow for pytest`

Suggested branch
- `ci/10-minimal-workflow`

Notes
- If Poetry is not desired in CI, we can switch to pip (`pip install -r requirements.txt`) in a follow-up plan.
- If tests are heavy, we can scope to a subset or mark slow tests to skip by default.
