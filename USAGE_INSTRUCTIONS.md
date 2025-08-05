# Coupa PO Attachment Downloader - User Guide

## Overview

The Coupa PO Attachment Downloader is an automated tool that downloads attachments (PDF, MSG, DOCX) from Coupa Purchase Orders. It processes multiple POs in batch, automatically renames files with PO prefixes, and generates detailed reports.

## What You Need Before Starting

- **Coupa Access**: Valid login credentials for your Coupa instance
- **Python**: Python 3.7 or higher installed on your computer
- **Internet Connection**: Stable internet connection for downloading files
- **PO Numbers**: List of Purchase Order numbers you want to process

## Step-by-Step Instructions

### Step 1: Prepare Your PO Numbers

1. **Open the input file**: Navigate to `data/input/input.csv`
2. **Add your PO numbers**: Replace the existing content with your PO numbers
3. **Save the file**: Ensure the file is saved with the correct format

**Example format:**

```csv
PO_NUMBER
PO15262984
PO15327452
PO15362783
```

**Important Notes:**

- One PO number per line
- Include the "PO" prefix
- No extra spaces or special characters
- The tool will automatically clean and validate your PO numbers

### Step 2: Install Required Libraries

1. **Open Terminal/Command Prompt**
2. **Navigate to the project folder**: `cd /path/to/CoupaDownloads`
3. **Install Python dependencies**: `pip install -r requirements.txt`
4. **Wait for installation to complete**

### Step 3: Configure Settings (Optional)

The tool works with default settings, but you can customize:

**Environment Variables (Optional):**

- `PROCESS_MAX_POS=10` - Limit to first 10 POs (useful for testing)
- `HEADLESS=true` - Run without browser window (advanced users)
- `LOGIN_TIMEOUT=60` - Login detection timeout in seconds

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

1. **Start the tool**: `python src/main.py`
2. **Wait for browser to open**: The tool will automatically launch Microsoft Edge
3. **Login to Coupa**:
   - The browser will navigate to Coupa
   - Log in manually if prompted
   - The tool will automatically detect when you're logged in
4. **Monitor progress**: Watch the terminal for real-time updates

### Step 5: Monitor the Process

The tool will show you:

```
🔐 Checking login status...
🌐 Navigating to Coupa homepage...
✅ Already logged in - proceeding with downloads

🎯 Processing 3 POs after successful login...

📋 Processing PO #PO15262984 (1/3)...
📎 Found 2 attachments
✅ Downloaded: PO15262984_invoice.pdf
✅ Downloaded: PO15262984_contract.docx

📋 Processing PO #PO15327452 (2/3)...
📎 Found 1 attachment
✅ Downloaded: PO15327452_specification.pdf
```

### Step 6: Find Your Downloads

**Download Location**: `~/Downloads/CoupaDownloads/`

**File Organization:**

- Files are automatically renamed with PO prefixes
- Example: `PO15262984_invoice.pdf`
- All supported file types: PDF, MSG, DOCX

**Folder Structure:**

```
~/Downloads/CoupaDownloads/
├── PO15262984_invoice.pdf
├── PO15262984_contract.docx
├── PO15327452_specification.pdf
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
- CSV processing tests: Input file validation

## Troubleshooting

### Common Issues and Solutions

**1. "No valid PO numbers provided"**

- Check your `data/input/input.csv` file format
- Ensure PO numbers include the "PO" prefix
- Remove any extra spaces or special characters

**2. "Login failed"**

- Ensure you have valid Coupa credentials
- Check your internet connection
- Try logging into Coupa manually first
- Increase `LOGIN_TIMEOUT` if needed

**3. "Browser not starting"**

- Ensure Microsoft Edge is installed
- Check that the WebDriver is in the `drivers/` folder
- Try running without headless mode: `export HEADLESS=false`

**4. "Downloads not appearing"**

- Check the download folder: `~/Downloads/CoupaDownloads/`
- Ensure you have write permissions
- Check if antivirus software is blocking downloads

**5. "Slow performance"**

- Reduce the number of POs processed: `export PROCESS_MAX_POS=10`
- Check your internet connection speed
- Close other browser tabs and applications

### Error Messages Explained

- **"PO number not found"**: The PO doesn't exist or you don't have access
- **"No attachments found"**: The PO exists but has no downloadable attachments
- **"Download timeout"**: The file took too long to download
- **"Browser session lost"**: The browser crashed or was closed unexpectedly

## Performance Tips

1. **Start Small**: Test with 5-10 POs first
2. **Stable Connection**: Use a reliable internet connection
3. **Close Other Apps**: Free up system resources
4. **Regular Breaks**: For large batches, the tool handles breaks automatically
5. **Monitor Resources**: Check CPU and memory usage during processing

## File Types Supported

- **PDF files**: Invoices, contracts, specifications
- **MSG files**: Email attachments
- **DOCX files**: Word documents, contracts, specifications

## Safety Features

- **Automatic cleanup**: Browser processes are properly closed
- **Error recovery**: The tool continues processing even if individual POs fail
- **Session management**: Handles login timeouts and browser crashes
- **File validation**: Only downloads supported file types
- **Progress tracking**: Detailed logging of all operations

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
# Install dependencies
pip install -r requirements.txt

# Run the tool
python src/main.py

# Run tests
python run_tests.py

# Limit processing (testing)
export PROCESS_MAX_POS=5 && python src/main.py
```

**Key Files:**

- `data/input/input.csv` - Your PO numbers
- `data/output/` - Generated reports
- `~/Downloads/CoupaDownloads/` - Downloaded files
- `tests/` - Telemetry and test data

**Environment Variables:**

- `PROCESS_MAX_POS` - Limit number of POs
- `HEADLESS` - Run without browser window
- `LOGIN_TIMEOUT` - Login detection timeout

That's it! The tool handles everything else automatically. Enjoy your automated Coupa downloads!
