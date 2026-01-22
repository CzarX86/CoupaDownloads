# Configuration Management Contract

**Contract ID**: CONFIG-UI-001
**Date**: 2025-11-12
**Type**: Data Contract
**Components**: `ui/config_panel.py` ↔ Configuration Files

## Overview

Defines how configuration settings are managed, persisted, and validated within the UI system.

## Data Structure

### Configuration Schema

```python
ConfigurationSettings = {
    "workers": int,        # 1-10, default: 4
    "download_dir": str,   # Absolute path, default: "./downloads"
    "input_csv": str,      # Absolute path (optional)
    "max_retries": int,    # 0-10, default: 3
    "last_updated": str    # ISO datetime string
}
```

## Interface Definition

### Configuration Panel Class

**Class**: `ConfigPanel`
**Location**: `src/ui/config_panel.py`

**Key Methods**:

```python
class ConfigPanel:
    def __init__(self, parent: tk.Widget) -> None:
        """Initialize configuration panel with UI widgets."""

    def get_config(self) -> dict:
        """Return current configuration as dictionary.
        Returns: ConfigurationSettings dict
        """

    def set_config(self, config: dict) -> None:
        """Update UI with provided configuration.
        Args: config - ConfigurationSettings dict
        """

    def validate_config(self) -> list[str]:
        """Validate current configuration.
        Returns: List of validation error messages (empty if valid)
        """
```

### File Operations

**Functions**:
```python
def save_config(config: dict, filepath: str = DEFAULT_CONFIG_PATH) -> None:
    """Save configuration to JSON file.
    Args:
        config: ConfigurationSettings dict
        filepath: Target file path
    Raises: IOError, ValueError
    """

def load_config(filepath: str = DEFAULT_CONFIG_PATH) -> dict:
    """Load configuration from JSON file.
    Args: filepath - Source file path
    Returns: ConfigurationSettings dict with defaults for missing fields
    Raises: IOError, ValueError
    """
```

## Validation Rules

### Field Validations

- **workers**: `1 <= value <= 10`, integer
- **download_dir**: Path exists and is writable directory
- **input_csv**: If provided, path exists, is readable file, has .csv extension
- **max_retries**: `0 <= value <= 10`, integer
- **last_updated**: Valid ISO datetime string

### Business Rules

- Configuration must have at least one valid download directory
- CSV file is optional but must be valid if specified
- All numeric fields must be within reasonable bounds
- Paths should be absolute to avoid ambiguity

## Error Handling

### Validation Errors
**Invalid workers count**: "Workers must be between 1 and 10"
**Invalid directory**: "Download directory must exist and be writable"
**Invalid CSV file**: "CSV file must exist and be readable"
**Invalid retries**: "Max retries must be between 0 and 10"

### File Operation Errors
**Save failed**: "Could not save configuration: {reason}"
**Load failed**: "Could not load configuration: {reason}, using defaults"

## File Format

### JSON Structure
```json
{
  "workers": 4,
  "download_dir": "/home/user/downloads",
  "input_csv": "/home/user/data/input.csv",
  "max_retries": 3,
  "last_updated": "2025-11-12T10:30:00Z"
}
```

### Default Values
- workers: 4
- download_dir: "./downloads"
- input_csv: null/empty
- max_retries: 3
- last_updated: current timestamp on save

## Testing Requirements

- **Valid configurations**: Save and load correctly
- **Invalid configurations**: Proper validation error messages
- **File I/O errors**: Graceful handling with fallbacks
- **Default values**: Applied when fields missing
- **Backward compatibility**: Handle older config formats