# Known Issues

## Playwright Test Failures: Log Capture

### Description
The Playwright tests for the following scenarios are failing due to missing console log messages in the test report:
1. **Start without file**: The expected error message "Please select an input file before starting." is not being captured.
2. **Stop during execution**: The expected system message "Stop requested. Waiting current operation to end..." is not being captured.

### Impact
These failures indicate that the `logToConsole` function in the frontend is not properly registering messages in the Playwright test environment. This affects the reliability of the test suite but does not impact the actual functionality of the application.

### Steps to Reproduce
1. Run the Playwright test suite:
   ```bash
   uv run --project . pytest -q tests/e2e/test_gui_playwright_probe.py
   ```
2. Observe the failures for the tests:
   - `test_gui_playwright_probe_start_without_file`
   - `test_gui_playwright_probe_stop_during_execution`

### Root Cause
The `logToConsole` function is not emitting messages in a way that Playwright can capture during the test execution. This may be due to:
- Timing issues where the logs are emitted before Playwright attaches its listener.
- Logs not being flushed to the DOM or console in the expected format.

### Proposed Fix
1. Ensure that `logToConsole` emits messages consistently and that Playwright's `page.on("console")` listener is attached early enough.
2. Add explicit flushing of logs to the DOM or console to ensure they are captured.
3. Validate that the Playwright bridge correctly relays all console messages to the test report.

### Status
- **Priority**: Medium
- **Owner**: Open
- **Next Steps**: Debug the `logToConsole` function and Playwright's log capture mechanism.

### Workaround
Manually verify the application behavior for these scenarios until the test suite is fixed.