# Downloader Module Documentation

## Overview

The `downloader.py` file is the **file operations specialist** of the project. Think of it as the "file manager" who handles all the complex tasks of finding, downloading, and organizing files from the web. This module contains three main classes that work together to manage the entire download process.

## What This Module Does

This module is responsible for:
- Finding attachment links on web pages
- Downloading files from those links
- Managing file names and extensions
- Renaming downloaded files with PO numbers
- Detecting when you need to log in
- Waiting for downloads to complete

## The Three Main Classes

### 1. FileManager Class

The `FileManager` class handles all file-related operations like a "file clerk" who knows everything about file types and naming.

#### Key Methods:

**get_supported_extensions()**
```python
@staticmethod
def get_supported_extensions() -> List[str]:
    return Config.ALLOWED_EXTENSIONS
```

**In Plain English:** This method returns a list of file types we're allowed to download (PDF, MSG, DOCX). It's like checking a "permitted file types" list.

**is_supported_file(filename)**
```python
@staticmethod
def is_supported_file(filename: str) -> bool:
    return any(filename.lower().endswith(ext) for ext in Config.ALLOWED_EXTENSIONS)
```

**In Plain English:** This checks if a file is one of the types we want to download. It's like a bouncer checking if a file has the right "ID" (extension) to be allowed in.

**extract_filename_from_aria_label(aria_label, index)**
```python
@staticmethod
def extract_filename_from_aria_label(aria_label: str, index: int) -> str:
    if aria_label is None:
        return f"attachment_{index + 1}"
    
    filename_match = re.search(r"(.+?)\s*file attachment", aria_label)
    return filename_match.group(1) if filename_match else f"attachment_{index + 1}"
```

**In Plain English:** This extracts the actual filename from the webpage's description. It's like reading a label on a box to find out what's inside. If it can't find a proper name, it creates a generic one like "attachment_1".

**rename_downloaded_files(po_number, files_to_rename, download_folder)**
```python
@staticmethod
def rename_downloaded_files(po_number: str, files_to_rename: set, download_folder: str) -> None:
    for filename in files_to_rename:
        if not filename.startswith(f"PO{po_number}_"):
            old_path = os.path.join(download_folder, filename)
            new_filename = f"PO{po_number}_{filename}"
            new_path = os.path.join(download_folder, new_filename)
            os.rename(old_path, new_path)
```

**In Plain English:** This renames downloaded files by adding the PO number as a prefix. For example, "document.pdf" becomes "PO15262984_document.pdf". It only renames files that don't already have any PO prefix to avoid double prefixes like "POPO15826591_...".

**Smart Renaming Logic:**
- If filename is "document.pdf" → rename to "PO15262984_document.pdf"
- If filename is "PO15262984_document.pdf" → skip (already has correct prefix)
- If filename is "PO15826591_document.pdf" → skip (already has PO prefix, even if different)
- This prevents double prefixes like "POPO15826591_document.pdf"

**Enhanced File Tracking:**
- Tracks file sizes before and after downloads
- Detects files that changed size (indicating new downloads)
- Provides better detection of new files
- Includes final check for unnamed files

**cleanup_double_po_prefixes(download_folder)**
```python
@staticmethod
def cleanup_double_po_prefixes(download_folder: str) -> None:
    """Clean up existing files with double PO prefixes (e.g., POPO15826591_...)."""
    for filename in os.listdir(download_folder):
        if filename.startswith("POPO"):
            clean_filename = filename[2:]  # Remove the first "PO"
            os.rename(old_path, new_path)
```

**In Plain English:** This method finds and fixes files that already have double PO prefixes:
- Finds files like "POPO15826591_document.pdf"
- Removes the first "PO" to make it "PO15826591_document.pdf"
- This fixes existing files that were created before the prevention logic was added

### 2. DownloadManager Class

The `DownloadManager` class is the "download specialist" who handles the actual process of finding and downloading files from web pages.

#### Key Methods:

**__init__(driver)**
```python
def __init__(self, driver: webdriver.Edge):
    self.driver = driver
    self.file_manager = FileManager()
```

**In Plain English:** When we create a download manager, we give it control of the browser and create a file manager to help with file operations.

**wait_for_download_complete(directory, timeout)**
```python
def _wait_for_download_complete(self, directory: str, timeout: int = 30) -> None:
    start_time = time.time()
    while time.time() - start_time < timeout:
        if not any(f.endswith(".crdownload") for f in os.listdir(directory)):
            return
        time.sleep(1)
    raise TimeoutException(f"Downloads not completed within {timeout} seconds")
```

**In Plain English:** This method waits for downloads to finish by checking for temporary ".crdownload" files. It's like waiting for a file to finish copying - you keep checking until the temporary file disappears and the real file appears.

**wait_for_attachments()**
```python
def _wait_for_attachments(self) -> None:
    WebDriverWait(self.driver, Config.ATTACHMENT_WAIT_TIMEOUT).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, Config.ATTACHMENT_SELECTOR)
        )
    )
```

**In Plain English:** This waits for attachment links to appear on the webpage. It's like waiting for a page to fully load before looking for download buttons.

**find_attachments()**
```python
def _find_attachments(self) -> List:
    return self.driver.find_elements(By.CSS_SELECTOR, Config.ATTACHMENT_SELECTOR)
```

**In Plain English:** This finds all the attachment links on the current webpage. It's like scanning a page to find all the "Download" buttons.

**download_attachment(attachment, index)**
```python
def _download_attachment(self, attachment, index: int) -> None:
    aria_label = attachment.get_attribute("aria-label")
    filename = self.file_manager.extract_filename_from_aria_label(aria_label, index)
    
    if not self.file_manager.is_supported_file(filename):
        print(f"    Skipping unsupported file: {filename}")
        return
    
    self.driver.execute_script("arguments[0].scrollIntoView();", attachment)
    attachment.click()
    print(f"    Downloading: {filename}")
    time.sleep(1)
```

**In Plain English:** This downloads a single attachment:
1. Gets the filename from the webpage
2. Checks if it's a supported file type
3. Scrolls to make the download link visible
4. Clicks the download link
5. Waits a moment before the next download

**download_attachments_for_po(display_po, clean_po)** - **NEW APPROACH!**
```python
def download_attachments_for_po(self, display_po: str, clean_po: str) -> None:
    url = Config.BASE_URL.format(clean_po)
    print(f"Processing PO #{display_po} (URL: {url})")
    
    self.driver.get(url)
    
    if "Page not found" in self.driver.title:
        print(f"  PO #{display_po} not found. Skipping.")
        return
    
    # Wait for attachments to load
    self._wait_for_attachments()
    
    # Find all attachment elements
    attachments = self._find_attachments()
    if not attachments:
        print(f"  No attachments found for PO #{display_po}")
        return
    
    print(f"  Found {len(attachments)} attachments. Downloading with proper names...")
    
    # Use new approach: download to temp directory with proper names
    self._download_with_proper_names(attachments, display_po)
```

**In Plain English:** This is the main method that handles downloading all attachments for a single PO using the **new approach**:
1. Navigate to the PO page
2. Check if the page exists
3. Wait for attachments to load
4. Find all attachment links
5. **NEW**: Extract supplier name from the page
6. **NEW**: Create supplier-specific folder
7. **NEW**: Use cascading "Save As" methods to download with proper names to supplier folder

**The New "Save As" Approach - Three Methods:**

We now use a **cascading approach** with three different "Save As" methods:

### **Method 1: Direct HTTP Download (Best)**
```python
# Extract download URLs and use requests library
response = requests.get(download_url, cookies=cookies, stream=True)
with open(f"PO{display_po}_{filename}", 'wb') as f:
    for chunk in response.iter_content(chunk_size=8192):
        f.write(chunk)
```

**How it works:**
1. **Extract download URLs** from attachment elements
2. **Use browser cookies** for authentication
3. **Download directly with proper filename** using Python requests
4. **No browser interaction needed** after URL extraction

### **Method 2: Right-Click Save As (Experimental)**
```python
# Right-click on attachment and select Save As
actions = ActionChains(self.driver)
actions.context_click(attachment).perform()
# Handle Save As dialog (complex and OS-dependent)
```

**How it works:**
1. **Right-click on attachment** to open context menu
2. **Navigate to "Save As" option** using keyboard
3. **Handle Save As dialog** to specify filename
4. **Note:** Very browser and OS dependent

### **Method 3: Temporary Directory (Fallback)**
```python
# Change download directory, download, then move with proper names
self.driver.execute_cdp_cmd('Page.setDownloadBehavior', {
    'behavior': 'allow',
    'downloadPath': temp_dir
})
```

**How it works:**
1. **Create temporary directory** for each PO
2. **Change browser download directory** using CDP
3. **Download to temp directory**
4. **Move files with proper names** to final destination

### **Method 4: File Tracking (Last Resort)**
If all else fails, falls back to the improved file tracking method.

**Benefits of This Cascading Approach:**
- ✅ **Direct HTTP is fastest** - no browser overhead
- ✅ **Perfect filename control** - files saved with exact names we want
- ✅ **Multiple fallbacks** - if one method fails, others take over
- ✅ **No race conditions** - files are properly named from the start
- ✅ **Session preservation** - uses browser cookies for authentication
- ✅ **Robust and reliable** - multiple methods ensure success

## 🗂️ **Supplier Folder Organization**

The system now automatically organizes files by supplier, creating a clean folder structure:

### **Supplier Name Extraction**
```python
def _extract_supplier_name(self) -> str:
    supplier_element = WebDriverWait(self.driver, 10).until(
        EC.presence_of_element_located((By.XPATH, Config.SUPPLIER_NAME_XPATH))
    )
    supplier_name = supplier_element.text.strip()
    return self._clean_folder_name(supplier_name)
```

**How it works:**
1. **Uses XPath** to find supplier name on PO page: `/html/body/div[1]/div[5]/div/div/div[4]/div/div[3]/section[2]/div[2]/div[1]/div/span[3]`
2. **Extracts text** from the supplier element
3. **Cleans the name** for safe folder naming
4. **Falls back** to "Unknown_Supplier" if extraction fails

### **Folder Name Cleaning**
```python
def _clean_folder_name(self, name: str) -> str:
    # Replace spaces and invalid characters with underscores
    cleaned = re.sub(r'[<>:"/\\|?*&\s]', '_', name)
    # Remove multiple underscores and trim
    cleaned = re.sub(r'_+', '_', cleaned).strip('_')
    # Limit length to 100 characters
    if len(cleaned) > 100:
        cleaned = cleaned[:100].rstrip('_')
    return cleaned
```

**Examples:**
- `"Ernst & Young LLP"` → `"Ernst___Young_LLP"`
- `"Company/Name:With<Invalid>Chars"` → `"Company_Name_With_Invalid_Chars"`
- `"Very Long Company Name..."` → Truncated to 100 characters

### **Folder Structure**
```
~/Downloads/CoupaDownloads/
├── Ernst___Young_LLP/
│   ├── PO15826591_document1.pdf
│   ├── PO15826591_document2.docx
│   └── PO15873456_report.pdf
├── Accenture_Ltd/
│   ├── PO15262984_invoice.pdf
│   └── PO15327452_contract.msg
└── Unknown_Supplier/
    └── PO15421343_attachment.pdf
```

**Benefits:**
- ✅ **Automatic organization** - files grouped by supplier
- ✅ **Easy navigation** - find all files for a specific supplier
- ✅ **Clean structure** - no mixed files in main folder
- ✅ **Safe naming** - handles special characters in supplier names
- ✅ **Fallback handling** - uses "Unknown_Supplier" if extraction fails

### 3. LoginManager Class

The `LoginManager` class is the "security guard" who detects when you need to log in and waits for you to complete the login process.

#### Key Methods:

**ensure_logged_in()**
```python
def ensure_logged_in(self) -> None:
    if ("login" in self.driver.current_url or 
        "sign_in" in self.driver.current_url or 
        "Log in" in self.driver.title):
        print("Detected login page. Please log in manually...")
        
        # Monitor for successful login indicators
        max_wait_time = Config.LOGIN_TIMEOUT
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            current_url = self.driver.current_url
            
            # Success indicators (URLs that indicate logged-in state)
            success_indicators = [
                "order_headers",  # PO pages
                "dashboard",      # Dashboard
                "home",          # Home page
                "profile",       # Profile page
                "settings",      # Settings page
            ]
            
            # Check if we're on a logged-in page
            if any(indicator in current_url for indicator in success_indicators):
                print("✅ Login detected automatically!")
                return
            
            # Check if we're still on login page
            if "login" in current_url or "sign_in" in current_url:
                print("⏳ Waiting for login completion...", end="\r")
                time.sleep(1)
                continue
            
            # If we're not on login page and not on a known success page,
            # assume login was successful
            if "login" not in current_url and "sign_in" not in current_url:
                print("✅ Login detected automatically!")
                return
```

**In Plain English:** This method:
1. Checks if we're on a login page
2. If yes, tells you to log in manually
3. Monitors the webpage for signs that login was successful
4. Looks for specific URLs that indicate you're logged in
5. Times out after a certain period if login doesn't complete

## Key Libraries Used

### 1. **Selenium** (`from selenium import webdriver`)
- **What it is:** A library for controlling web browsers programmatically
- **Why we use it:** To find elements on web pages, click links, and navigate
- **Think of it as:** A robot that can interact with websites

### 2. **re** (`import re`)
- **What it is:** Python's regular expression library
- **Why we use it:** To extract filenames from webpage descriptions
- **Think of it as:** A pattern matching tool for text

### 3. **os** (`import os`)
- **What it is:** Python's operating system interface
- **Why we use it:** To work with files, check file existence, and rename files
- **Think of it as:** A tool to interact with your computer's file system

### 4. **time** (`import time`)
- **What it is:** Python's time handling library
- **Why we use it:** To add delays and measure timeouts
- **Think of it as:** A timer and clock for the application

## How the Classes Work Together

1. **DownloadManager** uses **FileManager** to handle file operations
2. **DownloadManager** uses **LoginManager** to ensure login before downloading
3. All classes use **Config** for settings and timeouts
4. The workflow is coordinated by the main module

## Error Handling

The module includes comprehensive error handling:

1. **File Not Found**: If a PO page doesn't exist
2. **No Attachments**: If a PO has no downloadable files
3. **Download Timeouts**: If downloads take too long
4. **Login Timeouts**: If login takes too long
5. **File Renaming Errors**: If files can't be renamed

## Best Practices Used

1. **Single Responsibility**: Each class has one clear purpose
2. **Separation of Concerns**: File operations, downloads, and login are separate
3. **Error Handling**: Comprehensive error handling throughout
4. **Configuration**: Uses external configuration for flexibility
5. **Type Hints**: Clear documentation of data types
6. **Static Methods**: Methods that don't need instance data

## Benefits of This Approach

1. **Modularity**: Each class can be tested and modified independently
2. **Reusability**: Classes can be used in other projects
3. **Maintainability**: Clear separation makes debugging easier
4. **Flexibility**: Easy to add new file types or change behavior
5. **Reliability**: Comprehensive error handling prevents crashes
