# CoupaDownloads - Automated PO Attachment Downloader

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](https://github.com/CzarX86/CoupaDownloads)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

> **🚀 Plug & Play Solution** - Automatically downloads attachments from Coupa Purchase Orders with zero configuration required!

## ✨ Features

- 🔄 **Auto-Driver Download**: Automatically detects Edge version and downloads compatible driver
- 🌐 **Cross-Platform**: Works on Windows, macOS, and Linux
- 📎 **Batch Processing**: Download attachments from hundreds of POs automatically
- 📊 **Smart Reports**: Generates detailed Excel reports with telemetry data
- 🛡️ **Error Recovery**: Handles browser crashes and continues processing
- 📁 **Auto-Organization**: Files automatically renamed with PO prefixes
- 🔐 **Session Management**: Persistent login sessions with profile support

## 🚀 Quick Start

### Option 1: Portable Package (Recommended)
1. **Download** the portable ZIP for your platform
2. **Extract** the ZIP file
3. **Edit** `data/input/input.csv` with your PO numbers
4. **Run** the launcher script

### Option 2: Windows Users (One-Click Installation)
1. **Download** and extract the project
2. **Double-click** `install_windows.bat`
3. **Edit** `data\input\input.csv` with your PO numbers
4. **Run** `python src\main.py`

### Option 3: All Platforms
1. **Run**: `python install.py`
2. **Edit** `data/input/input.csv` with your PO numbers
3. **Run**: `python src/main.py`

That's it! The tool handles everything automatically:
- ✅ Downloads the correct EdgeDriver for your system
- ✅ Creates virtual environment and installs dependencies
- ✅ Sets up all necessary folders
- ✅ Opens browser and waits for login
- ✅ Downloads all attachments automatically

**Portable Package Advantages:**
- 🎒 **Zero Installation**: No Python installation required
- 📦 **Complete Package**: All dependencies included
- 🔧 **Stable Driver**: Pre-downloaded compatible EdgeDriver
- 🚀 **One-Click**: Just extract and run

## 📋 What You Need

### For Portable Package
- **Microsoft Edge** (automatically detected)
- **Coupa Access** (valid login credentials)
- **Internet Connection** (for downloads)

### For Source Installation
- **Python 3.8+** (automatically detected)
- **Microsoft Edge** (automatically detected)
- **Coupa Access** (valid login credentials)
- **Internet Connection** (for downloads)

## 📁 Project Structure

```
CoupaDownloads/
├── install_windows.bat          # Windows one-click installer
├── install_windows.ps1          # PowerShell installer
├── install.py                   # Universal installer
├── test_installation.py         # Installation verification
├── README_WINDOWS.md            # Windows-specific guide
├── USAGE_INSTRUCTIONS.md        # Detailed usage guide
├── venv/                        # Python virtual environment
├── drivers/                     # EdgeDriver (auto-downloaded)
├── data/
│   ├── input/
│   │   └── input.csv           # Your PO numbers here
│   ├── output/                 # Generated reports
│   └── backups/                # Backup files
├── src/                        # Source code
│   └── core/
│       ├── browser.py          # Browser management
│       ├── config.py           # Configuration
│       ├── csv_processor.py    # CSV processing
│       ├── downloader.py       # Download logic
│       └── driver_manager.py   # Auto-driver download
└── tests/                      # Test files
```

## 🎯 How It Works

### 1. Automatic Setup
The installer automatically:
- Detects your Python version
- Creates virtual environment
- Installs all dependencies
- Detects Microsoft Edge version
- Downloads compatible EdgeDriver
- Creates necessary folders
- Sets up sample input file

### 2. Smart Processing
The tool intelligently:
- Opens Microsoft Edge with your profile
- Navigates to Coupa and waits for login
- Processes each PO number from your CSV
- Downloads all attachments (PDF, MSG, DOCX)
- Renames files with PO prefixes
- Generates detailed reports
- Handles errors gracefully

### 3. File Organization
Downloads are automatically organized:
```
~/Downloads/CoupaDownloads/
├── PO15262984_invoice.pdf
├── PO15262984_contract.docx
├── PO15327452_specification.pdf
└── ...
```

## 📊 Generated Reports

### Excel Report
Location: `data/output/coupa_report_YYYYMMDD_HHMMSS.xlsx`
- PO numbers processed
- Number of attachments found/downloaded
- Processing status and error messages
- Timestamps and performance metrics

### Telemetry Data
- `tests/download_telemetry_summary.csv` - Overall performance
- `tests/download_telemetry_details.csv` - Step-by-step metrics

## 🔧 Configuration

### Environment Variables (Optional)
```bash
# Limit processing (for testing)
export PROCESS_MAX_POS=10

# Run without browser window
export HEADLESS=true

# Login timeout
export LOGIN_TIMEOUT=60
```

### Input File Format
Edit `data/input/input.csv`:
```csv
PO_NUMBER
PO15262984
PO15327452
PO15362783
```

## 🧪 Testing

### Verify Installation
```bash
python test_installation.py
```

### Run Tests
```bash
python run_tests.py
```

## 📦 Building Portable Packages

### Simple Portable Package
```bash
python build_portable_simple.py
```

### Advanced Portable Package (with embedded Python)
```bash
python build_portable_advanced.py
```

### Basic Portable Package
```bash
python build_portable.py
```

## 🔍 Troubleshooting

### Common Issues

**"Python not found"**
- Download Python from https://python.org
- Check "Add Python to PATH" during installation

**"Edge not found"**
- Install Microsoft Edge from https://microsoft.com/edge
- Tool will attempt to download driver anyway

**"Permission denied"**
- Run as Administrator (Windows)
- Check antivirus settings

**"Driver download failed"**
- Check internet connection
- Try running installer again

### Getting Help
- Check `USAGE_INSTRUCTIONS.md` for detailed documentation
- Review terminal output for error messages
- Run `python test_installation.py` for diagnostics

## 🛡️ Safety Features

- **Session Management**: Handles login timeouts and browser crashes
- **Error Recovery**: Continues processing even if individual POs fail
- **File Validation**: Only downloads supported file types
- **Browser Cleanup**: Properly closes browser processes
- **Progress Tracking**: Detailed logging of all operations

## 📈 Performance

- **Batch Processing**: Handle hundreds of POs efficiently
- **Parallel Downloads**: Multiple files downloaded simultaneously
- **Memory Management**: Efficient resource usage
- **Error Handling**: Robust error recovery mechanisms

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Microsoft Edge WebDriver team
- Selenium WebDriver community
- Coupa platform for providing the API

---

**Ready to automate your Coupa downloads?** Just run the installer and you're good to go! 🚀

For detailed instructions, see [USAGE_INSTRUCTIONS.md](USAGE_INSTRUCTIONS.md) or [README_WINDOWS.md](README_WINDOWS.md) for Windows users. 