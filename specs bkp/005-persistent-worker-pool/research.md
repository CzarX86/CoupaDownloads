# Research: Persistent Worker Pool Implementation

## Technical Decisions

### Worker Pool Architecture Pattern
**Decision**: Process-based worker pool with centralized orchestration  
**Rationale**: Python multiprocessing provides true process isolation, preventing browser session crashes from affecting other workers. Centralized state management in main process eliminates complex inter-worker synchronization.  
**Alternatives considered**: 
- Thread-based workers (rejected: browser automation blocks threads)
- Distributed queue system (rejected: over-engineering for 1-8 workers)
- Actor model (rejected: adds complexity without clear benefits)

### Browser Session Management
**Decision**: One persistent browser session per worker process  
**Rationale**: Maintains session state (cookies, authentication) across PO processing while providing isolation. Tab-based processing within each session optimizes resource usage.  
**Alternatives considered**:
- Session pooling (rejected: complex lifecycle management)
- Browser-per-PO (current approach, rejected: resource intensive)
- Shared browser with tab isolation (rejected: cross-contamination risk)

### State Management Strategy
**Decision**: Centralized state in main process with message passing  
**Rationale**: Simple coordination, clear ownership of shared data (PO queue, results), natural fit with Python multiprocessing queues.  
**Alternatives considered**:
- Shared memory (rejected: complex synchronization)
- Database coordination (rejected: overkill for ephemeral data)
- Worker-to-worker communication (rejected: coordination complexity)

### Profile Management Enhancement
**Decision**: Extend existing EXPERIMENTAL/workers/profile_manager.py  
**Rationale**: Leverages existing profile cloning and corruption detection infrastructure. Proven reliability in current parallel worker implementations.  
**Alternatives considered**:
- New profile manager (rejected: duplicate effort)
- Profile-per-session (rejected: storage overhead)
- Shared profile (rejected: security and isolation concerns)

### Memory Monitoring Integration
**Decision**: Use psutil for system memory tracking with 75% threshold  
**Rationale**: Matches clarified requirement for adaptive memory management. psutil provides cross-platform memory statistics.  
**Alternatives considered**:
- Process-specific memory limits (rejected: doesn't prevent system-wide issues)
- Fixed memory limits (rejected: not adaptive to system capabilities)
- No memory monitoring (rejected: requirement violation)

### Graceful Shutdown Implementation
**Decision**: Signal handling in main process only with 1-minute timeout  
**Rationale**: Prevents signal handling conflicts between processes. Clear timeout requirement from clarifications. Allows workers to complete current PO.  
**Alternatives considered**:
- Signal handling in workers (rejected: coordination complexity)
- Immediate shutdown (rejected: may corrupt in-progress POs)
- Longer timeout (rejected: clarified requirement is 1 minute)

### Observability Architecture
**Decision**: Configurable observability levels (basic/detailed/complete) during setup  
**Rationale**: Matches clarified requirement for user choice. Allows debugging without overwhelming normal operation.  
**Alternatives considered**:
- Always-on detailed logging (rejected: performance impact)
- Fixed minimal logging (rejected: debugging difficulty)
- Runtime configurable (rejected: complexity for little benefit)

### Load Balancing Strategy
**Decision**: Static initial distribution followed by adaptive rebalancing  
**Rationale**: Matches clarified hybrid approach. Simple round-robin start with performance-based adjustments.  
**Alternatives considered**:
- Pure round-robin (rejected: doesn't handle performance differences)
- Pure adaptive (rejected: complex initial distribution)
- Worker pull model (rejected: coordination overhead)

## Integration Points

### EXPERIMENTAL Subproject Integration
- Leverage existing `EXPERIMENTAL/workers/profile_manager.py` for profile handling
- Extend `EXPERIMENTAL/workers/task_queue.py` for PO distribution
- Use `EXPERIMENTAL/corelib/browser.py` for browser automation patterns
- Integrate with `EXPERIMENTAL/core/main.py` for entry point coordination

### Main Project Integration
- Minimal changes to `src/` directory (maintain existing interfaces)
- Replace current per-PO worker spawning in main processing loop
- Preserve existing CLI interface and user experience patterns
- Maintain compatibility with existing configuration and logging

### Testing Strategy
- Integration tests for worker pool lifecycle
- Session persistence validation across PO processing
- Graceful shutdown behavior under various scenarios
- Memory threshold violation handling
- Profile corruption recovery testing

## Implementation Approach

### Development Phases
1. **Phase 1**: Core worker pool implementation in EXPERIMENTAL/workers/
2. **Phase 2**: Integration with existing browser automation components
3. **Phase 3**: Observability and monitoring implementation
4. **Phase 4**: Graceful shutdown and error recovery
5. **Phase 5**: Load balancing and performance optimization

### Risk Mitigation
- Browser session stability: Implement robust restart mechanisms
- Memory leaks: Active monitoring with automatic worker cycling
- Profile corruption: Leverage existing detection and recovery patterns
- Signal handling: Clear process boundaries and timeout enforcement
- Performance regression: Maintain existing sequential fallback initially

## Dependencies and Prerequisites

### Required Components (Existing)
- `EXPERIMENTAL/workers/profile_manager.py` - Profile cloning and management
- `EXPERIMENTAL/corelib/browser.py` - Browser automation utilities
- `EXPERIMENTAL/corelib/downloader.py` - PO processing logic
- Python multiprocessing module - Process management
- psutil library - Memory monitoring

### New Components (To Implement)
- `EXPERIMENTAL/workers/persistent_pool.py` - Main orchestrator
- `EXPERIMENTAL/workers/worker_process.py` - Individual worker implementation
- `EXPERIMENTAL/workers/monitoring.py` - Memory and performance tracking
- Enhanced configuration handling for observability levels
- Signal handling and graceful shutdown coordination

### Testing Requirements
- Browser automation test infrastructure
- Multi-process testing capabilities
- Memory usage validation tools
- Signal handling test utilities
- Session persistence validation mechanisms