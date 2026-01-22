# Research: Asynchronous/Multiple Workers Implementation

**Date**: 2025-09-29  
**Context**: Fix parallel processing limitations in EXPERIMENTAL subproject due to browser profile conflicts

## Research Questions & Findings

### 1. Browser Profile Isolation Strategy

**Decision**: Create temporary profile copies for each worker  
**Rationale**:
- User has identified this as "the best and safer alternative" after extensive testing
- Approach #1 (tabs) rejected as "risky since errors in a process can break multiple instances"
- Approach #3 (profile reuse) "tried extensively without success"
- Provides complete isolation between workers, preventing cascading failures
- Well-supported by Selenium WebDriver with `--user-data-dir` parameter

**Alternatives considered**:
- **Tab-based processing**: Rejected due to error propagation risk and complexity of tab state management
- **Profile reuse workarounds**: Rejected after user's extensive testing confirmed infeasibility
- **Shared browser instances**: Not viable with Edge profile locking mechanisms

**Implementation approach**:
- Use `tempfile.mkdtemp()` for unique temporary profiles per worker
- Optional base profile copying for settings preservation
- Robust cleanup on worker completion/failure
- Edge `--user-data-dir` for custom profile locations

### 2. Python Parallel Processing Architecture

**Decision**: Use `multiprocessing.Pool` with custom worker processes  
**Rationale**:
- Provides true parallel execution (not limited by GIL)
- Each process gets isolated memory space, preventing interference
- Built-in error handling and worker restart capabilities
- Integrates well with existing EXPERIMENTAL architecture
- Better resource isolation than threading for browser automation

**Alternatives considered**:
- **Threading**: Limited by GIL for CPU-bound browser automation tasks
- **AsyncIO**: Doesn't solve the core browser profile isolation issue
- **Subprocess**: Lower-level, requires more error handling implementation

### 3. Integration with Existing EXPERIMENTAL Architecture

**Decision**: Extend existing components minimally while preserving all functionality  
**Rationale**:
- User requirement: "the rest of the workflow and logic remains untouched"
- Existing HeadlessConfiguration must work with parallel processing
- Maintain current download directory structure and file organization
- Preserve existing logging, progress tracking, and reporting mechanisms

**Integration points**:
- Enhance `MainApp` with optional parallel processing mode
- Extend `BrowserManager` to accept custom profile paths
- Maintain compatibility with `HeadlessConfiguration`
- Preserve existing CSV processing and folder hierarchy logic

### 4. Worker Pool Size and Resource Management

**Decision**: Default 4 workers, configurable up to 8, with resource monitoring  
**Rationale**:
- Based on typical desktop hardware (4-8 CPU cores)
- Browser automation is I/O bound (network, disk operations)
- Memory usage scales with browser instances (~150-200MB per worker)
- User can optimize based on system performance and workload

**Resource considerations**:
- Each worker requires dedicated browser process and profile
- Network bandwidth shared across workers (may become bottleneck)
- Disk I/O for downloads and profile management
- Temporary storage for profile copies

### 5. Error Handling and Recovery Mechanisms

**Decision**: Isolated worker failure with task redistribution and graceful degradation  
**Rationale**:
- Worker failures should not affect other workers (isolation principle)
- Failed tasks should be recoverable and reassignable to healthy workers
- Profile cleanup must occur even on worker crashes or interruption
- System should gracefully degrade to fewer workers if needed

**Recovery strategies**:
- Worker process monitoring and health checks
- Task queue with retry logic and failure tracking
- Graceful degradation to sequential mode on critical failures
- Comprehensive logging for debugging and monitoring
- Resource cleanup even on abnormal termination

### 6. Performance Optimization and Scalability

**Decision**: Optimize for batch processing with configurable parallelism  
**Rationale**:
- Target use case is processing batches of 5+ POs
- Parallel processing overhead should be justified by batch size
- Worker initialization time should be reasonable (<30 seconds per worker)
- System should provide measurable performance improvement

**Performance targets**:
- Significant speedup for batch processing (3-4x improvement target)
- Worker startup time under 30 seconds
- Memory usage scaling reasonably with worker count
- Efficient resource cleanup (under 10 seconds total)

### 7. Backward Compatibility and Migration

**Decision**: Maintain full backward compatibility with optional parallel mode  
**Rationale**:
- Existing users should see no change in default behavior
- Parallel processing should be opt-in initially
- All current interfaces, CLI options, and configurations preserved
- Sequential processing remains the default for single PO operations

**Compatibility requirements**:
- No breaking changes to existing APIs
- Preserve all current functionality and behavior
- Maintain existing test suite compatibility
- Support both sequential and parallel modes seamlessly

## Technology Integration

### Selenium WebDriver Enhancements
- Custom profile creation with `--user-data-dir` parameter
- Per-worker browser options configuration
- Enhanced error handling for profile conflicts and browser crashes
- Integration with existing `BrowserManager` architecture

### Python Multiprocessing Components
- `WorkerPool`: Manages worker lifecycle and task distribution
- `WorkerProcess`: Individual worker with isolated profile and browser context
- `TaskQueue`: Thread-safe task distribution and progress tracking
- `ProfileManager`: Temporary profile creation, copying, and cleanup

### EXPERIMENTAL Subproject Integration
- Minimal changes to existing `core/main.py` logic
- Extension of `corelib/browser.py` for profile isolation
- New `corelib/worker_pool.py` and `corelib/profile_manager.py` modules
- Preservation of all current configuration and behavioral patterns

## Implementation Risk Assessment

### Low Risk
- ✅ Temporary profile creation (well-established pattern)
- ✅ Python multiprocessing integration (standard library, proven approach)
- ✅ Existing architecture preservation (user requirement, minimal changes)
- ✅ Backward compatibility (optional parallel mode, default behavior unchanged)

### Medium Risk
- ⚠️ Memory usage scaling (needs monitoring and configurable limits)
- ⚠️ Profile cleanup robustness (handle locked files, permissions, crashes)
- ⚠️ Network bandwidth utilization (potential bottleneck with many workers)
- ⚠️ Cross-platform compatibility (Windows file locking, macOS permissions)

### High Risk
- 🔴 None identified - approach validated by user testing and established patterns

## Next Steps for Phase 1

1. **Data Models**: WorkerPool, WorkerInstance, ProfileManager, TaskQueue, ProcessingSession
2. **API Contracts**: Worker pool management, profile isolation, task distribution, status monitoring
3. **Test Scenarios**: Parallel processing validation, failure recovery, performance benchmarks
4. **Integration Design**: MainApp coordination, BrowserManager enhancements, HeadlessConfiguration compatibility

---

*Research complete - ready for Phase 1 design*