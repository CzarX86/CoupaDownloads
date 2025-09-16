# PR 19 — English UI Policy and Main Pipeline UI Audit

Status: Implemented. Added Language Policy block to `AGENTS.md` and audited main pipeline files under `src/`.

- `AGENTS.md` now includes a clear section: “Language Policy (UI vs. Source)”.
- A quick grep across `src/Core_main.py` and `src/core/*` shows user‑visible messages are already in English.
- No behavioral changes were required.

Manual checks:
- Running `python -m src.Core_main` shows English prompts/logs.
