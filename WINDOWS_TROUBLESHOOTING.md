# 🚀 Windows Troubleshooting Guide for CoupaDownloads

## 🎯 Quick Diagnosis

Let's identify what specific issue you're encountering:

### **Common Issues & Solutions:**

## 1. ❌ Python Not Found

**Symptoms:**
```
'python' is not recognized as an internal or external command
```

**Solution:**
1. **Download Python** from [python.org](https://www.python.org/downloads/)
2. **During installation**, check ✅ "Add Python to PATH"
3. **Restart Command Prompt** after installation
4. **Verify installation:**
   ```cmd
   python --version
   ```

## 2. ❌ pip Not Available

**Symptoms:**
```
'pip' is not recognized as an internal or external command
```

**Solution:**
```cmd
# Try these commands:
python -m pip --version
# OR
py -m pip --version
```

## 3. ❌ Virtual Environment Issues

**Symptoms:**
```
Failed to create virtual environment
```

**Solution:**
```cmd
# Remove existing venv and recreate
rmdir /s /q venv
python -m venv venv
venv\Scripts\activate
```

## 4. ❌ Permission Errors

**Symptoms:**
```
Access is denied
```

**Solution:**
1. **Run Command Prompt as Administrator**
2. **Or run PowerShell as Administrator:**
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

## 5. ❌ Edge Browser Issues

**Symptoms:**
```
Edge browser not found
```

**Solution:**
1. **Install Microsoft Edge** from [microsoft.com/edge](https://www.microsoft.com/edge)
2. **Update Edge** to latest version
3. **Verify installation:**
   ```cmd
   start msedge
   ```

## 6. ❌ Network/Firewall Issues

**Symptoms:**
```
Failed to download EdgeDriver
```

**Solution:**
1. **Check internet connection**
2. **Disable antivirus temporarily**
3. **Add project folder to antivirus exclusions**
4. **Use VPN if behind corporate firewall**

## 🛠️ Step-by-Step Windows Setup

### **Method 1: One-Click Installation (Recommended)**

1. **Download the project** ZIP file
2. **Extract** to `C:\CoupaDownloads`
3. **Right-click** `install_windows.bat`
4. **Select** "Run as administrator"
5. **Wait** for installation to complete

### **Method 2: Manual Installation**

```cmd
# 1. Open Command Prompt as Administrator
# 2. Navigate to project folder
cd C:\CoupaDownloads

# 3. Check Python
python --version

# 4. Create virtual environment
python -m venv venv

# 5. Activate virtual environment
venv\Scripts\activate

# 6. Install dependencies
pip install -r requirements.txt

# 7. Create directories
mkdir data\input
mkdir data\output
mkdir data\backups

# 8. Create sample input file
echo PO_NUMBER > data\input\input.csv
echo PO15262984 >> data\input\input.csv
```

### **Method 3: PowerShell Installation**

```powershell
# 1. Open PowerShell as Administrator
# 2. Set execution policy
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 3. Navigate to project
cd C:\CoupaDownloads

# 4. Run PowerShell installer
.\install_windows.ps1
```

## 🔍 Diagnostic Commands

Run these commands to check your setup:

```cmd
# Check Python
python --version

# Check pip
pip --version

# Check Edge (Windows)
powershell -Command "(Get-AppxPackage Microsoft.MicrosoftEdge.Stable).Version"

# Check if venv exists
dir venv

# Check if drivers folder exists
dir drivers

# Check if input file exists
dir data\input\input.csv
```

## 🚨 Common Error Messages & Fixes

### **Error: "Microsoft Edge not found"**
```cmd
# Install Edge from Microsoft Store or download from microsoft.com/edge
```

### **Error: "EdgeDriver download failed"**
```cmd
# Check internet connection
# Try running as administrator
# Disable antivirus temporarily
```

### **Error: "Permission denied"**
```cmd
# Run Command Prompt as Administrator
# Or use PowerShell with execution policy
```

### **Error: "Virtual environment activation failed"**
```cmd
# Delete and recreate venv
rmdir /s /q venv
python -m venv venv
venv\Scripts\activate
```

## 🎯 Testing Your Setup

After installation, test with these commands:

```cmd
# 1. Activate virtual environment
venv\Scripts\activate

# 2. Test Python imports
python -c "import selenium; print('Selenium OK')"
python -c "import pandas; print('Pandas OK')"
python -c "import openpyxl; print('OpenPyXL OK')"

# 3. Test driver manager
python -c "from src.core.driver_manager import DriverManager; dm = DriverManager(); print('Driver Manager OK')"

# 4. Run the application
python src\main.py
```

## 📞 Getting Help

If you're still having issues:

1. **Run diagnostic commands** above
2. **Take screenshots** of error messages
3. **Note your Windows version** (`winver` command)
4. **Note your Python version** (`python --version`)
5. **Note your Edge version** (from Edge browser settings)

## 🔧 Advanced Troubleshooting

### **Reset Everything:**
```cmd
# Remove all generated files
rmdir /s /q venv
rmdir /s /q drivers
rmdir /s /q build
rmdir /s /q __pycache__
del /q *.pyc

# Reinstall from scratch
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### **Use Different Python Version:**
```cmd
# If Python 3.8+ doesn't work, try Python 3.11
# Download from python.org and reinstall
```

### **Alternative: Use Portable Python:**
```cmd
# Download portable Python from python.org
# Extract to project folder
# Use portable Python instead of system Python
```

## 🎉 Success Indicators

You'll know it's working when:

✅ **Python version shows** (3.8 or higher)  
✅ **Virtual environment activates** (shows `(venv)` in prompt)  
✅ **Dependencies install** without errors  
✅ **EdgeDriver downloads** automatically  
✅ **Browser opens** when running `python src\main.py`  

---

**Need more help?** Share the specific error message you're seeing and I'll provide targeted assistance! 