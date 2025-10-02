# Research: Parallel Default Profile Loading & Cloning

## Edge Profile Management Research

### Decision: Use filesystem-based profile cloning with atomic copy operations
**Rationale**: 
- Edge profiles are directory structures containing user data, settings, and session state
- Selenium's `--user-data-dir` option allows specifying custom profile directories
- Python's `shutil.copytree()` provides atomic directory copying with ignore patterns
- Temporary directories can be created with `tempfile.mkdtemp()` for automatic cleanup

**Alternatives considered**:
- Symbolic links: Rejected due to Windows compatibility issues and profile corruption risk
- Profile sharing: Rejected due to Edge's single-profile-lock limitation
- Docker containers: Rejected as overkill for desktop automation

### Decision: Multi-level verification strategy combining browser capabilities and authentication checks
**Rationale**:
- WebDriver capabilities report actual profile path in use
- Authentication verification via lightweight Coupa endpoint confirms session state
- File-level verification of key artifacts (cookies.sqlite) ensures clone completeness
- Multiple verification points reduce false positives

**Alternatives considered**:
- Single verification method: Rejected as insufficient for reliability requirements
- Deep profile introspection: Rejected due to complexity and maintenance overhead

### Decision: Per-worker retry with exponential backoff and circuit breaker pattern
**Rationale**:
- Tenacity library provides robust retry mechanisms with configurable policies
- Per-worker isolation prevents cascading failures across the worker pool
- Circuit breaker pattern prevents resource exhaustion during systematic failures
- Structured logging (structlog) enables per-worker diagnostic tracking

**Alternatives considered**:
- Global retry policy: Rejected due to blast radius concerns
- Immediate failure: Rejected due to reliability requirements for transient issues

## Browser Automation Best Practices

### Decision: Edge-specific WebDriver configuration with profile isolation
**Rationale**:
- Microsoft Edge WebDriver provides native profile support via `--user-data-dir`
- Profile lock detection via file system monitoring prevents concurrent access
- Edge's sandbox isolation prevents profile corruption between instances
- Existing project already standardized on Edge browser

**Alternatives considered**:
- Chrome browser: Rejected to maintain consistency with existing automation
- Firefox: Rejected due to different profile management paradigm
- Multi-browser support: Deferred for future iteration

### Decision: Temporary profile lifecycle management with cleanup guarantees
**Rationale**:
- Context managers ensure cleanup even during exceptions
- `atexit` handlers provide backup cleanup for process termination
- Unique temporary directories prevent naming conflicts
- Graceful vs forced cleanup handles different termination scenarios

**Alternatives considered**:
- Persistent profile cache: Rejected due to disk space concerns and staleness issues
- Manual cleanup: Rejected due to reliability requirements

## Parallel Processing Integration

### Decision: Integrate with existing worker_pool.py architecture
**Rationale**:
- EXPERIMENTAL/workers/worker_pool.py already manages parallel browser instances
- Profile management fits naturally as a worker initialization concern
- Existing resource monitoring can track profile creation overhead
- Minimal disruption to established parallel processing patterns

**Alternatives considered**:
- Separate profile service: Rejected due to added complexity and coordination overhead
- Profile-per-request: Rejected due to startup cost implications

### Decision: Configurable concurrency limits for profile cloning
**Rationale**:
- High-concurrency scenarios (N >= 6) can cause disk I/O bottlenecks
- Semaphore-based throttling prevents resource exhaustion
- Configurable limits allow tuning for different hardware profiles
- Queue-based approach maintains startup order guarantees

**Alternatives considered**:
- Unlimited concurrency: Rejected due to resource exhaustion risk
- Sequential cloning: Rejected due to startup latency implications

## Platform-Specific Considerations

### Decision: Cross-platform path handling with OS-specific defaults
**Rationale**:
- macOS Edge profile: `~/Library/Application Support/Microsoft Edge/Default`
- Windows Edge profile: `%LOCALAPPDATA%/Microsoft/Edge/User Data/Default`
- Python `pathlib` provides cross-platform path manipulation
- Environment variable overrides enable custom profile locations

**Alternatives considered**:
- Single hardcoded path: Rejected due to multi-platform requirements
- Runtime detection only: Rejected due to configuration flexibility needs

### Decision: File system permission handling with fallback strategies
**Rationale**:
- Profile directories may have restrictive permissions
- Fallback to read-only profile copy when modification fails
- Clear error messages for permission-related failures
- Documentation of required permissions for different scenarios

**Alternatives considered**:
- Assume full permissions: Rejected due to enterprise environment constraints
- Fail fast on permission issues: Rejected due to usability concerns

## Verification Strategy Details

### Decision: Three-tier verification approach
**Rationale**:
1. **Capability verification**: Fast check via WebDriver API
2. **Authentication verification**: Functional check via Coupa endpoint
3. **Artifact verification**: Deep check via file system comparison

Each tier provides different confidence levels and failure diagnostics.

**Alternatives considered**:
- Single verification tier: Rejected due to reliability requirements
- Five+ tier verification: Rejected due to complexity and startup latency

### Decision: Configurable verification timeouts and thresholds
**Rationale**:
- Network conditions affect authentication verification timing
- Different environments require different timeout values
- Graceful degradation when verification takes longer than expected
- Operational flexibility for different deployment scenarios

**Alternatives considered**:
- Fixed timeouts: Rejected due to environment variability
- No timeout limits: Rejected due to hang prevention requirements