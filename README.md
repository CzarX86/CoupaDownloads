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

### Windows (Recommended)

1. **Download** `CoupaDownloads.exe`
2. **Double-click** to run
3. **Add** your PO numbers
4. **Click** "Start Download"

That's it! No installation, no dependencies, no setup required.

### Alternative: Source Installation

1. **Run**: `python install.py`
2. **Edit** `data/input/input.csv` with your PO numbers
3. **Run**: `python src/main.py`

That's it! The tool handles everything automatically:

- ✅ Downloads the correct EdgeDriver for your system
- ✅ Creates virtual environment and installs dependencies
- ✅ Sets up all necessary folders
- ✅ Opens browser and waits for login
- ✅ Downloads all attachments automatically

**Single EXE Advantages:**

- 🎒 **Zero Setup**: No Python, no drivers, no libraries
- 📦 **Single File**: Everything in one EXE
- 🚀 **One-Click**: Just run and use
- 🛡️ **Secure**: No system modifications
- 📱 **Portable**: Copy to any Windows machine
- 🖥️ **GUI Interface**: User-friendly graphical interface

## 📋 What You Need

### For Single EXE (Recommended)

- **Windows 10/11** (64-bit)
- **Microsoft Edge** browser
- **Internet connection**
- **Coupa access** (valid login)

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

## 📦 Building Single EXE

### Windows (Recommended)

```bash
# Build the executable
python build_single_exe.py

# Apply security features (optional)
python security_setup.py
```

This creates a single `CoupaDownloads.exe` file that includes:

- All Python dependencies
- Stable EdgeDriver
- Graphical user interface
- Complete system functionality
- Security optimizations
- Digital signature (if security_setup.py is run)

### Alternative: Source Installation

```bash
python install.py
```

## 🛡️ Security & Trust

### Digital Signature
- **Self-signed certificate** for development
- **Timestamp server** for authenticity
- **Verifiable signature** in file properties

### Windows Defender Compatibility
- **Optimized build** to avoid false positives
- **Clean execution patterns**
- **Professional metadata**
- **Security manifest** included

### File Integrity
- **MD5/SHA256 checksums** provided
- **Verification instructions** included
- **Transparent operations**

### If Security Warnings Appear:
1. **Windows Defender**: Click "More info" → "Run anyway"
2. **SmartScreen**: Click "More info" → "Run anyway"
3. **Verify checksums** match provided values
4. **Check digital signature** in file properties

## 🔍 Troubleshooting

### Common Issues

**"Windows Defender blocks the file"**
- Click "More info" and "Run anyway"
- Add to Windows Defender exclusions if needed
- Verify checksums match expected values

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
