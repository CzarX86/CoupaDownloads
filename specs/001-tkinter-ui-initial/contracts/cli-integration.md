# CLI Integration Contract

**Contract ID**: CLI-UI-001
**Date**: 2025-11-12
**Type**: Integration Contract
**Components**: `cli.py` ↔ `ui/main_window.py`

## Overview

Defines the integration point between the existing CLI system and the new UI system, ensuring backward compatibility while adding GUI functionality.

## Interface Definition

### CLI Entry Point Extension

**Function**: `main()`
**Location**: `src/cli.py`
**Extension**: Add `--ui` flag support

**Signature**:
```python
def main():
    parser = argparse.ArgumentParser(description='CoupaDownloads')
    parser.add_argument('--ui', action='store_true', help='Launch with GUI')
    args = parser.parse_args()

    if args.ui:
        from ui.main_window import launch_ui
        launch_ui()
    else:
        # Existing CLI logic
        run_downloads()
```

### UI Launch Function

**Function**: `launch_ui()`
**Location**: `src/ui/main_window.py`
**Purpose**: Entry point for GUI application

**Signature**:
```python
def launch_ui() -> None:
    """Launch the Tkinter GUI application."""
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()
```

**Preconditions**:
- Tkinter must be available
- No existing GUI instances running

**Postconditions**:
- GUI window is displayed
- Application enters event loop
- Function does not return until GUI is closed

## Error Handling

### Tkinter Not Available
**Condition**: `import tkinter` fails
**Response**: Display helpful error message and exit gracefully
**Error Message**: "Tkinter is not available. Please install tkinter for your Python distribution."

### Multiple GUI Instances
**Condition**: Another GUI instance is detected
**Response**: Display warning and allow user to choose whether to continue
**Error Message**: "Another GUI instance may be running. Continue anyway?"

## Backward Compatibility

- **CLI functionality**: Unchanged when `--ui` flag not used
- **Exit codes**: Same as existing CLI behavior
- **Configuration**: Same config files and environment variables
- **Logging**: Same logging behavior and output

## Testing Requirements

- **CLI without --ui**: Functions identically to before
- **CLI with --ui**: Launches GUI successfully
- **GUI launch failure**: Provides clear error messages
- **Multiple launches**: Handles gracefully