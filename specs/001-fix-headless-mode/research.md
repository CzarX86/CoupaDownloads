# Research: Fix Headless Mode in EXPERIMENTAL Subproject

## Overview
Research findings for implementing consistent headless mode configuration propagation in the EXPERIMENTAL subproject.

## Key Findings

### Current Implementation Analysis
**Decision**: Interactive setup sets environment variable but browser initialization doesn't consistently honor it  
**Rationale**: Analysis of EXPERIMENTAL/core/main.py shows `os.environ['HEADLESS'] = 'true'` is set during interactive setup, but EXPERIMENTAL/corelib/browser.py doesn't properly check this in all initialization paths  
**Alternatives considered**: 
- Using global configuration object (rejected: adds complexity)
- Passing headless parameter explicitly through all function calls (chosen: clearer data flow)

### Configuration Propagation Strategy
**Decision**: Remove environment variable dependency, pass headless parameter explicitly from interactive setup through to browser initialization  
**Rationale**: Clarification confirmed removing environment variables and using interactive setup as single source of truth. Explicit parameter passing is more predictable than environment variable side effects  
**Alternatives considered**:
- Environment variables (rejected: user requested removal)
- Global state (rejected: harder to test and debug)
- Configuration file (rejected: overkill for boolean flag)

### Browser Initialization Points
**Decision**: Identified 3 key initialization points that need headless parameter: `initialize_driver()`, `start()`, and process worker browser creation  
**Rationale**: Code analysis shows these are the only places where EdgeOptions are configured. Each needs explicit headless parameter  
**Alternatives considered**: 
- Monkey-patching browser options (rejected: too fragile)
- Single initialization wrapper (rejected: breaks existing patterns)

### Failure Handling Strategy
**Decision**: Implement retry once, then prompt user strategy as specified in clarifications  
**Rationale**: Balances automation reliability with user control. Single retry handles transient issues, user prompt handles persistent problems  
**Alternatives considered**:
- Fail immediately (rejected: too brittle)
- Always fallback to visible (rejected: defeats purpose of headless mode)
- Multiple retries (rejected: delays execution unnecessarily)

### Testing Approach
**Decision**: Unit tests for configuration propagation + integration test for full headless flow  
**Rationale**: Unit tests ensure parameter passing works correctly, integration test validates end-to-end browser behavior  
**Alternatives considered**:
- Only integration tests (rejected: harder to debug failures)
- Mock browser completely (rejected: wouldn't catch real headless issues)

## Implementation Considerations

### Edge Browser Headless Support
- Modern Edge versions support `--headless=new` flag
- Fallback to `--headless` for older versions if needed
- CDP (Chrome DevTools Protocol) commands work in headless mode

### Process Worker Implications
- Each worker process needs independent headless configuration
- Configuration must be passed during process spawn
- No shared state between workers

### Backwards Compatibility
- Existing visible mode functionality unchanged
- Interactive setup UI remains the same (just behavior fix)
- No breaking changes to CLI interfaces

## Next Steps
Proceed to Phase 1 design with:
1. Explicit headless parameter threading through call chain
2. Retry/prompt failure handling implementation
3. Comprehensive test coverage plan