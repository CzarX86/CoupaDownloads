# Research Phase: Refactor Core Interfaces for UI Integration

**Feature**: 001-refactor-core-interfaces
**Date**: 2025-11-12
**Status**: Complete

## Research Summary

Analysis of existing EXPERIMENTAL/core/main.py codebase to understand current architecture and identify clean interface extraction points. Focus on wrapping existing functionality without functional changes while enabling UI integration through simplified APIs.

## Current Architecture Analysis

### EXPERIMENTAL/core/main.py Structure
- **MainApp class**: Monolithic class handling configuration, processing, and status
- **Configuration handling**: Complex nested configuration system with multiple sources
- **Processing logic**: Core business logic for Coupa downloads and CSV processing
- **Status tracking**: Internal status management without external notification system

### Key Findings
1. **Configuration Complexity**: Multiple configuration layers (CLI args, files, defaults) managed internally
2. **Processing State**: Session-based processing with internal state tracking
3. **Status Updates**: No external notification system - status only accessible through direct queries
4. **Threading Model**: Uses threading for background operations but not exposed cleanly

## Interface Design Research

### ConfigurationManager Requirements
- **Abstraction Level**: Hide configuration complexity behind simple get/set operations
- **Data Types**: Use dict structures for easy serialization to UI
- **Validation**: Maintain existing validation logic but expose errors cleanly
- **Persistence**: Wrap existing save/load mechanisms

### ProcessingController Requirements
- **Session Management**: Generate unique session IDs (UUID4 as clarified)
- **Start/Stop Control**: Clean API for initiating and terminating processing
- **Status Queries**: Real-time status information access
- **Single Session**: No concurrent sessions to avoid complexity

### StatusManager Requirements
- **Subscription Model**: Callback-based notifications for real-time updates
- **Failure Handling**: Robust callback error handling (3-strike unsubscribe rule)
- **Update Frequency**: Immediate updates on state changes, periodic during processing
- **Thread Safety**: Safe cross-thread communication for UI integration

## Technical Constraints Validation

### Python 3.12 Compatibility
- ✅ All target features available (dataclasses, type hints, uuid)
- ✅ Built-in types only requirement satisfied
- ✅ No external dependencies needed

### Backward Compatibility
- ✅ Existing CLI functionality preserved through wrapper pattern
- ✅ No changes to core processing logic
- ✅ Interface layer is purely additive

### Performance Requirements
- ✅ Configuration operations: <100ms target achievable with caching
- ✅ Status updates: <50ms target feasible with direct callbacks
- ✅ Import time: <1s target met with lazy loading

## Risk Assessment

### Low Risk Items
- Interface extraction without functional changes
- Built-in types only (no dependency issues)
- Single-session design (avoids concurrency complexity)

### Medium Risk Items
- Callback failure handling (requires careful implementation)
- Thread safety for status updates (needs proper synchronization)

### Mitigation Strategies
- Comprehensive unit tests for all interfaces
- Integration tests verifying backward compatibility
- Gradual rollout with feature flags if needed

## Implementation Approach

### Phase 1: ConfigurationManager
- Extract configuration logic into dedicated class
- Implement dict-based API
- Add validation wrapper

### Phase 2: ProcessingController
- Create session management wrapper
- Implement start/stop/status methods
- Ensure single-session constraint

### Phase 3: StatusManager
- Build subscription system
- Implement callback management
- Add failure handling logic

### Testing Strategy
- Unit tests for each interface class
- Integration tests with existing MainApp
- Backward compatibility verification
- Performance benchmarking

## Success Criteria Alignment

All research validates achievability of success criteria:
- ✅ Interface instantiation <1s (simple class imports)
- ✅ Configuration operations <100ms (dict operations)
- ✅ Processing control maintains CLI compatibility (wrapper pattern)
- ✅ Status updates <50ms (direct callbacks)
- ✅ Built-in types only (dict, str, bool, UUID)

## Next Steps

Proceed to data model design phase with confidence that technical approach is sound and requirements are achievable.