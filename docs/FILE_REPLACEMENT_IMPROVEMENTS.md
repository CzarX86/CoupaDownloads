# File Replacement Improvements

## 🎯 **No More Duplicate Files**

The Coupa Downloads project now **replaces existing files** instead of creating duplicates, solving the file duplication problem.

## ✅ **What Was Fixed**

### 1. **File Duplication Problem**

- **Before**: Files were duplicated with counters (e.g., `document_1.pdf`, `document_2.pdf`)
- **After**: Existing files are replaced with new versions

### 2. **Configurable File Handling**

- **Default**: Replace existing files (recommended)
- **Option**: Skip existing files
- **Option**: Create backups before replacement

### 3. **Better File Management**

- Clean file organization
- No more duplicate files cluttering folders
- Consistent file naming

## 🔧 **Configuration Options**

### Environment Variables

```bash
# File replacement behavior (default: true)
export OVERWRITE_EXISTING_FILES=true    # Replace duplicates
export OVERWRITE_EXISTING_FILES=false   # Skip duplicates

# Backup creation (default: false)
export CREATE_BACKUP_BEFORE_OVERWRITE=true  # Create .backup files

# Verbose output for file operations
export VERBOSE_OUTPUT=true              # Show detailed messages
```

### Default Settings

```python
OVERWRITE_EXISTING_FILES = True         # Replace duplicates by default
CREATE_BACKUP_BEFORE_OVERWRITE = False  # No backups by default
VERBOSE_OUTPUT = False                  # Clean output by default
```

## 📊 **Behavior Comparison**

### 🔄 **Default Behavior (Replace)**

```
📋 Processing PO #PO15363269...
📎 Found 2 attachment(s)
🔄 Replacing existing file: PO15363269_document.pdf
✅ Downloaded 2/2 files
```

### ⏭️ **Skip Existing Files**

```bash
export OVERWRITE_EXISTING_FILES=false
```

```
📋 Processing PO #PO15363269...
📎 Found 2 attachment(s)
⏭️ Skipping existing file: PO15363269_document.pdf
✅ Downloaded 1/2 files
```

### 💾 **With Backup Creation**

```bash
export CREATE_BACKUP_BEFORE_OVERWRITE=true
export VERBOSE_OUTPUT=true
```

```
📋 Processing PO #PO15363269...
📎 Found 2 attachment(s)
💾 Created backup: PO15363269_document.pdf.backup
🔄 Replacing existing file: PO15363269_document.pdf
✅ Downloaded 2/2 files
```

## 🎨 **File Handling Features**

### **Replacement Logic**

- ✅ **Smart Detection**: Identifies existing files with same names
- ✅ **Safe Replacement**: Removes old file before adding new one
- ✅ **Atomic Operation**: File replacement is atomic (no partial states)
- ✅ **Error Handling**: Graceful handling of file system errors

### **Backup System**

- 💾 **Automatic Backups**: Creates `.backup` files before replacement
- 💾 **Preserve History**: Keeps previous versions for safety
- 💾 **Configurable**: Can be enabled/disabled as needed

### **Skip Mode**

- ⏭️ **Skip Existing**: Preserves existing files
- ⏭️ **Continue Processing**: Processes other files normally
- ⏭️ **Report Skipped**: Shows which files were skipped

## 🚀 **Usage Examples**

### **Default Mode (Recommended)**

```bash
python src/main.py
```

**Behavior**: Replace existing files with new versions

### **Skip Existing Files**

```bash
export OVERWRITE_EXISTING_FILES=false
python src/main.py
```

**Behavior**: Skip files that already exist

### **With Backups**

```bash
export CREATE_BACKUP_BEFORE_OVERWRITE=true
export VERBOSE_OUTPUT=true
python src/main.py
```

**Behavior**: Create backups before replacing files

### **Full Control**

```bash
export OVERWRITE_EXISTING_FILES=true
export CREATE_BACKUP_BEFORE_OVERWRITE=true
export VERBOSE_OUTPUT=true
python src/main.py
```

**Behavior**: Replace files with backups and detailed output

## 📋 **File Naming Convention**

### **Standard Format**

```
PO{PO_NUMBER}_{ORIGINAL_FILENAME}
```

### **Examples**

- `PO15363269_document.pdf`
- `PO15363269_invoice.pdf`
- `PO15363269_contract.docx`

### **Backup Files**

- `PO15363269_document.pdf.backup`
- `PO15363269_invoice.pdf.backup`

## 🎯 **What's Fixed**

### **Before (Duplication)**

```
📁 Supplier_Folder/
   📄 PO15363269_document.pdf
   📄 PO15363269_document_1.pdf
   📄 PO15363269_document_2.pdf
   📄 PO15363269_document_3.pdf
```

### **After (Replacement)**

```
📁 Supplier_Folder/
   📄 PO15363269_document.pdf          # Latest version
   📄 PO15363269_document.pdf.backup   # Previous version (if enabled)
   📄 PO15363269_invoice.pdf
   📄 PO15363269_contract.docx
```

## 💡 **Best Practices**

### **For Regular Use**

- Use default settings (replace files)
- Keep folders clean and organized
- Focus on latest versions

### **For Safety**

- Enable backup creation for critical files
- Use verbose output to monitor operations
- Check backup files periodically

### **For Selective Updates**

- Use skip mode to preserve specific files
- Combine with manual file management
- Review skipped files regularly

## 🔄 **Migration Guide**

### **From Old System**

- **Before**: Duplicate files with counters
- **After**: Clean file replacement
- **Benefit**: Organized, manageable file structure

### **For Existing Users**

- No changes needed to workflows
- Same functionality, better file management
- Optional backup creation for safety

## 🎉 **Benefits**

### **File Organization**

- ✅ **No Duplicates**: Clean, organized file structure
- ✅ **Latest Versions**: Always have the most recent files
- ✅ **Easy Management**: Simple file naming and organization
- ✅ **Space Efficient**: No wasted storage on duplicates

### **User Experience**

- ✅ **Predictable**: Consistent file behavior
- ✅ **Safe**: Optional backup creation
- ✅ **Flexible**: Configurable replacement behavior
- ✅ **Transparent**: Clear feedback on file operations

### **Maintenance**

- ✅ **Clean Folders**: No duplicate file cleanup needed
- ✅ **Consistent Naming**: Standard file naming convention
- ✅ **Error Prevention**: Atomic file operations
- ✅ **Easy Recovery**: Backup system for safety

## 🧪 **Testing**

### **Test Script**

```bash
python scripts/test_file_replacement.py
```

### **Test Features**

- ✅ File replacement logic
- ✅ Configuration options
- ✅ Backup creation
- ✅ Skip mode behavior

---

**🎯 CONCLUSION**: The file replacement improvements provide **clean, organized file management** by replacing duplicates instead of creating them, while maintaining **flexibility and safety** through configurable options and backup systems.
