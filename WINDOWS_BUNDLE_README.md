# Windows Bundle Creator

## 🎯 Overview

This project includes a single, streamlined method for creating Windows bundles that handles webdriver download issues commonly encountered in corporate environments.

## 🚀 Quick Start

### Create Windows Bundle

```bash
# Run the Windows bundle creator
python scripts/create_windows_bundle.py
```

This will create: `output/CoupaDownloads_Windows_v1.0.0.zip`

## 📋 What's Included

The Windows bundle includes:

- ✅ **Manual webdriver download instructions** - Step-by-step guide for downloading EdgeDriver
- ✅ **Enhanced troubleshooting tools** - Comprehensive diagnostics for webdriver issues
- ✅ **Network issue solutions** - Solutions for corporate firewall/DNS issues
- ✅ **Placeholder files** - Shows expected webdriver structure
- ✅ **Standard setup script** - `setup_windows.bat` for easy installation

## 🔧 Manual WebDriver Setup

Since automatic webdriver downloads often fail in corporate environments, the bundle includes manual download instructions:

1. **Download EdgeDriver** from: https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/
2. **Extract** the ZIP file
3. **Copy** `msedgedriver.exe` to the `drivers\` directory
4. **Rename** to create multiple versions as needed
5. **Run** `setup_windows.bat` to complete setup

## 🎯 Key Features

- **No network dependencies** for webdriver setup
- **Corporate environment compatible**
- **Handles DNS resolution issues**
- **Bypasses firewall restrictions**
- **Multiple download sources provided**

## 📁 Bundle Contents

```
CoupaDownloads_Windows_v1.0.0/
├── setup_windows.bat                    # Main setup script
├── manual_webdriver_download.bat        # Manual download guide
├── troubleshoot_webdriver_enhanced.bat  # Enhanced troubleshooting
├── NETWORK_ISSUE_SOLUTION.md           # Network issue solutions
├── requirements.txt                     # Python dependencies
├── drivers/                             # WebDriver directory
│   ├── msedgedriver.exe                # Placeholder files
│   ├── msedgedriver_120.exe
│   ├── msedgedriver_119.exe
│   └── msedgedriver_118.exe
├── src/                                 # Application source
└── data/                                # Data directory
```

## 🎉 Success Story

This solution successfully resolved webdriver download issues for a Windows user who encountered:

```
Failed to resolve 'msedgedriver.azureedge.net' ([Errno 11001] getaddrinfo failed)
```

The user was able to:

1. Download EdgeDriver 138 manually
2. Set it as the default driver
3. Successfully run the application

## 📞 Support

If you encounter issues:

1. Run `troubleshoot_webdriver_enhanced.bat`
2. Follow the manual download instructions
3. Check `NETWORK_ISSUE_SOLUTION.md` for detailed guidance

---

**Single Method Solution** - Streamlined Windows bundle creation with manual webdriver handling
