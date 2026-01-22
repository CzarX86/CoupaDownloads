# Quick Start: Tkinter UI

**Feature**: 002-tkinter-ui
**Date**: 2025-11-12

## Prerequisites

- Python 3.12 installed
- Tkinter available (included with Python on most platforms)
- **Graphical desktop environment** (GUI display available)
- Existing CoupaDownloads CLI installation
- Valid CSV file with download targets
- Writable download directory

## Installation

The GUI is integrated with the existing CLI. No additional installation required.

```bash
# Verify Tkinter availability
python -c "import tkinter; print('Tkinter available')"
```

## Launch GUI

### From Command Line
```bash
# Launch GUI mode
poetry run python -m src.cli.main --ui

# Or use the convenience script
poetry run python launch_gui.py

# Or with existing CLI
poetry run python tools/feedback_cli.py --ui
```

### Direct Python Execution
```python
from src.ui.gui import CoupaDownloadsGUI
import tkinter as tk

root = tk.Tk()
app = CoupaDownloadsGUI(root)
root.mainloop()
```

### Using Launch Script
```bash
# Direct execution (requires proper PYTHONPATH)
python launch_gui.py

# Or with poetry
poetry run python launch_gui.py
```

## Configuration Setup

1. **Launch the GUI** using one of the methods above
2. **Configure Settings**:
   - Click "Browse" next to CSV File to select your input file
   - Click "Browse" next to Download Directory to choose output location
   - Set Worker Count (1-10, default: 3)
   - Set Max Retries (0-5, default: 2)
3. **Save Configuration** - settings persist across sessions

## Basic Usage

### Start Downloads
1. Ensure configuration is set and valid (green checkmarks)
2. Click the **"Start Downloads"** button
3. Monitor progress in the status bar
4. Button becomes disabled during operation

### Stop Downloads
1. Click the **"Stop Downloads"** button (enabled during operation)
2. System gracefully stops all workers
3. Status updates show stopping progress

### Monitor Progress
- **Status Bar**: Shows current operation status
- **Progress Indicators**: Visual feedback during downloads
- **Error Messages**: Displayed for configuration or runtime issues

## Troubleshooting

### GUI Won't Launch
```bash
# Check Tkinter installation
python -c "import tkinter; tkinter._test()"

# On Linux, install tkinter package
sudo apt-get install python3-tk  # Ubuntu/Debian
sudo dnf install tkinter        # Fedora

# Check if running in headless environment
echo $DISPLAY  # Should show something like :0 or :1
```

### Headless Environment
If you're running in a headless environment (no GUI display), the GUI cannot launch:
```bash
# The CLI will show this error:
# Error: GUI is not available on this system.

# Solutions:
# 1. Use a graphical desktop environment
# 2. Use X11 forwarding if connecting via SSH: ssh -X user@host
# 3. Use VNC or similar remote desktop solution
# 4. Run on a local machine with GUI
```

### Configuration Errors
- **"CSV file not found"**: Verify file exists and path is correct
- **"Directory not writable"**: Check permissions on download directory
- **"Invalid worker count"**: Must be integer between 1-10

### Performance Issues
- Reduce worker count if system becomes unresponsive
- Ensure adequate free disk space in download directory
- Close other memory-intensive applications

## Advanced Usage

### Command Line Integration
The GUI respects all existing CLI parameters. Use `--help` to see available options.

### Configuration File Location
- **Location**: `~/.coupadownloads/config.ini`
- **Permissions**: Automatically set to secure (user-only access)
- **Backup**: Previous version saved as `config.ini.backup`

### Logging
- GUI operations logged to standard CoupaDownloads log
- Status messages also available in log files
- No sensitive information included in logs

## Development

### Testing GUI Components
```bash
# Run GUI-specific tests
poetry run pytest tests/unit/test_gui.py -v

# Run integration tests
poetry run pytest tests/integration/test_ui_cli.py -v
```

### Building for Distribution
The GUI integrates with existing PyInstaller configuration for standalone executables.

## Support

- Check status bar for real-time feedback
- Review application logs for detailed error information
- Ensure CSV file format matches expected structure
- Verify network connectivity for download operations