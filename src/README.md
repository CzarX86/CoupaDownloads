src/ — project source root

Layout overview:

- `main.py`: CLI/entrypoint for the application.
- `lib/`: Shared helpers and utilities (browser, driver manager, excel processing, downloader).
- `core/`: Domain core logic and controllers (config, CSV handling, processing controller).
- `workers/`: Worker pool, worker processes, verifiers, and session management.
- `specs/`: Contract definitions and small spec modules referenced by workers.
- `ui/`: UI components (CLI/GUI-specific code).
- `config/`: Configuration loaders and interfaces.
- `utils/`: Misc small utilities used across the project.
- `cli/`: CLI subcommands and argument parsing helpers.

Notes:
- Keep `drivers/` at repo root for local dev EdgeDriver binaries.
- Avoid committing large binary artifacts or downloads (use `data/downloads/` ignored by git).
- Remove or repurpose empty folders (e.g., `tools/` was removed).
