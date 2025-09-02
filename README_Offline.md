# CoupaDownloads - Offline Windows Bundle

## 🚀 Quick Start (No Internet Required)

1. **Extract** this ZIP file to a folder
2. **Run** `setup_windows_offline.bat` as Administrator
3. **Edit** `data/input/input.csv` with your PO numbers
4. **Run** `python src/main.py`

## 🎯 Offline Features

### ✅ Pre-included WebDrivers
This bundle includes multiple EdgeDriver versions:
- `msedgedriver.exe` (default)
- `msedgedriver_120.exe` (Edge 120)
- `msedgedriver_119.exe` (Edge 119)
- `msedgedriver_118.exe` (Edge 118)

### 🌐 No Network Dependencies
- **No webdriver downloads** during setup
- **No internet required** for webdriver setup
- **Works in restricted networks** (corporate firewalls, proxies)
- **Eliminates DNS resolution issues**

### 🛠️ Enhanced Reliability
- Pre-tested webdriver compatibility
- Multiple driver versions included
- Automatic fallback mechanisms
- Comprehensive error handling

## 📋 Requirements

- **Windows 10/11** (64-bit)
- **Python 3.8+** (automatically detected)
- **Microsoft Edge** browser
- **No internet connection required** for setup

## 🚨 Common Issues Solved

### ❌ Network Resolution Errors
**Problem:** `Failed to resolve 'msedgedriver.azureedge.net'`
**Solution:** ✅ Pre-included webdrivers - no network needed

### ❌ Corporate Firewall Blocks
**Problem:** Downloads blocked by corporate security
**Solution:** ✅ Offline bundle - no external downloads

### ❌ Proxy Configuration Issues
**Problem:** Proxy settings interfere with downloads
**Solution:** ✅ No network dependencies

### ❌ DNS Resolution Failures
**Problem:** `getaddrinfo failed` errors
**Solution:** ✅ Local webdrivers - no DNS lookups

## 📁 Package Contents

```
CoupaDownloads_Windows_Offline/
├── setup_windows_offline.bat    # Offline setup script
├── requirements.txt              # Python dependencies
├── drivers/                      # Pre-included WebDrivers
│   ├── msedgedriver.exe         # Default driver
│   ├── msedgedriver_120.exe     # Edge 120 driver
│   ├── msedgedriver_119.exe     # Edge 119 driver
│   ├── msedgedriver_118.exe     # Edge 118 driver
│   └── README.md                # Driver documentation
├── src/                          # Application source
├── data/                         # Data directory
│   ├── input/                   # Input files
│   └── output/                  # Output files
└── README.md                     # This file
```

## 🎯 Usage

### First Time Setup
```bash
# Run offline setup (as Administrator)
setup_windows_offline.bat

# Activate virtual environment
venv\Scripts\activate

# Edit input file
notepad data\input\input.csv

# Run application
python src\main.py
```

### Regular Usage
```bash
# Activate virtual environment
venv\Scripts\activate

# Run application
python src\main.py
```

## 🔧 Troubleshooting

### Setup Issues
1. **Run as Administrator** - Required for webdriver setup
2. **Check Python installation** - Must be in PATH
3. **Verify webdriver files** - Should be in `drivers/` directory

### Runtime Issues
1. **Edge browser required** - Install Microsoft Edge
2. **Permission issues** - Add `drivers/` to antivirus exclusions
3. **Driver compatibility** - Update Edge browser if needed

### Network Issues
1. **No network required** - This is an offline bundle
2. **If internet needed** - Only for Coupa website access
3. **Proxy settings** - May be needed for Coupa access

## 🔄 Updates

### WebDriver Updates
```bash
# Manual update (requires internet)
download_drivers.bat

# Or download from:
# https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/
```

### Application Updates
- Download new offline bundle
- Extract and run setup
- Migrate your input files

## 📞 Support

### Offline Bundle Issues
1. Check `drivers/README.md` for webdriver troubleshooting
2. Verify all files were extracted properly
3. Ensure Microsoft Edge is installed
4. Run setup as Administrator

### Network Issues
- This bundle is designed for offline use
- No network dependencies for setup
- Only Coupa website access requires internet

## 🎉 Success Indicators

✅ Setup completes without network errors
✅ Webdriver files found in bundle
✅ Application starts successfully
✅ Downloads begin processing
✅ No DNS resolution errors

---

**Offline Windows Bundle v1.0** - Designed for network-restricted environments with pre-included webdrivers.
