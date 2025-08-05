# CSV Processor Module Documentation

## Overview

The `csv_processor.py` file is the **data reader** of the project. Think of it as the "file clerk" who reads and validates the list of Purchase Order (PO) numbers from a CSV file. This module handles all the tasks related to reading, validating, and processing PO numbers from spreadsheet data.

## What This Module Does

This module is responsible for:
- Reading PO numbers from a CSV file
- Validating that PO numbers have the correct format
- Cleaning PO numbers (removing prefixes like "PO")
- Processing multiple PO numbers efficiently
- Providing the data that the rest of the application needs to work

## The CSVProcessor Class

The `CSVProcessor` class follows the **Single Responsibility Principle** - its only job is to handle CSV file operations and PO number processing.

### Key Methods Explained

#### 1. **read_po_numbers_from_csv(csv_file_path)**
```python
@staticmethod
def read_po_numbers_from_csv(csv_file_path: str) -> List[str]:
    if not os.path.exists(csv_file_path):
        raise FileNotFoundError(f"PO input file {csv_file_path} not found")
    
    po_entries = []
    with open(csv_file_path, newline="") as f:
        reader = csv.reader(f)
        # Skip header if exists
        try:
            header = next(reader)
        except StopIteration:
            pass
        
        for row in reader:
            if row:  # Skip empty rows
                po_entries.append(row[0].strip())  # Get first column value
    
    return po_entries
```

**In Plain English:** This method reads the CSV file and extracts all PO numbers:
1. **Check if file exists**: Make sure the CSV file is actually there
2. **Open the file**: Start reading the spreadsheet
3. **Skip the header**: Ignore the first row if it contains column names
4. **Read each row**: Go through the file line by line
5. **Extract PO numbers**: Take the first column from each row
6. **Clean the data**: Remove extra spaces
7. **Return the list**: Give back all the PO numbers found

**Example CSV file:**
```csv
PO_NUMBER
PO15262984
PO15327452
PO15362783
```

**Result:** `["PO15262984", "PO15327452", "PO15362783"]`

#### 2. **validate_po_number(po)**
```python
@staticmethod
def validate_po_number(po: str) -> bool:
    clean_po = po.replace("PO", "").strip()
    return clean_po.isdigit()
```

**In Plain English:** This method checks if a PO number is valid:
1. **Remove "PO" prefix**: Take away the "PO" part if it exists
2. **Remove spaces**: Clean up any extra spaces
3. **Check if numeric**: Make sure what's left is only numbers
4. **Return result**: True if valid, False if not

**Examples:**
- `"PO15262984"` → `"15262984"` → `True` (valid)
- `"15262984"` → `"15262984"` → `True` (valid)
- `"PO15262984A"` → `"15262984A"` → `False` (invalid - contains letter)
- `"PO15262984 "` → `"15262984"` → `True` (valid - spaces removed)

#### 3. **clean_po_number(po)**
```python
@staticmethod
def clean_po_number(po: str) -> str:
    return po.replace("PO", "").strip()
```

**In Plain English:** This method prepares a PO number for use in URLs:
1. **Remove "PO" prefix**: Take away the "PO" part
2. **Remove spaces**: Clean up any extra spaces
3. **Return clean number**: Give back just the numeric part

**Examples:**
- `"PO15262984"` → `"15262984"`
- `"15262984"` → `"15262984"`
- `"PO15262984 "` → `"15262984"`

#### 4. **process_po_numbers(po_entries)**
```python
@staticmethod
def process_po_numbers(po_entries: List[str]) -> List[Tuple[str, str]]:
    valid_entries = []
    
    for po in po_entries:
        if CSVProcessor.validate_po_number(po):
            clean_po = CSVProcessor.clean_po_number(po)
            valid_entries.append((po, clean_po))
        else:
            print(f"⚠️ Invalid PO number format: {po}")
    
    return valid_entries
```

**In Plain English:** This method processes a list of PO numbers and returns valid ones:
1. **Start with empty list**: Prepare to collect valid PO numbers
2. **Check each PO**: Go through the list one by one
3. **Validate format**: Make sure each PO number is properly formatted
4. **Create pairs**: For valid POs, create a pair of (original, cleaned)
5. **Skip invalid ones**: Print a warning for invalid POs
6. **Return results**: Give back all the valid PO pairs

**Example Input:** `["PO15262984", "PO15327452", "INVALID123", "PO15362783"]`

**Example Output:** 
```python
[
    ("PO15262984", "15262984"),
    ("PO15327452", "15327452"), 
    ("PO15362783", "15362783")
]
```

**Console Output:** `⚠️ Invalid PO number format: INVALID123`

#### 5. **get_csv_file_path()**
```python
@staticmethod
def get_csv_file_path() -> str:
    return Config.get_csv_file_path()
```

**In Plain English:** This method finds where the CSV file is located. It asks the configuration module for the file path, which is typically in the same folder as the script.

## 📊 **Enhanced CSV Structure**

The CSV processor now supports an enhanced format with comprehensive tracking:

### **Original Format:**
```csv
PO_NUMBER
PO15826591
PO15873456
```

### **Enhanced Format:**
```csv
PO_NUMBER,STATUS,SUPPLIER,ATTACHMENTS_FOUND,ATTACHMENTS_DOWNLOADED,LAST_PROCESSED,ERROR_MESSAGE,DOWNLOAD_FOLDER,COUPA_URL
PO15826591,COMPLETED,Ernst___Young_LLP,3,3,2024-01-15 14:30:25,,Ernst___Young_LLP/,https://coupa.company.com/requisition_lines/15826591
PO15873456,FAILED,,0,0,2024-01-15 14:32:10,Login timeout,,https://coupa.company.com/requisition_lines/15873456
```

### **Column Descriptions:**

| Column | Purpose | Example |
|--------|---------|---------|
| `PO_NUMBER` | Original PO identifier | `PO15826591` |
| `STATUS` | Processing status | `COMPLETED`, `FAILED`, `PARTIAL`, `PENDING` |
| `SUPPLIER` | Extracted supplier name | `Ernst___Young_LLP` |
| `ATTACHMENTS_FOUND` | Number found on page | `4` |
| `ATTACHMENTS_DOWNLOADED` | Number successfully downloaded | `3` |
| `LAST_PROCESSED` | Processing timestamp | `2024-01-15 14:30:25` |
| `ERROR_MESSAGE` | Failure details | `Login timeout` |
| `DOWNLOAD_FOLDER` | File location | `Ernst___Young_LLP/` |
| `COUPA_URL` | **NEW:** Direct link to PO page | `https://coupa.company.com/requisition_lines/15826591` |

## Key Libraries Used

### 1. **csv** (`import csv`)
- **What it is:** Python's built-in CSV file reading library
- **Why we use it:** To read spreadsheet data in a standardized way
- **Think of it as:** A tool that understands spreadsheet format

### 2. **os** (`import os`)
- **What it is:** Python's operating system interface
- **Why we use it:** To check if files exist and work with file paths
- **Think of it as:** A tool to interact with your computer's file system

### 3. **typing** (`from typing import List, Tuple`)
- **What it is:** Python's type hinting system
- **Why we use it:** To specify what type of data methods return
- **Think of it as:** A way to document what kind of data we expect

## CSV File Format

The module expects a CSV file with this structure:

### Required Format
```csv
PO_NUMBER
PO15262984
PO15327452
PO15362783
```

### What the Module Handles
1. **Header Row**: Automatically skips the first row if it contains column names
2. **PO Prefix**: Accepts PO numbers with or without "PO" prefix
3. **Spaces**: Automatically removes extra spaces
4. **Empty Rows**: Skips any empty lines in the file
5. **Multiple Columns**: Only reads the first column (ignores others)

### Valid PO Number Examples
- `PO15262984` (with prefix)
- `15262984` (without prefix)
- `PO15262984 ` (with spaces)
- ` 15262984 ` (with spaces)

### Invalid PO Number Examples
- `PO15262984A` (contains letters)
- `15262984A` (contains letters)
- `PO15262984-123` (contains special characters)
- `ABC123` (no numbers)

## Error Handling

The module includes several types of error handling:

### 1. **File Not Found**
```python
if not os.path.exists(csv_file_path):
    raise FileNotFoundError(f"PO input file {csv_file_path} not found")
```

**In Plain English:** If the CSV file doesn't exist, the program stops with a clear error message.

### 2. **Empty File**
```python
try:
    header = next(reader)
except StopIteration:
    pass
```

**In Plain English:** If the CSV file is empty, the program handles it gracefully without crashing.

### 3. **Invalid PO Numbers**
```python
if CSVProcessor.validate_po_number(po):
    # Process valid PO
else:
    print(f"⚠️ Invalid PO number format: {po}")
```

**In Plain English:** Invalid PO numbers are reported but don't stop the program from processing valid ones.

## Data Flow

Here's how data flows through the module:

1. **Input**: CSV file with PO numbers
2. **Read**: Extract all PO numbers from the file
3. **Validate**: Check each PO number format
4. **Clean**: Remove prefixes and spaces
5. **Output**: List of (original, cleaned) PO number pairs

## Benefits of This Approach

1. **Separation of Concerns**: CSV processing is separate from other operations
2. **Reusability**: Can be used with different CSV files
3. **Validation**: Ensures data quality before processing
4. **Flexibility**: Handles different PO number formats
5. **Error Handling**: Graceful handling of invalid data
6. **Type Safety**: Clear documentation of data types

## Best Practices Used

1. **Single Responsibility**: This class only handles CSV operations
2. **Static Methods**: Methods that don't need instance data
3. **Type Hints**: Clear documentation of data types
4. **Error Handling**: Comprehensive error handling
5. **Data Validation**: Ensures data quality
6. **Clean Code**: Clear, readable method names and logic

## Integration with Other Modules

The CSV processor works with other modules:

1. **Config Module**: Gets the CSV file path
2. **Main Module**: Receives the processed PO numbers
3. **Downloader Module**: Uses the cleaned PO numbers for URLs

This modular design makes the code more maintainable and testable.
