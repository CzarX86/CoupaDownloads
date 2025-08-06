# Network Issue Solution Guide

## 🚨 Problem: Network Resolution Errors

If you see errors like:
```
Failed to resolve 'msedgedriver.azureedge.net'
getaddrinfo failed
DNS resolution error
```

## ✅ Solution: Manual WebDriver Download

### Step 1: Download WebDriver
1. **Open your web browser**
2. **Go to:** https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/
3. **Click:** "Download" for Windows (64-bit)
4. **Save** the ZIP file

### Step 2: Extract and Install
1. **Extract** the ZIP file
2. **Copy** `msedgedriver.exe` to the `drivers\` directory
3. **Rename** to create multiple versions:
   ```
   drivers   ├── msedgedriver.exe          (default)
   ├── msedgedriver_120.exe      (Edge 120)
   ├── msedgedriver_119.exe      (Edge 119)
   └── msedgedriver_118.exe      (Edge 118)
   ```

### Step 3: Verify Installation
1. **Run:** `setup_windows.bat`
2. **Check:** Webdriver detection
3. **Test:** Application startup

## 🔧 Alternative Download Sources

If Microsoft site is blocked:

### Option 1: GitHub Releases
- Visit: https://github.com/microsoft/edge-selenium-tools/releases
- Download latest Windows release

### Option 2: Selenium Downloads
- Visit: https://selenium.dev/downloads/
- Download EdgeDriver for Windows

### Option 3: ChromeDriver (Fallback)
- Visit: https://chromedriver.chromium.org/downloads
- Download ChromeDriver (may work with Edge)

## 🚨 Common Network Issues

### Corporate Firewall
- **Problem:** Downloads blocked by corporate security
- **Solution:** Download from home/outside network
- **Alternative:** Contact IT for webdriver access

### DNS Resolution
- **Problem:** `getaddrinfo failed` errors
- **Solution:** Manual download bypasses DNS
- **Alternative:** Use different DNS servers

### Proxy Configuration
- **Problem:** Proxy interferes with downloads
- **Solution:** Manual download bypasses proxy
- **Alternative:** Configure proxy settings

### Network Timeouts
- **Problem:** Downloads timeout or fail
- **Solution:** Manual download is more reliable
- **Alternative:** Try during off-peak hours

## 📋 Verification Steps

After manual download:

1. **Check files exist:**
   ```bash
   dir drivers\msedgedriver*.exe
   ```

2. **Test webdriver:**
   ```bash
   drivers\msedgedriver.exe --version
   ```

3. **Run setup:**
   ```bash
   setup_windows.bat
   ```

4. **Test application:**
   ```bash
   python src\main.py
   ```

## 🎉 Success Indicators

✅ Webdriver files found in `drivers\` directory
✅ Setup completes without network errors
✅ Application starts successfully
✅ Downloads begin processing
✅ No DNS resolution errors

## 📞 Support

If manual download also fails:
1. Check internet connectivity
2. Try different download sources
3. Contact your network administrator
4. Use a different network (mobile hotspot, etc.)

---

**Network Issue Solution v1.0** - Manual webdriver download for network-restricted environments.
