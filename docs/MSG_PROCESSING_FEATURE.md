# MSG File Processing Feature

## Overview

The Coupa Downloads system now includes **automatic MSG file processing** that converts .msg files to PDF format and extracts any attachments into organized subfolders.

## How It Works

### User Prompt

Before starting PO processing, the system asks the user:

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

### Processing Steps

When MSG processing is enabled:

1. **File Detection**: System detects downloaded .msg files
2. **Subfolder Creation**: Creates subfolder named `PO{number}_{msg_filename}`
3. **PDF Conversion**: Converts MSG to PDF using available tools
4. **Attachment Extraction**: Extracts all attachments from MSG
5. **File Organization**: Moves original MSG and organizes all files

## Folder Structure

### Before Processing

```
Supplier_Folder/
├── PO123456_original_email.msg
└── other_files.pdf
```

### After Processing

```
Supplier_Folder/
├── PO123456_original_email.msg
├── PO123456_original_email/
│   ├── PO123456_original_email.pdf
│   ├── PO123456_attachment1.pdf
│   ├── PO123456_attachment2.xlsx
│   ├── PO123456_invoice.docx
│   └── PO123456_original_email.msg
└── other_files.pdf
```

## Conversion Methods

### Primary: LibreOffice

- **Command**: `libreoffice --headless --convert-to pdf`
- **Advantage**: High-quality conversion, preserves formatting
- **Requirement**: LibreOffice installed on system

### Secondary: Python Libraries

- **Method**: extract-msg + weasyprint/pdfkit
- **Process**: MSG → HTML → PDF
- **Advantage**: Pure Python solution
- **Requirement**: `extract-msg`, `weasyprint`, or `pdfkit`

### Fallback: HTML Only

- **Method**: extract-msg → HTML
- **Result**: HTML file instead of PDF
- **Advantage**: Always works if extract-msg is available

## Attachment Extraction

### Supported Attachments

- **All file types**: Since file restrictions are removed
- **Naming**: `PO{number}_{original_filename}`
- **Location**: Same subfolder as PDF conversion

### Extraction Process

1. **Parse MSG**: Use extract-msg library
2. **Identify Attachments**: Find all embedded files
3. **Filter Artifacts**: Remove signature images, icons, and small files
4. **Clean Filenames**: Remove invalid characters
5. **Save Files**: Write to subfolder with PO prefix

### Artifact Filtering

The system automatically filters out common email artifacts to focus on business-relevant attachments:

**Filtered Out (Artifacts)**:

- Signature images (`signature.png`, `sig_logo.gif`)
- Company logos and icons (`logo.png`, `icon.ico`)
- Small images (< 5KB)
- Very small files (< 1KB)
- Embedded objects without extensions
- Email client artifacts

**Extracted (Business Files)**:

- Business documents (PDF, DOCX, XLSX)
- Large images (> 5KB)
- Archives (ZIP, RAR)
- Any file with meaningful size and extension

**Configuration**:

```bash
# Enable/disable filtering (default: enabled)
export FILTER_MSG_ARTIFACTS=true

# Adjust minimum file sizes
export MSG_ARTIFACT_MIN_SIZE=1024  # 1KB minimum
export MSG_IMAGE_MIN_SIZE=5120     # 5KB minimum for images
```

## Dependencies

### Required Python Libraries

```bash
pip install extract-msg weasyprint pdfkit
```

### Optional System Tools

- **LibreOffice**: For best PDF conversion quality
- **wkhtmltopdf**: Alternative PDF conversion tool

### Installation Verification

```bash
python scripts/test_msg_processing.py
```

## Configuration

### Enable/Disable

- **Runtime**: User prompt before processing
- **Default**: Disabled (user must choose)
- **Scope**: Per processing session

### File Handling

- **Original MSG**: Moved to subfolder
- **PDF Output**: Named `PO{number}_{msg_name}.pdf`
- **Attachments**: Extracted with PO prefix
- **Subfolder**: Named after original MSG file

## Error Handling

### Graceful Degradation

- **Missing LibreOffice**: Falls back to Python conversion
- **Missing extract-msg**: Skips MSG processing
- **Conversion Failure**: Continues with other files
- **Attachment Failure**: Logs error, continues processing

### Error Messages

```
⚠️ Could not convert MSG to PDF (no suitable converter found)
⚠️ extract-msg library not available for MSG conversion
❌ MSG processing failed for PO123456_email.msg: [error details]
```

## Usage Examples

### Example 1: Simple Email

**Input**: `PO123456_simple_email.msg`
**Output**:

```
PO123456_simple_email/
├── PO123456_simple_email.pdf
└── PO123456_simple_email.msg
```

### Example 2: Email with Attachments

**Input**: `PO789012_complex_email.msg` (contains invoice.pdf, report.xlsx)
**Output**:

```
PO789012_complex_email/
├── PO789012_complex_email.pdf
├── PO789012_invoice.pdf
├── PO789012_report.xlsx
└── PO789012_complex_email.msg
```

### Example 3: Multiple MSG Files

**Input**: Multiple .msg files in same PO
**Output**: Separate subfolder for each MSG file

## Integration with Existing Features

### Enhanced Progress System

MSG processing integrates with the enhanced progress feedback:

```
📋 POPO123456.....20% | 2s elapsed | ~5m remaining
   📎 3 file(s) found
   📥 Starting download of 3 file(s)...
   ✅ email.msg 1.2MB/1.2MB (100%)
   📁 Created subfolder: PO123456_email
   📄 Converted to PDF: PO123456_email.pdf
   📎 Extracted 2 attachment(s)
   ✅ PO123456_email completed: 3/3 files
```

### File Type Restrictions

- **Compatible**: Works with file type restrictions removed
- **MSG Files**: Always processed when feature is enabled
- **Other Files**: Processed normally

### Excel/CSV Integration

- **Status Updates**: MSG processing results included in reports
- **File Organization**: Maintains existing folder structure
- **Backup System**: Original files preserved

## Testing

### Test Script

```bash
python scripts/test_msg_processing.py
```

### Manual Testing

1. **Enable MSG processing** when prompted
2. **Download POs** with .msg files
3. **Check subfolders** for organized content
4. **Verify PDF conversion** and attachment extraction

### Expected Output

```
🧪 Testing MSG File Processing Feature
==================================================
📁 Test directory: ~/Downloads/CoupaDownloads/test_msg_processing
📧 Testing: Sample Email with Attachments
   MSG File: PO123456_sample_email.msg
   PO Number: 123456
   ✅ Created test MSG file
   ✅ MSG processing completed successfully
```

## Troubleshooting

### Issue: MSG Processing Not Working

**Solutions**:

1. Check if MSG processing was enabled during user prompt
2. Verify extract-msg library is installed: `pip install extract-msg`
3. Check for error messages in console output

### Issue: PDF Conversion Failing

**Solutions**:

1. Install LibreOffice for best results
2. Install weasyprint: `pip install weasyprint`
3. Check system dependencies

### Issue: Attachments Not Extracted

**Solutions**:

1. Verify extract-msg library is working
2. Check if MSG file actually contains attachments
3. Review error messages for specific issues

### Issue: Subfolder Not Created

**Solutions**:

1. Check file permissions in download directory
2. Verify MSG file was downloaded successfully
3. Check for error messages during processing

### Issue: Important Attachments Missing

**Solutions**:

1. Check if artifact filtering is too aggressive:
   ```bash
   export FILTER_MSG_ARTIFACTS=false  # Disable filtering
   ```
2. Adjust minimum file sizes:
   ```bash
   export MSG_ARTIFACT_MIN_SIZE=512   # Lower threshold
   export MSG_IMAGE_MIN_SIZE=2048     # Lower image threshold
   ```
3. Review console output for filtered files:
   ```
   🚫 Filtered out: signature.png (signature/icon artifact)
   ```

### Issue: Too Many Artifacts Extracted

**Solutions**:

1. Enable artifact filtering (default):
   ```bash
   export FILTER_MSG_ARTIFACTS=true
   ```
2. Increase minimum file sizes:
   ```bash
   export MSG_ARTIFACT_MIN_SIZE=2048  # Higher threshold
   export MSG_IMAGE_MIN_SIZE=10240    # Higher image threshold
   ```

## Benefits

### For Users

- **Better Organization**: Email content separated from other files
- **PDF Access**: Easy-to-read PDF versions of emails
- **Attachment Access**: All attachments extracted and organized
- **Searchability**: PDF content is searchable

### For Business

- **Compliance**: PDF format for long-term storage
- **Accessibility**: Multiple formats for different use cases
- **Organization**: Clear structure for email-based POs
- **Efficiency**: Automated processing saves manual work

## Future Enhancements

### Planned Features

- **Email Metadata**: Extract and display email headers
- **Batch Processing**: Process multiple MSG files simultaneously
- **Custom Templates**: User-defined PDF conversion templates
- **OCR Integration**: Extract text from image attachments

### Configuration Options

- **PDF Quality**: Adjustable conversion quality
- **Attachment Filtering**: Selective attachment extraction
- **Folder Naming**: Customizable subfolder naming
- **Processing Rules**: Conditional MSG processing

## Conclusion

The MSG processing feature provides a comprehensive solution for handling email attachments in Coupa downloads. It automatically organizes email content, converts to searchable PDF format, and extracts all attachments with proper naming conventions.

The feature is designed to be:

- **User-friendly**: Simple enable/disable prompt
- **Robust**: Multiple fallback conversion methods
- **Flexible**: Works with existing file organization
- **Reliable**: Graceful error handling and recovery
