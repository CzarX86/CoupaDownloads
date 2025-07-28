# CoupaDownloads Roadmap & Pipeline

This document tracks the current state, planned features, improvements, and bug fixes for the CoupaDownloads project.

---

## ✅ Current Features
- Automated download of PO attachments from Coupa
- Robust CSV processing and status tracking
- Persistent login session (browser remains open)
- Proper PO file naming (no duplicate POPO prefix)
- Efficient workflow (no unnecessary navigation)
- Automatic browser session recovery
- Progress tracking for PO processing
- Error handling for browser crashes and session loss
- Profile-based browser sessions for persistent login

---

## 🚧 Planned Features & Improvements
- [ ] **Enhance login persistency** (improve session handling and reduce re-login prompts, browser is not kept open on coupa home page after workflow execution)
- [ ] **Handle download of files already present in the download folder** (skip or prompt for overwrite)
- [ ] **Right-click window remains open during execution but it should be closed after use ** (close right-click download window)
- [ ] **Enhance feedback on terminal during execution for better readability, maybe using a tabular format if possible** (improved status, color, and grouping)
- [ ] **Remove download folder from CSV file** (as it duplicates supplier info)
- [ ] **Headless mode improvements** (better support, more reliable)
- [ ] **Download retry logic** for failed attachments
- [ ] **Detailed logging and reporting** (exportable logs)
- [ ] **Docker support** for easier deployment
- [ ] **Automated test suite** for core workflow

---

## 🔧 Download Method Optimization & Efficiency Improvements
- [ ] **Remove inefficient download methods** (current cascading approach has redundancy)
- [ ] **Optimize direct HTTP download method** (most efficient, should be primary)
- [ ] **Remove right-click Save As method** (complex, OS-dependent, unreliable)
- [ ] **Simplify temporary directory method** (keep as fallback only)
- [ ] **Implement batch download capability** (download multiple files simultaneously)
- [ ] **Add download progress indicators** (real-time progress for large files)
- [ ] **Optimize file naming logic** (reduce redundant operations)
- [ ] **Implement download caching** (avoid re-downloading same files)
- [ ] **Add download speed optimization** (parallel downloads, connection pooling)
- [ ] **Remove unnecessary browser interactions** (minimize clicks, scrolls, waits)

### Current Inefficiencies Identified:
1. **Cascading Download Methods**: Three different methods tried sequentially (direct HTTP → right-click → temp directory)
2. **Right-Click Method**: Complex, OS-dependent, requires keyboard simulation
3. **Temporary Directory Overhead**: Creates temp dirs, changes download paths, moves files
4. **Redundant File Operations**: Multiple file existence checks and naming operations
5. **Sequential Downloads**: Files downloaded one by one instead of in parallel
6. **Excessive Browser Interactions**: Unnecessary scrolling, clicking, waiting between downloads

### Planned Optimizations:
1. **Primary Method**: Direct HTTP download with proper authentication
2. **Fallback Only**: Simplified temporary directory method
3. **Batch Processing**: Download multiple files simultaneously
4. **Smart Caching**: Track downloaded files to avoid duplicates
5. **Reduced Browser Interaction**: Minimize clicks and page interactions

---

## 🐞 Known Issues / Bug Fixes Planned
- [ ] **Stacktrace being shown on terminal during execution even though set to false in config file**
- [ ] Occasional browser crash on large batch (monitor and auto-recover)
- [ ] Edge driver orphan processes (ensure full cleanup)
- [ ] Some PO pages may require manual login even after session recovery

---

## 💡 Ideas for Future Improvements
- [ ] Web UI for monitoring and controlling downloads
- [ ] Integration with Slack or Teams for notifications
- [ ] Advanced analytics on PO/download activity

---

*Last updated: 2024-07-28* 