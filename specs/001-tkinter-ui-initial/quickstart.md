# Quickstart: Tkinter UI Initial Implementation

**Date**: 2025-11-12
**Feature**: Tkinter UI Initial Implementation
**Estimated Effort**: 4-6 hours

## Overview

This guide provides step-by-step instructions for implementing the initial Tkinter UI feature. The implementation focuses on creating a basic GUI that integrates with the existing CLI system.

## Prerequisites

- Python 3.12 installed
- Tkinter available (`python -m tkinter` should open a test window)
- Poetry environment set up
- Basic understanding of Tkinter widgets

## Implementation Steps

### Step 1: Create UI Module Structure

```bash
cd /Users/juliocezar/Dev/CoupaDownloads_Refactoring
mkdir -p src/ui
touch src/ui/__init__.py
```

### Step 2: Implement CLI Integration

Modify `src/cli.py` to add the `--ui` flag:

```python
# Add to imports
import argparse

# Modify main() function
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

### Step 3: Create Main Window (`src/ui/main_window.py`)

Implement the main application window with basic structure:

```python
import tkinter as tk
from tkinter import ttk
from config_panel import ConfigPanel
import threading
import multiprocessing as mp

class MainWindow:
    def __init__(self, root, status_queue=None):
        self.root = root
        self.root.title("CoupaDownloads - Download Manager")
        self.root.geometry("800x600")
        self.status_queue = status_queue or mp.Queue()

        self.setup_menu()
        self.setup_toolbar()
        self.setup_main_frame()
        self.setup_status_bar()

        # Start status monitoring
        self.start_status_monitoring()

    def setup_menu(self):
        # Implement menu bar with File, View, Help
        pass

    def setup_toolbar(self):
        # Implement toolbar with Start/Stop buttons
        pass

    def setup_main_frame(self):
        # Implement notebook with Configuration tab
        pass

    def setup_status_bar(self):
        # Implement status bar for messages
        pass

    def start_status_monitoring(self):
        # Start thread to monitor status queue
        pass

    def start_downloads(self):
        # Launch download process
        pass

    def stop_downloads(self):
        # Stop download process
        pass

def launch_ui():
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()
```

### Step 4: Create Configuration Panel (`src/ui/config_panel.py`)

Implement the configuration interface:

```python
import tkinter as tk
from tkinter import ttk, filedialog

class ConfigPanel:
    def __init__(self, parent):
        self.parent = parent
        self.setup_widgets()

    def setup_widgets(self):
        # Create worker settings frame
        # Create CSV settings frame
        # Create retry settings frame
        pass

    def browse_download_dir(self):
        # Implement directory browser
        pass

    def browse_input_csv(self):
        # Implement file browser
        pass

    def get_config(self):
        # Return configuration dict
        return {
            'workers': 4,
            'download_dir': './downloads',
            'input_csv': '',
            'max_retries': 3
        }

    def validate_config(self):
        # Validate configuration
        return []
```

### Step 5: Add Status Communication

Implement status monitoring in MainWindow:

```python
def start_status_monitoring(self):
    """Start monitoring status queue in background thread."""
    def monitor_loop():
        while True:
            try:
                status = self.status_queue.get(timeout=1)
                # Update status bar on main thread
                self.root.after(0, lambda: self.update_status_display(status))
            except:
                continue

    thread = threading.Thread(target=monitor_loop, daemon=True)
    thread.start()

def update_status_display(self, status):
    """Update status bar with new message."""
    # Update status bar text
    pass
```

### Step 6: Integrate with Core System

Connect UI controls to download operations:

```python
def start_downloads(self):
    """Launch downloads with current configuration."""
    config = self.config_panel.get_config()

    # Validate configuration
    errors = self.config_panel.validate_config()
    if errors:
        messagebox.showerror("Configuration Error", "\n".join(errors))
        return

    # Launch download process
    # self.download_process = mp.Process(target=run_downloads, args=(config, self.status_queue))
    # self.download_process.start()

    # Update UI state
    self.start_btn.config(state=tk.DISABLED)
    self.stop_btn.config(state=tk.NORMAL)
    self.status_var.set("Running downloads...")

def stop_downloads(self):
    """Stop download operations."""
    if hasattr(self, 'download_process'):
        # Signal stop
        self.download_process.terminate()
        self.download_process.join(timeout=5)

    # Update UI state
    self.start_btn.config(state=tk.NORMAL)
    self.stop_btn.config(state=tk.DISABLED)
    self.status_var.set("Ready")
```

## Testing the Implementation

### Basic UI Test

```bash
cd /Users/juliocezar/Dev/CoupaDownloads_Refactoring
python -m src.cli --ui
```

**Expected Results:**
- GUI window opens with title "CoupaDownloads - Download Manager"
- Configuration panel visible with input fields
- Start/Stop buttons functional (may show errors if core not connected)
- Status bar shows "Ready"

### Configuration Test

1. Change worker count to 6
2. Select a download directory
3. Choose a CSV file
4. Verify values are retained

### Integration Test

1. Ensure existing CLI still works: `python -m src.cli`
2. Verify no import errors when launching GUI
3. Test error handling for missing Tkinter

## Common Issues & Solutions

### Tkinter Not Available
```bash
# macOS
brew install python-tk

# Ubuntu/Debian
sudo apt-get install python3-tk
```

### Import Errors
- Ensure `src/` is in Python path
- Check file permissions
- Verify all required files exist

### UI Not Responsive
- Ensure status updates use `root.after()` for thread safety
- Check that background threads are daemon threads
- Verify queue operations don't block

## Next Steps

After completing this initial implementation:

1. **Phase 2**: Add real monitoring panel with worker status
2. **Phase 3**: Implement advanced features (batch operations, error handling)
3. **Phase 4**: Polish UI/UX and comprehensive testing

## Files Created/Modified

- `src/cli.py` - Added --ui flag support
- `src/ui/__init__.py` - Package marker
- `src/ui/main_window.py` - Main application window
- `src/ui/config_panel.py` - Configuration interface

## Validation Checklist

- [ ] GUI launches with `python -m src.cli --ui`
- [ ] Configuration panel displays all required fields
- [ ] File/directory browsers work correctly
- [ ] Start/Stop buttons update UI state appropriately
- [ ] Status bar shows messages
- [ ] CLI still works without --ui flag
- [ ] No import errors or crashes