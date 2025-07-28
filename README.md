# Coupa PO Attachment Downloader

A Selenium-based automation script to download attachments from Coupa Purchase Orders (POs).

## Features

- Downloads attachments (PDF, MSG, DOCX) from Coupa PO pages
- Automatically renames files with PO prefix
- Handles login prompts manually
- Supports batch processing from CSV file

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure the local WebDriver is available:
   - The script uses `drivers/edgedriver_138` (already included)
   - No need to download additional drivers

3. Prepare your PO numbers in `input.csv` (in the same directory as `main.py`):
```csv
PO_NUMBER
PO15262984
PO15327452
```

## Usage

Run the script:
```bash
python main.py
```

The script will:
1. Read PO numbers from `input.csv`
2. Navigate to each PO page
3. **Automatically detect login** - No manual input required
4. Download attachments to `~/Downloads/CoupaDownloads/`
5. Rename files with PO prefix (e.g., `PO15262984_filename.pdf`)

### Login Detection

The script automatically detects successful login by monitoring:
- URL changes (redirects to logged-in pages)
- Page content changes
- Timeout after 60 seconds (configurable via `LOGIN_TIMEOUT`)

### Browser Cleanup

The script ensures clean browser shutdown:
- **Automatic cleanup**: Kills existing Edge processes before starting
- **Graceful shutdown**: Properly closes browser on completion or interruption
- **Signal handling**: Responds to Ctrl+C and system signals
- **Cross-platform**: Works on macOS, Windows, and Linux

## Testing

### Running Tests

The project includes a comprehensive test suite using pytest:

```bash
# Run all tests
python run_tests.py

# Run specific test types
python run_tests.py --type unit
python run_tests.py --type integration
python run_tests.py --type fast

# Run with verbose output
python run_tests.py -v

# Run tests directly with pytest
python -m pytest tests/
```

### Test Categories

- **Unit Tests**: Test individual functions and logic
- **Integration Tests**: Test complete workflows with mocked dependencies
- **File Operation Tests**: Test file handling and renaming
- **CSV Processing Tests**: Test CSV file reading and validation
- **Selenium Integration Tests**: Test web automation components

### Test Coverage

The test suite covers:
- ✅ PO number validation and cleaning
- ✅ CSV file processing
- ✅ File extension validation
- ✅ File renaming operations
- ✅ Error handling scenarios
- ✅ Environment variable parsing
- ✅ URL formatting
- ✅ Local WebDriver functionality
- ✅ Selenium WebDriver mocking
- ✅ Download folder management

## Architecture

The project follows clean code and SOLID principles with modular architecture:

### Modules

- **`config.py`** - Single Responsibility: Configuration management
- **`browser.py`** - Single Responsibility: Browser lifecycle management
- **`downloader.py`** - Single Responsibility: File operations and downloads
- **`csv_processor.py`** - Single Responsibility: CSV file processing
- **`main.py`** - Single Responsibility: Workflow orchestration

### Design Principles

- **Single Responsibility Principle**: Each module has one clear purpose
- **Open/Closed Principle**: Easy to extend without modifying existing code
- **Dependency Inversion**: High-level modules don't depend on low-level modules
- **Interface Segregation**: Clean interfaces between components
- **Liskov Substitution**: Components can be easily replaced

## Configuration

- **Download folder**: `~/Downloads/CoupaDownloads/`
- **Supported file types**: PDF, MSG, DOCX
- **WebDriver**: Uses local `drivers/edgedriver_138` (no internet required)
- **Environment variables**:
  - `PAGE_DELAY`: Debug delay after page load (default: 0)
  - `EDGE_PROFILE_DIR`: Edge browser profile directory (optional)
  - `LOGIN_TIMEOUT`: Login detection timeout in seconds (default: 60)

## Files

- `main.py` - Main orchestrator (lean entry point)
- `config.py` - Configuration and settings
- `browser.py` - Browser management and WebDriver setup
- `downloader.py` - File operations and attachment downloading
- `csv_processor.py` - CSV file reading and PO processing
- `input.csv` - PO numbers to process
- `requirements.txt` - Python dependencies
- `run_tests.py` - Test runner script
- `pytest.ini` - Pytest configuration
- `tests/` - Test suite directory
- `drivers/` - Local WebDriver files (edgedriver_138)

## Project Structure

```
CoupaDownloads/
├── main.py                 # Main orchestrator (lean entry point)
├── config.py               # Configuration and settings
├── browser.py              # Browser management and WebDriver setup
├── downloader.py           # File operations and attachment downloading
├── csv_processor.py        # CSV file reading and PO processing
├── input.csv               # PO numbers to process
├── requirements.txt         # Python dependencies
├── run_tests.py            # Test runner script
├── pytest.ini             # Pytest configuration
├── README.md               # Documentation
├── .gitignore              # Git ignore rules
└── tests/                  # Test suite
    ├── __init__.py
    ├── conftest.py         # Pytest fixtures
    ├── test_utils.py       # Utility function tests
    ├── test_csv_processing.py
    ├── test_file_operations.py
    ├── test_selenium_integration.py
    ├── test_integration.py
    └── test_main_functions.py
``` 