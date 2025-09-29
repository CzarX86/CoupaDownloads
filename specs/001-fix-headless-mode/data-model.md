# Data Model: Fix Headless Mode in EXPERIMENTAL Subproject

## Core Entities

### HeadlessConfiguration
**Purpose**: Represents the headless mode preference and its propagation through the system

**Fields**:
- `enabled: bool` - Whether headless mode is enabled
- `source: str` - Always "interactive_setup" (single source of truth)
- `retry_attempted: bool` - Whether initialization retry was attempted
- `fallback_to_visible: bool` - Whether user chose visible mode fallback

**Validation Rules**:
- `enabled` must be boolean
- `source` must equal "interactive_setup"
- `retry_attempted` only true if initial headless initialization failed
- `fallback_to_visible` only true if retry also failed and user chose visible mode

**State Transitions**:
1. **Initial**: `enabled=False, source="interactive_setup", retry_attempted=False, fallback_to_visible=False`
2. **User Selection**: `enabled=True/False` based on interactive setup choice
3. **Retry State**: `retry_attempted=True` if headless initialization fails
4. **Fallback State**: `fallback_to_visible=True` if user chooses visible mode after retry failure

### BrowserInstance
**Purpose**: Represents individual browser sessions with headless configuration

**Fields**:
- `headless_mode: bool` - Current browser headless state
- `initialization_attempts: int` - Number of initialization attempts made
- `process_id: str` - Identifier for process worker (if applicable)
- `edge_options: dict` - Browser options including headless flags

**Validation Rules**:
- `initialization_attempts` must be 1 or 2 (initial + retry)
- `headless_mode` must match HeadlessConfiguration.enabled (unless fallback occurred)
- `process_id` required for process worker instances

**Relationships**:
- Each BrowserInstance is configured by one HeadlessConfiguration
- Process workers have independent BrowserInstance entities

### InteractiveSetupSession
**Purpose**: Represents user configuration session including headless preference

**Fields**:
- `headless_preference: bool` - User's headless mode choice
- `session_timestamp: datetime` - When setup was completed
- `configuration_applied: bool` - Whether config was successfully applied

**Validation Rules**:
- `headless_preference` must be boolean
- `session_timestamp` must be valid datetime
- `configuration_applied` only true after successful browser initialization

**Relationships**:
- One InteractiveSetupSession creates one HeadlessConfiguration
- One HeadlessConfiguration may affect multiple BrowserInstance entities

## Entity Lifecycle

```
InteractiveSetupSession → HeadlessConfiguration → BrowserInstance(s)
        ↓                        ↓                      ↓
    User Choice            Parameter Passing      Browser Launch
```

## Data Flow

1. **Collection**: InteractiveSetupSession captures user preference
2. **Configuration**: HeadlessConfiguration created with preference
3. **Propagation**: Configuration passed to all browser initialization points
4. **Application**: Each BrowserInstance respects the headless setting
5. **Failure Handling**: Retry logic updates HeadlessConfiguration state
6. **User Choice**: Fallback handling updates final configuration state

## Constraints

- No persistent storage required (all in-memory during execution)
- Configuration is immutable once browser instances are created
- Process workers get configuration copy, not shared reference
- All state transitions must be logged for debugging