# 🚀 CoupaDownloads - Windows Release

## ✨ What's New in This Release

This release includes everything you need to run CoupaDownloads on Windows with enhanced parallel processing:

- ✅ **Parallel Processing** - Process multiple POs simultaneously with configurable workers
- ✅ **Profile Isolation** - Independent browser profiles prevent worker conflicts
- ✅ **Performance Scaling** - Up to 6x faster processing with optimal worker configuration
- ✅ **Automatic EdgeDriver download** - No manual driver management needed
- ✅ **Enhanced driver compatibility** - Works with Edge 116-120
- ✅ **One-click setup** - Just run `setup_windows.bat`
- ✅ **All dependencies included** - No internet required after setup
- ✅ **Comprehensive error handling** - Better troubleshooting

## 🎯 Quick Start

### Step 1: Download and Extract
1. Download the ZIP file from GitHub releases
2. Extract to a folder (e.g., `C:\CoupaDownloads`)

### Step 2: Run Setup
```cmd
# Double-click or run:
setup_windows.bat
```

### Step 3: Edit Your PO Numbers
Edit `data\input\input.csv` with your PO numbers:
```csv
PO_NUMBER
PO15262984
PO15327452
PO15362783
```

Supported columns (CSV/Excel) — the app fills these when available:
- PO_NUMBER, STATUS, SUPPLIER, ATTACHMENTS_FOUND, ATTACHMENTS_DOWNLOADED,
  AttachmentName, LAST_PROCESSED, ERROR_MESSAGE, DOWNLOAD_FOLDER, COUPA_URL

### Step 4: Run the Application

**Standard Mode (Sequential):**
```cmd
# Run the application (module mode)
poetry run python -m src.Core_main
```

**Parallel Processing Mode:**
```cmd
# Enable parallel processing with environment variables
export COUPA_ENABLE_PARALLEL=true
export COUPA_MAX_WORKERS=4
poetry run python -m src.Core_main

# Or configure directly in interactive mode
poetry run python -m src.Core_main --parallel --workers 4
```

**Parallel Processing Configuration:**
- `COUPA_ENABLE_PARALLEL=true` - Enable parallel processing
- `COUPA_MAX_WORKERS=4` - Set number of worker processes (scale with available resources; no hard cap unless you set `MAX_PARALLEL_WORKERS_CAP`)
- `COUPA_PROFILE_CLEANUP_ON_START=true` - Clean profiles on startup
- `COUPA_PROFILE_REUSE_ENABLED=true` - Reuse browser profiles (default: true)

For detailed configuration options, see: `EXPERIMENTAL/docs/parallel-processing.md`

### Feedback and training loop
- 🪄 **Guided wizard** — `poetry run python tools/feedback_cli.py wizard`
  - Launches an interactive, English-only walkthrough for preparing review CSVs, ingesting annotations, evaluating metrics, training Sentence Transformers, and exporting Label Studio tasks.
- ⚙️ **Classic CLI** — `poetry run python tools/feedback_cli.py --help`
  - Ideal for automation; uses the same handlers that the wizard calls behind the scenes.

## 📚 User Guide
For a complete end-to-end manual (installation, configuration, running, outputs, troubleshooting), see:
- `docs/USER_GUIDE.md` - General usage guide
- `EXPERIMENTAL/docs/parallel-processing.md` - Parallel processing configuration and optimization

## 🚀 Future Releases
- **Standalone Executables**: Upcoming releases will include self-contained executables for Windows and macOS that require no installation or external dependencies.

## 🔧 What the Setup Does

1. **Checks Python installation**
2. **Downloads EdgeDrivers automatically**
3. **Creates virtual environment**
4. **Installs all dependencies**
5. **Sets up sample files**
6. **Configures parallel processing environment**
7. **Sets up everything**

## 📁 Release Contents

```
CoupaDownloads/
├── setup_windows.bat          # Windows installer
├── download_drivers.bat       # Driver download script
├── pyproject.toml             # Manifesto de dependências (Poetry)
├── poetry.lock                # Versões travadas das dependências
├── drivers/                   # EdgeDriver versions (downloaded)
├── src/                      # Application source code
├── EXPERIMENTAL/             # Parallel processing implementation
│   ├── docs/parallel-processing.md  # Parallel processing guide
│   ├── core/                # Enhanced core modules
│   ├── workers/             # Worker pool and profile management
│   └── corelib/             # Shared configuration and models
├── tests/                    # Test suites including performance validation
├── data/
│   ├── input/               # Your PO numbers here
│   ├── output/              # Generated reports
│   └── backups/             # Backup files
└── README.md                # This file
```

## 🛠️ Troubleshooting

### Python Not Found
- Download Python from [python.org](https://python.org)
- Check "Add Python to PATH" during installation

### Edge Browser Issues
- Install Microsoft Edge from [microsoft.com/edge](https://www.microsoft.com/edge)
- Update to latest version

### Driver Download Issues
- Check internet connection
- Run Command Prompt as Administrator
- Disable antivirus temporarily

### Permission Errors
- Run Command Prompt as Administrator
- Or run PowerShell with: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### Parallel Processing Issues
- **High resource usage**: Reduce `COUPA_MAX_WORKERS` (try 2-4 workers)
- **Profile conflicts**: Set `COUPA_PROFILE_CLEANUP_ON_START=true`
- **Memory issues**: Lower worker count or increase system RAM
- **Performance not improving**: Check system specs and network latency

Run performance validation: `poetry run pytest tests/integration/parallel/test_performance_validation.py -v`

### 📁 Folder Naming (New Convention)
During processing each PO now uses a canonical working directory ending with `__WORK` (e.g. `PO_123456__WORK`).
Only after all downloads settle is it atomically renamed to a single final status folder:

`PO_123456__WORK` → `PO_123456_COMPLETED` | `PO_123456_FAILED` | `PO_123456_PARTIAL` | `PO_123456_NO_ATTACHMENTS`

Key guarantees:
- Exactly one final folder per PO (no proliferation of `-2`, `-3` variants)
- No unsuffixed final folders remain
- Retries reuse the same `__WORK` directory

Older runs may still contain multiple suffixed variants; new executions won’t create them.

## 🎉 Success Indicators

You'll know it's working when:
- ✅ Python version shows (3.8 or higher)
- ✅ EdgeDrivers download successfully
- ✅ Virtual environment activates (shows `(venv)` in prompt)
- ✅ Dependencies install without errors
- ✅ Browser opens when running the application
- ✅ Parallel processing shows worker count > 1 in logs (when enabled)
- ✅ Performance tests pass with expected scaling improvements

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Ensure Microsoft Edge is installed and updated
3. Run Command Prompt as Administrator
4. Check your internet connection

## 🔄 Updates

To update to a new release:
1. Download the new ZIP file
2. Extract to a new folder
3. Run `setup_windows.bat` again
4. Copy your PO numbers from the old `data\input\input.csv`

---

**Ready to use!** Just run `setup_windows.bat` and you're good to go! 🚀

## 📚 Optional: RAG (LlamaIndex) Tools

This repo includes an isolated RAG module under `embeddinggemma_feasibility`.

- Instale todas as dependências (core, ML, anotação, testes) com:
  - `poetry install`

Run the interactive RAG CLI:
- `poetry run rag-cli`

Notes:
- The RAG stack uses LlamaIndex + HNSWLib. Internet may be required on first run to download small HF models unless cached.
- To stay fully offline, disable reranking in the CLI when prompted.

## � Documentation

- **Core Interfaces Guide**: `docs/core_interfaces.md` - Developer guide for UI integration APIs
- **Parallel Processing Guide**: `EXPERIMENTAL/docs/parallel-processing.md`
- **Performance Reports**: `reports/performance_validation_report.md`
- Release notes: `docs/RELEASE_NOTES.md`
- Release strategy: `docs/RELEASE_STRATEGY.md`
- Offline bundle guide: `docs/howto/README_Offline.md`
- Network troubleshooting: `docs/platform/NETWORK_ISSUE_SOLUTION.md`
- Profile protection: `docs/howto/PROFILE_PROTECTION.md`
- E2E flow diagram: `docs/reports/E2E_FLOW_DIAGRAM.md`
- Implementation reports: `docs/reports/IMPLEMENTATION_REPORT.md`, `docs/reports/THREAD_IMPLEMENTATION_REPORT.md`
- Guia GitHub MCP (Codex VS Code): `docs/howto/github_mcp_codex_vscode.md`
- Blueprint de refatoração e SPA: `docs/refactor/pr32-refactor-spa-blueprint.md`
- Wizard de treinamento guiado: `docs/cli/training_wizard.md`
