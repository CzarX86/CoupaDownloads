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
```
    # This is a static method that takes a file path and returns a list of strings
    # Check if the CSV file exists at the given path
    # If file doesn't exist, raise a FileNotFoundError with a descriptive message
    
    # Create an empty list to store PO numbers
    # Open the CSV file with proper newline handling
    # Create a CSV reader object to parse the file
    
    # Try to read the first row (header) and skip it
    # If the file is empty, catch the StopIteration exception and continue
    
    # Loop through each row in the CSV file
    # If the row is not empty, process it
    # Take the first column value, remove extra spaces, and add to our list
    
    # Return the complete list of PO numbers
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
```
PO_NUMBER
PO15262984
PO15327452
PO15362783
```

**Result:** `["PO15262984", "PO15327452", "PO15362783"]`

#### 2. **validate_po_number(po)**
```
    # This is a static method that takes a string and returns a boolean
    # Remove the "PO" prefix from the PO number if it exists
    # Remove any extra spaces from the beginning and end
    # Check if the remaining string contains only digits
    # Return True if it's all digits, False otherwise
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
```
    # This is a static method that takes a string and returns a string
    # Remove the "PO" prefix from the PO number if it exists
    # Remove any extra spaces from the beginning and end
    # Return the cleaned PO number (just the numeric part)
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
```
    # This is a static method that takes a list of strings and returns a list of tuples
    # Create an empty list to store valid PO number pairs
    
    # Loop through each PO number in the input list
    # Check if the current PO number is valid using the validate method
    # If the PO number is valid:
    #     Clean the PO number using the clean method
    #     Create a tuple with (original_po, cleaned_po) and add to our list
    # If the PO number is invalid:
    #     Print a warning message with the invalid PO number
    
    # Return the list of valid PO number pairs
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
```
[
    ("PO15262984", "15262984"),
    ("PO15327452", "15327452"), 
    ("PO15362783", "15362783")
]
```

**Console Output:** `⚠️ Invalid PO number format: INVALID123`

#### 5. **get_csv_file_path()**
```
    # This is a static method that returns a string
    # Ask the Config module for the CSV file path
    # Return the file path from the configuration
```

**In Plain English:** This method finds where the CSV file is located. It asks the configuration module for the file path, which is typically in the same folder as the script.

## 📊 **Enhanced CSV Structure**

The CSV processor now supports an enhanced format with comprehensive tracking:

### **Original Format:**
```
PO_NUMBER
PO15826591
PO15873456
```

### **Enhanced Format:**
```
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
```
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
```
    # Check if the CSV file exists at the specified path
    # If the file doesn't exist, raise a FileNotFoundError with a descriptive message
```

**In Plain English:** If the CSV file doesn't exist, the program stops with a clear error message.

### 2. **Empty File**
```
    # Try to read the first row from the CSV reader
    # If the file is empty and there's nothing to read, catch the StopIteration exception
    # Continue processing without crashing (pass means do nothing)
```

**In Plain English:** If the CSV file is empty, the program handles it gracefully without crashing.

### 3. **Invalid PO Numbers**
```
    # Check if the current PO number is valid using the validate method
    # If the PO number is valid, process it normally
    # If the PO number is invalid, print a warning message with the invalid PO
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