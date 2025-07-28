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

---

## 🚧 Planned Features & Improvements
- [ ] **Configurable PO filtering** (e.g., by supplier, date, status)
- [ ] **Email notifications** on completion or failure
- [ ] **Headless mode improvements** (better support, more reliable)
- [ ] **Download retry logic** for failed attachments
- [ ] **Detailed logging and reporting** (exportable logs)
- [ ] **User-friendly CLI options** (e.g., select range, dry-run)
- [ ] **Docker support** for easier deployment
- [ ] **Automated test suite** for core workflow
- [ ] **Multi-user profile support**
- [ ] **Support for additional Coupa modules** (e.g., invoices)

---

## 🐞 Known Issues / Bug Fixes Planned
- [ ] Occasional browser crash on large batch (monitor and auto-recover)
- [ ] Edge driver orphan processes (ensure full cleanup)
- [ ] Some PO pages may require manual login even after session recovery

---

## 💡 Ideas for Future Improvements
- [ ] Web UI for monitoring and controlling downloads
- [ ] Integration with Slack or Teams for notifications
- [ ] Support for other browsers (Chrome, Firefox)
- [ ] Advanced analytics on PO/download activity
- [ ] Scheduling/automation (run at set intervals)

---

*Last updated: 2024-07-28* 