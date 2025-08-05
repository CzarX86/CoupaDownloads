# File Type Restrictions - Configuration Guide

## Overview

The Coupa Downloads system now supports **flexible file type restrictions**. You can configure which file types are allowed to be downloaded from Coupa attachments.

## Current Configuration

### ✅ **All File Types Allowed** (Default)

```python
ALLOWED_EXTENSIONS: List[str] = []  # Empty list = allow all file types
```

**Result**: The system will download **any file type** found in Coupa attachments, including:

- Documents: PDF, DOCX, XLSX, PPTX, TXT, CSV, XML
- Images: JPG, PNG, GIF, BMP, SVG
- Archives: ZIP, RAR, 7Z, TAR
- Media: MP4, MP3, AVI, MOV
- Executables: EXE, MSI, APP
- And any other file type

## Configuration Options

### Option 1: Allow All File Types (Current Setting)

```python
# In src/core/config.py
ALLOWED_EXTENSIONS: List[str] = []  # Empty list = allow all file types
```

**Benefits**:

- Downloads all attachments regardless of type
- No risk of missing important files
- Maximum flexibility

**Considerations**:

- May download unwanted file types
- Could include executable files (security consideration)

### Option 2: Allow Common File Types

```python
# In src/core/config.py
ALLOWED_EXTENSIONS: List[str] = [
    '.pdf', '.msg', '.docx', '.xlsx', '.txt', '.jpg', '.png',
    '.zip', '.rar', '.csv', '.xml', '.pptx', '.mp4', '.mp3'
]
```

**Benefits**:

- Covers most common business file types
- Excludes potentially dangerous file types
- Good balance of flexibility and security

### Option 3: Allow Only Specific Types

```python
# In src/core/config.py
ALLOWED_EXTENSIONS: List[str] = ['.pdf', '.docx', '.xlsx']
```

**Benefits**:

- Maximum security
- Only downloads essential document types
- Reduces storage usage

### Option 4: Block Specific Types (Advanced)

If you want to allow all files EXCEPT specific types, you can modify the `is_supported_file` method:

```python
# In src/core/downloader.py, modify the is_supported_file method:
@staticmethod
def is_supported_file(filename: str) -> bool:
    """Check if file has supported extension."""
    # Block specific dangerous file types
    blocked_extensions = ['.exe', '.msi', '.bat', '.cmd', '.scr', '.pif']

    # Check if file has blocked extension
    if any(filename.lower().endswith(ext) for ext in blocked_extensions):
        return False

    # Allow all other files
    return True
```

## How It Works

### File Type Checking Process

1. **Attachment Discovery**: System finds all file attachments in Coupa
2. **Extension Check**: For each file, checks if its extension is in `ALLOWED_EXTENSIONS`
3. **Download Decision**:
   - If `ALLOWED_EXTENSIONS` is empty → Download all files
   - If extension matches → Download file
   - If extension doesn't match → Skip file with message

### Code Implementation

```python
# In src/core/downloader.py
@staticmethod
def is_supported_file(filename: str) -> bool:
    """Check if file has supported extension."""
    # If no extensions are specified, allow all files
    if not Config.ALLOWED_EXTENSIONS:
        return True
    # Otherwise, check if file has any of the allowed extensions
    return any(filename.lower().endswith(ext) for ext in Config.ALLOWED_EXTENSIONS)
```

## Testing File Type Restrictions

### Run the Test Script

```bash
python scripts/test_file_type_restrictions.py
```

**Expected Output**:

```
🧪 Testing File Type Restrictions Removal
==================================================
📋 Testing 19 file types...
🔧 Current ALLOWED_EXTENSIONS: []

   ✅ ALLOWED document.pdf
   ✅ ALLOWED email.msg
   ✅ ALLOWED report.docx
   ✅ ALLOWED image.jpg
   ✅ ALLOWED photo.png
   ✅ ALLOWED data.xlsx
   ✅ ALLOWED spreadsheet.csv
   ✅ ALLOWED archive.zip
   ✅ ALLOWED compressed.rar
   ✅ ALLOWED text.txt
   ✅ ALLOWED config.xml
   ✅ ALLOWED presentation.pptx
   ✅ ALLOWED video.mp4
   ✅ ALLOWED audio.mp3
   ✅ ALLOWED script.py
   ✅ ALLOWED webpage.html
   ✅ ALLOWED database.db
   ✅ ALLOWED executable.exe
   ✅ ALLOWED no_extension_file

==================================================
🎉 SUCCESS: All file types are now allowed!
```

## Security Considerations

### ✅ **Safe File Types**

- Documents: `.pdf`, `.docx`, `.xlsx`, `.txt`, `.csv`
- Images: `.jpg`, `.png`, `.gif`, `.bmp`
- Archives: `.zip`, `.rar`, `.7z`
- Media: `.mp4`, `.mp3`, `.avi`

### ⚠️ **Potentially Risky File Types**

- Executables: `.exe`, `.msi`, `.bat`, `.cmd`
- Scripts: `.vbs`, `.ps1`, `.js`
- System files: `.scr`, `.pif`, `.com`

### 🔒 **Recommended Security Practices**

1. **Scan Downloads**: Use antivirus software to scan downloaded files
2. **Sandbox Testing**: Test suspicious files in a virtual environment
3. **User Awareness**: Train users to be cautious with executable files
4. **Network Security**: Ensure proper network security measures

## Real-World Usage Examples

### Example 1: Business Documents Only

```python
ALLOWED_EXTENSIONS: List[str] = [
    '.pdf', '.docx', '.xlsx', '.pptx', '.txt', '.csv', '.xml'
]
```

**Use Case**: Financial department downloading only business documents

### Example 2: Media and Documents

```python
ALLOWED_EXTENSIONS: List[str] = [
    '.pdf', '.docx', '.xlsx', '.jpg', '.png', '.mp4', '.zip'
]
```

**Use Case**: Marketing department downloading documents and media files

### Example 3: All Files (Current Setting)

```python
ALLOWED_EXTENSIONS: List[str] = []
```

**Use Case**: General use where you want to capture all attachments

## Troubleshooting

### Issue: Files Still Being Skipped

**Solution**: Check the configuration file and restart the application

```bash
# Verify current settings
python scripts/test_file_type_restrictions.py
```

### Issue: Want to Block Specific Types

**Solution**: Use the advanced blocking method described in Option 4 above

### Issue: Performance Concerns

**Solution**: Consider limiting to specific file types to reduce download time and storage usage

## Migration from Previous Version

### Before (Restricted)

```python
ALLOWED_EXTENSIONS: List[str] = [".pdf", ".msg", ".docx"]
```

- Only PDF, MSG, and DOCX files were downloaded
- Other file types were skipped with "unsupported type" message

### After (Unrestricted)

```python
ALLOWED_EXTENSIONS: List[str] = []  # Empty list
```

- All file types are now downloaded
- No files are skipped due to type restrictions

## Conclusion

The file type restriction system is now **flexible and configurable**. You can:

- ✅ **Allow all files** (current setting)
- ✅ **Allow specific file types** (for security)
- ✅ **Block specific file types** (advanced configuration)
- ✅ **Test your configuration** with the provided test script

Choose the configuration that best fits your security requirements and business needs.
