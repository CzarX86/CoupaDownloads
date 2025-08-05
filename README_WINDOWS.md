# CoupaDownloads - Windows Installation Guide

## 🚀 Quick Start for Windows Users

### Option 1: One-Click Installation (Recommended)

1. **Download the project** from GitHub
2. **Extract the ZIP file** to a folder (e.g., `C:\CoupaDownloads`)
3. **Double-click** `install_windows.bat`
4. **Wait for installation** to complete
5. **Edit** `data\input\input.csv` with your PO numbers
6. **Run** `python src\main.py`

That's it! The tool will automatically:
- ✅ Install Python dependencies
- ✅ Download the correct EdgeDriver for your Edge version
- ✅ Create necessary folders
- ✅ Set up everything for you

### Option 2: PowerShell Installation (Advanced)

1. **Right-click** `install_windows.ps1`
2. **Select** "Run with PowerShell"
3. **Follow** the on-screen instructions

### Option 3: Universal Python Installer

1. **Open Command Prompt** in the project folder
2. **Run**: `python install.py`
3. **Follow** the prompts

## 📋 System Requirements

- **Windows 10/11** (64-bit)
- **Python 3.8+** (automatically detected)
- **Microsoft Edge** (automatically detected)
- **Internet connection** for downloads

## 🔧 What the Installer Does

### Automatic Detection
- ✅ **Python Version**: Checks if Python 3.8+ is installed
- ✅ **Edge Browser**: Detects Microsoft Edge installation
- ✅ **Edge Version**: Identifies your Edge version automatically
- ✅ **Compatible Driver**: Downloads the correct EdgeDriver version

### Setup Process
- 📦 **Virtual Environment**: Creates isolated Python environment
- 📦 **Dependencies**: Installs all required Python packages
- 📁 **Directories**: Creates necessary folders
- 📝 **Sample File**: Creates example input file
- 🔧 **Driver Setup**: Downloads and configures EdgeDriver

## 📁 Project Structure After Installation

```
CoupaDownloads/
├── install_windows.bat          # Windows installer
├── install_windows.ps1          # PowerShell installer
├── install.py                   # Universal installer
├── venv/                        # Python virtual environment
├── drivers/                     # EdgeDriver (auto-downloaded)
│   └── msedgedriver.exe        # Windows EdgeDriver
├── data/
│   ├── input/
│   │   └── input.csv           # Your PO numbers here
│   ├── output/                 # Generated reports
│   └── backups/                # Backup files
├── src/                        # Source code
└── tests/                      # Test files
```

## 🎯 How to Use

### 1. Prepare Your PO Numbers
Edit `data\input\input.csv`:
```csv
PO_NUMBER
PO15262984
PO15327452
PO15362783
```

### 2. Run the Tool
```cmd
python src\main.py
```

### 3. Login to Coupa
- The browser will open automatically
- Log in to Coupa when prompted
- The tool will wait for you to complete login

### 4. Monitor Progress
Watch the terminal for real-time updates:
```
🔐 Checking login status...
✅ Already logged in - proceeding with downloads
📋 Processing PO #PO15262984 (1/3)...
📎 Found 2 attachments
✅ Downloaded: PO15262984_invoice.pdf
```

### 5. Find Your Downloads
All files are saved to: `%USERPROFILE%\Downloads\CoupaDownloads\`

## 🔍 Troubleshooting

### "Python is not installed"
- Download Python from https://python.org
- **Important**: Check "Add Python to PATH" during installation
- Restart Command Prompt after installation

### "Microsoft Edge not found"
- Install Microsoft Edge from https://microsoft.com/edge
- The tool will attempt to download the driver anyway

### "Permission denied"
- Run Command Prompt as Administrator
- Check Windows Defender/Antivirus settings
- Ensure you have write permissions to the project folder

### "Driver download failed"
- Check your internet connection
- Try running the installer again
- The tool will use a fallback driver version

### "Browser won't start"
- Close all Edge browser windows
- Restart the tool
- Check if Edge is running in background

## ⚙️ Advanced Configuration

### Environment Variables
Set these before running the tool:

```cmd
set PROCESS_MAX_POS=10
set HEADLESS=false
set LOGIN_TIMEOUT=60
python src\main.py
```

### Virtual Environment
If you need to reactivate the virtual environment:
```cmd
venv\Scripts\activate
```

### Update Dependencies
```cmd
venv\Scripts\activate
pip install -r requirements.txt --upgrade
```

## 📊 Features

### Automatic Features
- 🔄 **Auto-Driver Download**: Downloads correct EdgeDriver version
- 🔄 **Version Detection**: Detects Edge browser version automatically
- 🔄 **Profile Management**: Uses your Edge profile for persistent login
- 🔄 **Error Recovery**: Handles browser crashes and timeouts
- 🔄 **Progress Tracking**: Real-time progress updates

### Download Features
- 📎 **Multiple Formats**: PDF, MSG, DOCX files
- 📎 **Auto-Renaming**: Files prefixed with PO numbers
- 📎 **Batch Processing**: Process hundreds of POs
- 📎 **Excel Reports**: Detailed processing reports
- 📎 **Telemetry**: Performance tracking and analytics

### Safety Features
- 🛡️ **Session Management**: Handles login timeouts
- 🛡️ **Browser Cleanup**: Properly closes browser processes
- 🛡️ **Error Handling**: Continues processing even if individual POs fail
- 🛡️ **File Validation**: Only downloads supported file types

## 🆘 Support

### Log Files
- Check terminal output for detailed error messages
- Review `data\output\` for Excel reports
- Check `tests\` folder for telemetry data

### Common Issues
1. **Slow downloads**: Check internet connection
2. **Login issues**: Try logging into Coupa manually first
3. **Browser crashes**: Close other Edge windows and restart
4. **Permission errors**: Run as Administrator

### Getting Help
- Check the main `USAGE_INSTRUCTIONS.md` for detailed documentation
- Review error messages in the terminal
- Check the `docs\` folder for technical documentation

## 🎉 Success!

Once everything is set up, you can:
- Process hundreds of POs automatically
- Download attachments in batch
- Generate detailed reports
- Track performance metrics

The tool handles all the complexity for you - just add your PO numbers and run!

---

**Need help?** Check the main documentation or review the error messages in the terminal. 