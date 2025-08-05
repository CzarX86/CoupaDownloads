# Coupa PO Attachment Downloader - User Guide

## Overview

The Coupa PO Attachment Downloader is an automated tool that downloads attachments from Coupa Purchase Orders. It processes multiple POs in batch, automatically renames files with PO prefixes, converts MSG files to PDF format, extracts email attachments, and generates detailed Excel reports with comprehensive analytics.

## What You Need Before Starting

- **Coupa Access**: Valid login credentials for your Coupa instance
- **Python**: Python 3.7 or higher installed on your computer
- **Microsoft Edge**: Latest version of Microsoft Edge browser
- **Internet Connection**: Stable internet connection for downloading files
- **PO Numbers**: List of Purchase Order numbers you want to process

## Step-by-Step Instructions

### Step 1: Prepare Your PO Numbers

You can use either CSV or Excel format for your input file. The tool automatically detects which format you're using.

#### Option A: Excel Format (Recommended)

1. **Open the input file**: Navigate to `data/input/input.xlsx`
2. **Add your PO numbers**: Replace the existing content with your PO numbers
3. **Save the file**: Ensure the file is saved in Excel format (.xlsx)

#### Option B: CSV Format

1. **Open the input file**: Navigate to `data/input/input.csv`
2. **Add your PO numbers**: Replace the existing content with your PO numbers
3. **Save the file**: Ensure the file is saved with the correct format

**Example format (both CSV and Excel):**

```
PO_NUMBER
PO15262984
PO15327452
PO15362783
```

**Important Notes:**

- One PO number per line
- Include the "PO" prefix
- No extra spaces or special characters
- The tool will automatically detect and use whichever file format you provide
- The tool will automatically clean and validate your PO numbers
- Input files are automatically backed up before processing

### Step 2: Install Required Libraries

#### Option A: Automatic Installation (Recommended)

**Windows:**

- Double-click `install_windows.bat` OR
- Right-click `install_windows.ps1` → "Run with PowerShell"

**All Platforms:**

- Run: `python install.py`

#### Option B: Manual Installation

1. **Open Terminal/Command Prompt**
2. **Navigate to the project folder**: `cd /path/to/CoupaDownloads`
3. **Create virtual environment**: `python -m venv venv`
4. **Activate virtual environment**:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
5. **Install Python dependencies**: `pip install -r requirements.txt`
6. **Wait for installation to complete**

**Note**: The automatic installation will handle everything for you, including:

- Creating virtual environment
- Installing Python dependencies
- Downloading the correct EdgeDriver for your system
- Setting up necessary directories
- Creating sample input files

### Step 3: Configure Settings (Optional)

The tool works with default settings, but you can customize:

**Environment Variables (Optional):**

- `PROCESS_MAX_POS=10` - Limit to first 10 POs (useful for testing)
- `HEADLESS=true` - Run without browser window (advanced users)
- `LOGIN_TIMEOUT=60` - Login detection timeout in seconds
- `VERBOSE_OUTPUT=true` - Show detailed processing information
- `SHOW_DETAILED_PROCESSING=true` - Show step-by-step processing details
- `SHOW_SELENIUM_LOGS=true` - Show browser automation logs

**Example (macOS/Linux):**

```bash
export PROCESS_MAX_POS=5
python src/main.py
```

**Example (Windows):**

```cmd
set PROCESS_MAX_POS=5
python src/main.py
```

### Step 4: Run the Downloader

1. **Activate virtual environment** (if using manual installation):
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
2. **Start the tool**: `python src/main.py`
3. **Wait for browser to open**: The tool will automatically launch Microsoft Edge
4. **Login to Coupa**:
   - The browser will navigate to Coupa
   - Log in manually if prompted
   - The tool will automatically detect when you're logged in
5. **Choose MSG processing option**: The tool will ask if you want to automatically process MSG files
6. **Monitor progress**: Watch the terminal for real-time updates

**Note**: If you used automatic installation, the virtual environment is already activated.

**Automatic EdgeDriver Management**: The tool automatically detects your Microsoft Edge version and downloads the compatible EdgeDriver, so you don't need to manually install or configure it.

### Step 5: MSG File Processing Options

When you run the tool, it will ask about MSG file processing:

```
📧 MSG File Processing Options
========================================
Would you like to automatically process .msg files?
This will:
  • Convert .msg files to PDF format
  • Extract any attachments from .msg files
  • Create subfolders named after the original .msg file
  • Organize attachments in these subfolders

Enable MSG processing? (y/n):
```

**Choose 'y' if you want to:**

- Convert MSG files to readable PDF format
- Extract attachments from within MSG files
- Organize files in subfolders for better organization
- Filter out small artifacts and duplicates

**Choose 'n' if you want to:**

- Download MSG files as-is without processing
- Keep the original file structure

### Step 6: Monitor the Process

The tool provides enhanced progress tracking with time estimates and file size information:

```
🔐 Checking login status...
🌐 Navigating to Coupa homepage...
✅ Already logged in - proceeding with downloads

📧 MSG File Processing Options
========================================
Would you like to automatically process .msg files?
Enable MSG processing? (y/n): y
✅ MSG processing enabled

🚀 Starting processing of 3 POs...

📋 PO15262984...........67% | 2m 15s elapsed | ~1m 10s remaining
   📎 2 file(s) found
   📥 Starting download of 2 file(s)...
   ✅ PO15262984_invoice.pdf 2.3MB/2.3MB (100%)
   ✅ PO15262984_contract.docx 1.1MB/1.1MB (100%)

📋 PO15327452...........89% | 3m 25s elapsed | ~0m 25s remaining
   📎 1 file(s) found
   📥 Starting download of 1 file(s)...
   ✅ PO15327452_specification.pdf 5.7MB/5.7MB (100%)
```

### Step 7: Find Your Downloads

**Download Location**: `~/Downloads/CoupaDownloads/`

**File Organization:**

- Files are automatically renamed with PO prefixes
- Example: `PO15262984_invoice.pdf`
- All file types are supported by default (PDF, MSG, DOCX, XLSX, TXT, JPG, PNG, ZIP, RAR, CSV, XML)

**If MSG processing was enabled:**

```
~/Downloads/CoupaDownloads/
├── PO15262984_invoice.pdf
├── PO15262984_contract.docx
├── PO15327452_specification.pdf
├── PO15327452_email.msg/
│   ├── PO15327452_MSG_email.pdf
│   ├── PO15327452_MSG_email.msg
│   ├── attachment1.pdf
│   └── attachment2.docx
└── ...
```

## Advanced Features

### Excel Report Generation

The tool automatically generates detailed Excel reports:

**Location**: `data/output/coupa_report_YYYYMMDD_HHMMSS.xlsx`

**Report Contents:**

- PO numbers processed
- Number of attachments found
- Number of attachments downloaded
- Processing status (Success/Failed)
- Error messages (if any)
- Processing timestamps
- Download folder locations
- Supplier information (when available)
- File sizes and types
- Processing duration per PO

### Enhanced Progress Tracking

The tool provides comprehensive real-time progress updates:

- **Overall progress**: Shows current PO and total count with time estimates
- **Individual PO progress**: Shows attachments found and downloaded with file sizes
- **Time tracking**: Shows elapsed time and estimated remaining time
- **File size progress**: Shows download progress with file sizes
- **Error handling**: Continues processing even if individual POs fail
- **Session recovery**: Automatically recovers from browser crashes
- **Performance metrics**: Tracks processing speed and efficiency

### MSG File Processing

When enabled, the tool provides advanced MSG processing:

- **Convert MSG to PDF**: Makes email files readable using multiple conversion methods
- **Extract attachments**: Pulls out files embedded in emails
- **Organize files**: Creates subfolders for better organization
- **Filter artifacts**: Removes small files and duplicates based on configurable size thresholds
- **Multiple conversion methods**: Uses LibreOffice, Python libraries, or fallback methods
- **Consistent naming**: Maintains consistent file naming conventions

### Browser Session Management

The tool includes robust browser session handling:

- **Automatic login detection**: Detects when you're logged in
- **Session persistence**: Maintains login across browser restarts
- **Crash recovery**: Automatically recovers from browser crashes
- **Profile management**: Uses your existing Edge profile for persistent sessions
- **Homepage parking**: Returns browser to Coupa homepage after processing

### Telemetry and Analytics

The tool tracks detailed performance metrics:

**Files Generated:**

- `tests/download_telemetry_summary.csv` - Overall performance summary
- `tests/download_telemetry_details.csv` - Detailed step-by-step metrics

**Metrics Tracked:**

- Page load times
- Download success rates
- Error frequencies
- Processing durations
- Browser performance data
- File size distributions
- Processing efficiency metrics

### Testing and Validation

**Run Tests (Optional):**

```bash
# Run all tests
python run_tests.py

# Run specific test types
python run_tests.py --type unit
python run_tests.py --type integration
python run_tests.py --type fast
```

**Test Categories:**

- Unit tests: Individual function testing
- Integration tests: Complete workflow testing
- File operation tests: Download and renaming validation
- CSV/Excel processing tests: Input file validation
- MSG processing tests: Email conversion and attachment extraction
- Browser automation tests: Login and navigation validation

## Troubleshooting

### Common Issues and Solutions

**1. "No valid PO numbers provided"**

- Check your `data/input/input.csv` or `data/input/input.xlsx` file format
- Ensure PO numbers include the "PO" prefix
- Remove any extra spaces or special characters

**2. "Login failed"**

- Ensure you have valid Coupa credentials
- Check your internet connection
- Try logging into Coupa manually first
- Increase `LOGIN_TIMEOUT` if needed

**3. "Browser not starting"**

- Ensure Microsoft Edge is installed
- The tool automatically downloads the correct EdgeDriver for your system
- If automatic download fails, check your internet connection
- Try running without headless mode: `export HEADLESS=false`

**4. "Downloads not appearing"**

- Check the download folder: `~/Downloads/CoupaDownloads/`
- Ensure you have write permissions
- Check if antivirus software is blocking downloads

**5. "Slow performance"**

- Reduce the number of POs processed: `export PROCESS_MAX_POS=10`
- Check your internet connection speed
- Close other browser tabs and applications

**6. "MSG processing errors"**

- Ensure you have the required dependencies installed
- Check if the MSG file is corrupted
- Try processing without MSG conversion first
- Check if LibreOffice is installed for better conversion

**7. "Browser session lost"**

- The tool automatically attempts to recover browser sessions
- If recovery fails, restart the tool
- Check your internet connection stability

### Error Messages Explained

- **"PO number not found"**: The PO doesn't exist or you don't have access
- **"No attachments found"**: The PO exists but has no downloadable attachments
- **"Download timeout"**: The file took too long to download
- **"Browser session lost"**: The browser crashed or was closed unexpectedly
- **"MSG conversion failed"**: The MSG file couldn't be converted to PDF
- **"Session recovery failed"**: Could not restore browser session after crash

## Performance Tips

1. **Start Small**: Test with 5-10 POs first
2. **Stable Connection**: Use a reliable internet connection
3. **Close Other Apps**: Free up system resources
4. **Regular Breaks**: For large batches, the tool handles breaks automatically
5. **Monitor Resources**: Check CPU and memory usage during processing
6. **MSG Processing**: Only enable if you need email conversion (adds processing time)
7. **Browser Settings**: Keep browser updated for best performance

## File Types Supported

The tool supports all common file types by default, including:

- **PDF files**: Invoices, contracts, specifications
- **MSG files**: Email attachments (can be converted to PDF)
- **DOCX files**: Word documents, contracts, specifications
- **XLSX files**: Excel spreadsheets
- **TXT files**: Text documents
- **Image files**: JPG, PNG
- **Archive files**: ZIP, RAR
- **Data files**: CSV, XML

**Note**: You can restrict file types by modifying the configuration if needed.

## Safety Features

- **Automatic cleanup**: Browser processes are properly closed
- **Error recovery**: The tool continues processing even if individual POs fail
- **Session management**: Handles login timeouts and browser crashes
- **File validation**: Only downloads supported file types
- **Progress tracking**: Detailed logging of all operations
- **Backup creation**: Input files are backed up before processing
- **File organization**: Automatic renaming and folder structure
- **Crash recovery**: Automatic browser session recovery
- **Safe file handling**: Prevents overwriting existing files unless configured

## Support and Maintenance

**Log Files:**

- Check terminal output for detailed error messages
- Review telemetry files for performance analysis
- Excel reports provide processing summaries

**Updates:**

- The tool includes comprehensive testing
- Regular updates improve reliability and performance
- Check the `docs/` folder for technical documentation

## Quick Reference

**Essential Commands:**

```bash
# Automatic installation (recommended)
python install.py

# Manual installation
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Run the tool
python src/main.py

# Run tests
python run_tests.py

# Limit processing (testing)
export PROCESS_MAX_POS=5 && python src/main.py
```

**Key Files:**

- `data/input/input.xlsx` or `data/input/input.csv` - Your PO numbers
- `data/output/` - Generated reports
- `~/Downloads/CoupaDownloads/` - Downloaded files
- `tests/` - Telemetry and test data

**Environment Variables:**

- `PROCESS_MAX_POS` - Limit number of POs
- `HEADLESS` - Run without browser window
- `LOGIN_TIMEOUT` - Login detection timeout
- `VERBOSE_OUTPUT` - Show detailed processing information
- `SHOW_DETAILED_PROCESSING` - Show step-by-step details
- `SHOW_SELENIUM_LOGS` - Show browser automation logs

**Current Features:**

- **Excel Support**: Can read from both CSV and Excel files
- **MSG Processing**: Convert email files to PDF and extract attachments
- **Enhanced Progress**: Real-time progress tracking with time estimates
- **Better Error Handling**: Continues processing even with failures
- **File Type Support**: Handles all common file types
- **Session Recovery**: Automatic browser crash recovery
- **Performance Analytics**: Detailed telemetry and reporting
- **Automatic Setup**: Self-contained installation and configuration

That's it! The tool handles everything else automatically. Enjoy your automated Coupa downloads!
