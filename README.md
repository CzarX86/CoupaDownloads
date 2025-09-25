# 🚀 CoupaDownloads - Windows Release

## ✨ What's New in This Release

This release includes everything you need to run CoupaDownloads on Windows:

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
```cmd
# (Opcional) Abra uma shell do Poetry
# poetry shell

# Run the application (module mode)
poetry run python -m src.Core_main
```

### Feedback and training loop
- 🧭 **PDF Training Wizard** — start the FastAPI backend (`PYTHONPATH=src poetry run python -m server.pdf_training_app.main`) and the SPA (`cd src/spa && npm run dev`) to upload PDFs, acompanhar o pré-processamento, anotar direto no viewer e gerar datasets/treinamentos.
- 📡 **API endpoints** — `curl http://localhost:8008/api/pdf-training/jobs?resource_type=document&resource_id=<id>` monitora jobs de análise; use `/api/pdf-training/documents` para gerenciar uploads e `/api/pdf-training/training-runs` para disparar treinamentos.
- 🪦 **Legacy CLI** — `tools/feedback_cli.py` permanece apenas como stub informativo. Todo o fluxo de treinamento/feedback ocorre pelo backend + SPA ou chamadas REST.

## 📚 User Guide
For a complete end-to-end manual (installation, configuration, running, outputs, troubleshooting), see:
`docs/USER_GUIDE.md`

## 🔧 What the Setup Does

1. **Checks Python installation**
2. **Downloads EdgeDrivers automatically**
3. **Creates virtual environment**
4. **Installs all dependencies**
5. **Sets up sample files**
6. **Configures everything**

## 📁 Release Contents

```
CoupaDownloads/
├── setup_windows.bat          # Windows installer
├── download_drivers.bat       # Driver download script
├── pyproject.toml             # Manifesto de dependências (Poetry)
├── poetry.lock                # Versões travadas das dependências
├── drivers/                   # EdgeDriver versions (downloaded)
├── src/                      # Application source code
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

## 🎉 Success Indicators

You'll know it's working when:
- ✅ Python version shows (3.8 or higher)
- ✅ EdgeDrivers download successfully
- ✅ Virtual environment activates (shows `(venv)` in prompt)
- ✅ Dependencies install without errors
- ✅ Browser opens when running the application

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

## 📖 Documentation

- Release notes: `docs/RELEASE_NOTES.md`
- Release strategy: `docs/RELEASE_STRATEGY.md`
- Offline bundle guide: `docs/howto/README_Offline.md`
- Network troubleshooting: `docs/platform/NETWORK_ISSUE_SOLUTION.md`
- Profile protection: `docs/howto/PROFILE_PROTECTION.md`
- E2E flow diagram: `docs/reports/E2E_FLOW_DIAGRAM.md`
- Implementation reports: `docs/reports/IMPLEMENTATION_REPORT.md`, `docs/reports/THREAD_IMPLEMENTATION_REPORT.md`
- Guia GitHub MCP (Codex VS Code): `docs/howto/github_mcp_codex_vscode.md`
- Blueprint de refatoração e SPA: `docs/refactor/pr32-refactor-spa-blueprint.md`
- Fluxo PDF-first (passo a passo): `docs/HITL_FEEDBACK_WORKFLOW.md`
