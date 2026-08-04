# SortableJS (vendored)

- Version: **1.15.7**
- Package: <https://www.npmjs.com/package/sortablejs/v/1.15.7>
- Source archive: <https://registry.npmjs.org/sortablejs/-/sortablejs-1.15.7.tgz>
- License: MIT (`LICENSE`)
- `Sortable.min.js` SHA-256: `bf4241bc73fef7f11c59a283a69fe8051cdd31c6d8ff5a2b9ba219e7831fcf76`
- `LICENSE` SHA-256: `e94dfc31e800d169257569db270457c9f028440c9ccae41e7eb78b2db18f1298`

The file is bundled locally because Contract Downloader must work offline and must
not load executable code from a CDN. `hierarchy-sorter.js` is the application
adapter; application code should not call SortableJS directly.

## Updating

1. Review the new SortableJS release and license.
2. Run `npm pack sortablejs@<version>` in a temporary directory.
3. Copy `package/Sortable.min.js` and `package/LICENSE` here.
4. Update the version and checksums in this file and in
   `tests/e2e/test_gui_hierarchy_workflow.py`.
5. Run the hierarchy E2E tests in Chromium and WebKit.
