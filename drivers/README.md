# WebDriver Information - Offline Bundle

## 🎯 Included WebDrivers

This bundle includes the following Microsoft Edge WebDrivers:

- `msedgedriver` - macOS/Linux driver (Edge 120+)
- `msedgedriver.exe` - Windows driver (Edge 120+)

## ✅ Automatic Driver Management

The application uses intelligent driver management that:

1. **Scans local drivers** - Checks for compatible drivers in the `drivers/` directory
2. **Detects Edge version** - Automatically detects your installed Edge browser version
3. **Downloads if needed** - Falls back to web download if no compatible local driver is found
4. **Verifies compatibility** - Tests drivers before use to ensure they work

## 🚨 Troubleshooting

### WebDriver Not Found
If you see "No webdrivers found in bundle":
1. Check that all files were extracted properly
2. Ensure the `drivers/` directory exists
3. Verify webdriver files are present
4. Run the validation script: `python src/utils/validate_setup.py`

### Permission Issues
- **macOS**: Run `chmod +x drivers/msedgedriver`
- **Linux**: Run `chmod +x drivers/msedgedriver`
- **Windows**: Run setup script as **Administrator**

### Edge Browser Issues
- Ensure Microsoft Edge is installed
- Update Edge to latest version
- Clear browser cache if needed

## 🔄 Updating WebDrivers

The application will automatically:
1. Detect your Edge version
2. Download compatible drivers if needed
3. Verify and use the best available driver

For manual updates:
1. Download new driver from: https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/
2. Replace files in `drivers/` directory
3. Ensure proper permissions (executable on macOS/Linux)

## 🎉 Success Indicators

✅ Setup validation passes
✅ Webdriver files found and executable
✅ Application starts successfully
✅ Downloads begin processing

---

**Offline Bundle v1.0** - Intelligent driver management for network-restricted environments.
