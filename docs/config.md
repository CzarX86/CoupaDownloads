# Config Module Documentation

## Overview

The `config.py` file is the **settings manager** of the project. Think of it as the "control panel" where all the important settings and configurations are stored in one place. Instead of having settings scattered throughout the code, everything is centralized here.

## What This Module Does

This module defines all the configuration settings that the application needs to run. It's like a recipe book that tells the application:
- Where to save downloaded files
- What types of files to download
- How long to wait for things to load
- What browser settings to use
- And many other important settings

## The Config Class

The `Config` class follows the **Single Responsibility Principle** - its only job is to manage configuration settings.

### Key Settings Explained

#### 1. **Base URLs and Paths**
```python
BASE_URL = "https://unilever.coupahost.com/order_headers/{}"
DOWNLOAD_FOLDER = os.path.expanduser("~/Downloads/CoupaDownloads")
DRIVER_PATH = os.path.join(os.path.dirname(__file__), "drivers", "edgedriver_138")
```

**In Plain English:**
- `BASE_URL`: The website address where PO pages are located. The `{}` is a placeholder that gets replaced with the actual PO number
- `DOWNLOAD_FOLDER`: Where downloaded files will be saved (in your Downloads folder)
- `DRIVER_PATH`: Where the Edge browser driver is located on your computer

#### 2. **File Settings**
```python
ALLOWED_EXTENSIONS: List[str] = [".pdf", ".msg", ".docx"]
```

**In Plain English:** This tells the application which file types to download. It will only download PDF, MSG, and DOCX files, ignoring other types.

#### 3. **Environment Variables**
```python
PAGE_DELAY = float(os.environ.get("PAGE_DELAY", "0"))
EDGE_PROFILE_DIR = os.environ.get("EDGE_PROFILE_DIR")
LOGIN_TIMEOUT = int(os.environ.get("LOGIN_TIMEOUT", "60"))
HEADLESS = os.environ.get("HEADLESS", "false").lower() == "true"
```

**In Plain English:** These are settings you can change without editing the code:
- `PAGE_DELAY`: How long to wait after loading a page (useful for debugging)
- `EDGE_PROFILE_DIR`: Where to find your Edge browser profile (for saved logins)
- `LOGIN_TIMEOUT`: How long to wait for you to log in (in seconds)
- `HEADLESS`: Whether to run the browser in the background (true) or show the window (false)

#### 4. **Browser Settings**
```python
BROWSER_OPTIONS = {
    "download.default_directory": DOWNLOAD_FOLDER,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": False,
}
```

**In Plain English:** These tell the browser how to behave:
- `download.default_directory`: Where to save downloads
- `download.prompt_for_download`: Don't ask for permission before downloading
- `download.directory_upgrade`: Allow downloads to the specified folder
- `safebrowsing.enabled`: Turn off safe browsing warnings

#### 5. **CSS Selectors**
```python
ATTACHMENT_SELECTOR = "span[aria-label*='file attachment']"
```

**In Plain English:** This is like a "search term" that helps the application find attachment links on the webpage. It looks for elements that contain "file attachment" in their description.

#### 6. **Timeouts**
```python
ATTACHMENT_WAIT_TIMEOUT = 10
DOWNLOAD_WAIT_TIMEOUT = 30
```

**In Plain English:** How long to wait for things to happen:
- `ATTACHMENT_WAIT_TIMEOUT`: How long to wait for attachments to appear on the page
- `DOWNLOAD_WAIT_TIMEOUT`: How long to wait for downloads to complete

#### 7. **Debug Settings**
```python
SHOW_EDGE_CRASH_STACKTRACE = False
```

**In Plain English:** Whether to show detailed error messages when the browser crashes. Set to `False` to keep error messages clean and simple.

## Key Libraries Used

### 1. **os** (`import os`)
- **What it is:** Python's operating system interface
- **Why we use it:** To work with file paths, environment variables, and create directories
- **Think of it as:** A tool that helps the application interact with your computer's file system

### 2. **typing** (`from typing import List`)
- **What it is:** Python's type hinting system
- **Why we use it:** To specify what type of data a variable should contain
- **Think of it as:** A way to document what kind of data we expect

## Class Methods

### 1. **ensure_download_folder_exists**
```python
@classmethod
def ensure_download_folder_exists(cls) -> None:
    if not os.path.exists(cls.DOWNLOAD_FOLDER):
        os.makedirs(cls.DOWNLOAD_FOLDER)
```

**In Plain English:** This method checks if the download folder exists, and if not, it creates it. It's like making sure you have a folder ready before trying to put files in it.

### 2. **get_csv_file_path**
```python
@classmethod
def get_csv_file_path(cls) -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, "input.csv")
```

**In Plain English:** This method figures out where the CSV file with PO numbers is located. It looks in the same folder as the script itself.

## Environment Variables

Environment variables are settings that you can change without editing the code. You can set them in your terminal:

```bash
# Set a page delay for debugging
export PAGE_DELAY=5

# Enable headless mode
export HEADLESS=true

# Set a custom login timeout
export LOGIN_TIMEOUT=120
```

## Benefits of This Approach

1. **Centralized Configuration**: All settings are in one place
2. **Easy to Modify**: Change settings without touching the main code
3. **Environment-Specific**: Different settings for different environments
4. **Type Safety**: Type hints help catch errors early
5. **Documentation**: Clear comments explain what each setting does

## Best Practices Used

1. **Single Responsibility**: This class only handles configuration
2. **Class Methods**: Methods that don't need instance data
3. **Type Hints**: Clear documentation of data types
4. **Default Values**: Sensible defaults for all settings
5. **Environment Variables**: Flexible configuration without code changes
