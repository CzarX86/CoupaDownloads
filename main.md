# Main Module Documentation

## Overview

The `main.py` file is the **orchestrator** of the entire Coupa Downloads automation project. Think of it as the "conductor" of an orchestra - it doesn't play the instruments itself, but it coordinates all the other parts to work together harmoniously.

## What This Project Does

This project automates the process of downloading attachments from Coupa (a procurement system) for multiple Purchase Orders (POs). Here's what it does in plain English:

1. **Reads a list of PO numbers** from a CSV file
2. **Opens a web browser** (Microsoft Edge) automatically
3. **Navigates to each PO page** in Coupa
4. **Detects if you need to log in** and waits for you to do so
5. **Finds all attachments** on each PO page
6. **Downloads the attachments** to your computer
7. **Renames the files** with the PO number as a prefix
8. **Cleans up** by closing the browser properly

## The Main Class: CoupaDownloader

The `CoupaDownloader` class is the heart of the application. It follows the **Single Responsibility Principle** - its only job is to coordinate the workflow.

### How It Works (Step by Step)

#### 1. Initialization (`__init__`)
```python
def __init__(self):
    self.browser_manager = BrowserManager()
    self.driver = None
    self.download_manager = None
    self.login_manager = None
```

**In Plain English:** When we create a new downloader, we prepare all the tools we'll need:
- A browser manager (to handle the web browser)
- A download manager (to handle file downloads)
- A login manager (to handle login detection)
- We start with no browser open yet

#### 2. Setup (`setup`)
```python
def setup(self) -> None:
    Config.ensure_download_folder_exists()
    self.driver = self.browser_manager.start(headless=Config.HEADLESS)
    self.download_manager = DownloadManager(self.driver)
    self.login_manager = LoginManager(self.driver)
```

**In Plain English:** This is like preparing your workspace:
- Make sure the download folder exists
- Start the web browser (either visible or hidden)
- Create the download and login managers

#### 3. Process PO Numbers (`process_po_numbers`)
```python
def process_po_numbers(self) -> list:
    csv_file_path = CSVProcessor.get_csv_file_path()
    po_entries = CSVProcessor.read_po_numbers_from_csv(csv_file_path)
    valid_entries = CSVProcessor.process_po_numbers(po_entries)
```

**In Plain English:** This reads and validates the PO numbers:
- Find the CSV file with PO numbers
- Read all the PO numbers from the file
- Check which ones are valid (proper format)
- Return the list of valid POs to process

#### 4. Download Attachments (`download_attachments`)
```python
def download_attachments(self, valid_entries: list) -> None:
    for display_po, clean_po in valid_entries:
        self.login_manager.ensure_logged_in()
        self.download_manager.download_attachments_for_po(display_po, clean_po)
```

**In Plain English:** This is the main work loop:
- For each PO number in our list:
  - Make sure we're logged in
  - Download all attachments for that PO

#### 5. Main Execution (`run`)
```python
def run(self) -> None:
    try:
        self.setup()
        valid_entries = self.process_po_numbers()
        if not valid_entries:
            return
        self.download_attachments(valid_entries)
    except KeyboardInterrupt:
        print("\nScript interrupted by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        self.browser_manager.cleanup()
```

**In Plain English:** This is the complete workflow:
- Set up everything we need
- Get the list of PO numbers to process
- If we have valid POs, download their attachments
- If anything goes wrong, handle it gracefully
- Always clean up the browser when we're done

## Key Libraries Used

### 1. **Selenium** (`from selenium import webdriver`)
- **What it is:** A library for controlling web browsers programmatically
- **Why we use it:** To automate clicking, typing, and navigating websites
- **Think of it as:** A robot that can use a web browser just like you do

### 2. **Our Custom Modules**
- **`browser`**: Handles starting and stopping the web browser
- **`config`**: Contains all the settings and configuration
- **`csv_processor`**: Reads and processes the CSV file with PO numbers
- **`downloader`**: Handles the actual downloading of files

## Error Handling

The code includes several types of error handling:

1. **Keyboard Interrupt**: If you press Ctrl+C, it stops gracefully
2. **General Exceptions**: If something unexpected happens, it shows an error message
3. **Finally Block**: No matter what happens, it always cleans up the browser

## Headless Mode

The script supports "headless" mode, which means the browser runs in the background without showing a window. This is controlled by the `HEADLESS` environment variable.

## The Main Function

```python
def main() -> None:
    downloader = CoupaDownloader()
    downloader.run()
```

**In Plain English:** This is the entry point - when you run the script, it creates a downloader and starts the whole process.

## How to Use

1. **Prepare your CSV file** with PO numbers
2. **Run the script**: `python main.py`
3. **Log in manually** if prompted
4. **Wait for completion** - the script will handle everything else

## Project Architecture

This project follows **SOLID principles** and **clean code** practices:

- **Single Responsibility**: Each module has one clear purpose
- **Open/Closed**: Easy to extend without changing existing code
- **Dependency Inversion**: High-level code doesn't depend on low-level details
- **Interface Segregation**: Clean, focused interfaces
- **Liskov Substitution**: Components can be easily replaced

The main module is intentionally **lean** (only 87 lines) because it delegates specific tasks to specialized modules, making the code more maintainable and testable.
