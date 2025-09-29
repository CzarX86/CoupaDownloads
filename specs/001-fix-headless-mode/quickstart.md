# Quickstart: Fix Headless Mode in EXPERIMENTAL Subproject

## Prerequisites
- Python 3.12 with Poetry installed
- Microsoft Edge browser available
- CoupaDownloads repository cloned
- On branch `001-fix-headless-mode`

## Quick Validation Test

### 1. Test Current Broken Behavior
```bash
cd /path/to/CoupaDownloads
git checkout 001-fix-headless-mode

# Run EXPERIMENTAL subproject
cd EXPERIMENTAL
poetry run python core/main.py

# When prompted for "Run browser in headless mode? [Y/n]:"
# Choose "Y" (Yes)
# EXPECTED CURRENT ISSUE: Browser window still appears (broken behavior)
```

### 2. After Implementation - Test Fixed Behavior
```bash
# Same setup as above
cd EXPERIMENTAL
poetry run python core/main.py

# When prompted for "Run browser in headless mode? [Y/n]:"
# Choose "Y" (Yes)
# EXPECTED FIXED BEHAVIOR: No browser window appears (headless mode working)
```

## Development Workflow

### 1. Set Up Development Environment
```bash
# Ensure you're in the correct branch
git branch --show-current  # Should show: 001-fix-headless-mode

# Install dependencies
poetry install

# Run existing tests to ensure baseline
poetry run pytest EXPERIMENTAL/ -v
```

### 2. Key Files to Modify
Based on research and design:

```
EXPERIMENTAL/core/main.py
├── _interactive_setup() function
└── MainApp.process_single_po() and worker functions

EXPERIMENTAL/corelib/browser.py
├── BrowserManager.initialize_driver() method
├── BrowserManager.start() method
└── BrowserManager._create_browser_options() method

EXPERIMENTAL/corelib/config.py
└── Remove HEADLESS environment variable dependency
```

### 3. Implementation Verification Steps

#### Step 1: Unit Tests
```bash
# Create and run contract tests
poetry run pytest tests/unit/test_headless_config.py -v

# Expected: All contract tests pass
```

#### Step 2: Integration Tests
```bash
# Test headless mode end-to-end
poetry run pytest tests/integration/test_headless_flow.py -v

# Expected: Headless mode actually prevents browser windows
```

#### Step 3: Manual Validation
```bash
# Test interactive setup with headless=True
cd EXPERIMENTAL
poetry run python core/main.py

# Verify:
# 1. Prompt asks for headless mode
# 2. Choosing "Y" results in no visible browser
# 3. Processing continues normally
# 4. Logs indicate "headless mode activated"
```

#### Step 4: Process Worker Validation
```bash
# Test with process pool mode enabled
cd EXPERIMENTAL
poetry run python core/main.py

# When prompted:
# - Choose process pool mode: Y
# - Choose headless mode: Y

# Verify:
# - Multiple worker processes spawn
# - No browser windows appear for any worker
# - All workers complete successfully
```

### 4. Failure Handling Verification
```bash
# Test failure handling (may require simulating Edge issues)
# 1. Run with headless mode enabled
# 2. If headless fails to initialize:
#    - System should retry once automatically
#    - If retry fails, user should be prompted
#    - User can choose visible mode or stop execution
```

## Success Criteria Checklist

### Functional Requirements Validation
- [ ] **FR-001**: Interactive setup headless choice affects browser initialization
- [ ] **FR-002**: Consistent headless config across all browser initialization points
- [ ] **FR-003**: Interactive setup allows headless configuration (no environment vars)
- [ ] **FR-004**: Headless parameter passed to all browser manager calls
- [ ] **FR-005**: Process workers respect headless mode independently
- [ ] **FR-006**: Identical functionality between headless and visible modes
- [ ] **FR-007**: Clear feedback when headless mode is enabled
- [ ] **FR-008**: Appropriate headless browser arguments applied
- [ ] **FR-009**: Retry once, then prompt user on headless failure

### User Acceptance Scenarios
- [ ] **Scenario 1**: User selects headless mode → no browser windows appear
- [ ] **Scenario 2**: User selects visible mode → browser windows appear normally
- [ ] **Scenario 3**: System runs successfully in headless CI/CD environment
- [ ] **Scenario 4**: Process workers all respect headless configuration

### Edge Cases
- [ ] **Edge 1**: Headless failure → retry → user choice flow works
- [ ] **Edge 2**: Browser crashes handled same way in both modes
- [ ] **Edge 3**: Mid-session preference changes affect subsequent browsers

## Troubleshooting

### Common Issues
1. **Browser still appears despite headless=True**
   - Check: Is `--headless=new` in browser options?
   - Check: Are all initialization paths using headless parameter?

2. **Process workers not respecting headless mode**
   - Check: Is headless config passed to worker args tuple?
   - Check: Worker initialization using correct config?

3. **Headless initialization fails**
   - Check: Edge browser version supports headless mode
   - Check: Retry and user prompt logic working correctly

### Debug Commands
```bash
# Enable verbose logging for browser initialization
export SHOW_SELENIUM_LOGS=true
poetry run python core/main.py

# Check browser options being applied
# Look for "--headless=new" in debug output
```

## Next Steps After Implementation
1. Run full test suite: `poetry run pytest`
2. Update documentation if needed
3. Create PR with implementation
4. Move planning artifacts to `PR_PLANS/Implemented/`