# Tkinter UI Plan for CoupaDownloads

## Overview
This document outlines the plan for implementing an optional Tkinter-based graphical user interface (GUI) for the CoupaDownloads application. The goal is to provide a user-friendly interface for configuring, monitoring, and controlling download operations while minimizing changes to the existing codebase.

## Objectives
- **Minimal Impact**: Integrate the UI as an optional component that doesn't alter the core download logic
- **User-Friendly**: Provide intuitive controls for common operations (start/stop downloads, configure workers, view logs)
- **Non-Blocking**: Allow the application to run with or without the UI
- **Maintainable**: Keep UI code separate from business logic

## Architecture

### Integration Strategy
- Create a new `ui/` directory under `src/` for UI-related code
- Add a command-line flag (e.g., `--ui`) to launch the application with GUI
- Use multiprocessing to run the UI in a separate process from the download workers
- Communicate between UI and core logic via queues or shared state
- Implement real-time updates using threading in the UI process to poll worker status
- Use shared memory or message passing for worker queue information

### File Structure
```
src/
├── ui/
│   ├── __init__.py
│   ├── main_window.py      # Main application window
│   ├── config_panel.py     # Configuration settings panel
│   ├── monitor_panel.py    # Real-time monitoring dashboard
│   ├── log_viewer.py       # Log display and filtering
│   └── dialogs.py          # Dialog boxes for file selection, etc.
├── core/
│   └── ... (existing code)
└── cli.py                  # Modified to support --ui flag
```

## UI Components

### Main Window
- **Title**: CoupaDownloads - Download Manager
- **Menu Bar**:
  - File: Open config, Save config, Exit
  - View: Show logs, Show monitor
  - Help: About, Documentation
- **Toolbar**: Quick access to start/stop operations
- **Status Bar**: Current status, progress indicators

### Configuration Panel
- **Worker Settings**:
  - Number of parallel workers (1-10)
  - Browser profile selection
  - Download directory
- **CSV Settings**:
  - Input file selection
  - Output directory
  - Encoding options (UTF-8, ISO-8859-1)
- **Retry Settings**:
  - Max retries per download
  - Delay between retries

### Monitor Panel
- **Real-time Dashboard**:
  - Active workers count
  - Completed downloads
  - Failed downloads
  - Current progress bars per worker
- **Worker Status Table**:
  - Worker ID
  - Current task
  - Status (idle, downloading, processing)
  - Progress percentage
- **Worker Details Grid** (Side-by-Side View):
  - Each worker displayed in a separate column/panel
  - **Status Indicator**: Visual status (idle, busy, error) with color coding
  - **Current Job**: Details of the job currently being processed
  - **Job Queue**: Scrollable list showing:
    - Pending jobs (waiting in queue)
    - In-progress job (current)
    - Completed jobs (last N jobs with timestamps)
    - Failed jobs (with error summaries)
  - **Performance Metrics**: Download speed, success rate, uptime
  - **Controls**: Individual worker pause/resume, cancel current job

### Log Viewer
- **Log Display**:
  - Real-time log streaming
  - Filter by log level (DEBUG, INFO, WARNING, ERROR)
  - Search functionality
  - Auto-scroll to bottom
- **Export Options**:
  - Save logs to file
  - Clear log display

## Functionality

### Core Operations
1. **Load Configuration**: Import settings from existing config files
2. **Start Downloads**: Launch worker pool with specified parameters
3. **Monitor Progress**: Display real-time status of all workers
4. **Stop Downloads**: Gracefully terminate all operations
5. **View Results**: Display summary of completed downloads and errors
6. **Worker Queue Monitoring**: Real-time side-by-side view of each worker's status and job queue

### Advanced Features
- **Profile Management**: Create, clone, and manage browser profiles
- **Batch Operations**: Queue multiple download jobs
- **Error Handling**: Display detailed error messages with retry options
- **Performance Metrics**: Show download speeds, success rates
- **Individual Worker Control**: Pause, resume, or cancel jobs for specific workers

## Dependencies
- **Tkinter**: Built-in Python GUI library (no additional installation needed)
- **ttk**: Enhanced Tkinter widgets for better appearance
- **threading**: For UI responsiveness during long operations
- **queue**: For inter-process communication

## Implementation Phases

### Phase 1: Basic UI Framework
- Create main window with basic layout
- Implement configuration panel
- Add start/stop functionality
- Integrate with existing CLI entry point

### Phase 2: Monitoring and Logging
- Add real-time monitoring panel
- Implement log viewer
- Add progress indicators
- Connect to existing logging system
- Implement side-by-side worker queue visualization with real-time updates

### Phase 3: Advanced Features
- Profile management interface
- Batch job queuing
- Error handling dialogs
- Performance metrics display

### Phase 4: Polish and Testing
- UI/UX improvements
- Comprehensive testing
- Documentation updates
- Performance optimization

## Initial Implementation Details (Phase 1)

### File Structure Setup
Create the following directory structure under `src/`:
```
src/
├── ui/
│   ├── __init__.py
│   ├── main_window.py
│   ├── config_panel.py
│   └── __pycache__/ (auto-generated)
├── cli.py (modified)
└── ... (existing files)
```

### CLI Integration
Modify `cli.py` to support the `--ui` flag:

```python
import argparse
from ui.main_window import launch_ui

def main():
    parser = argparse.ArgumentParser(description='CoupaDownloads')
    parser.add_argument('--ui', action='store_true', help='Launch with GUI')
    args = parser.parse_args()
    
    if args.ui:
        launch_ui()
    else:
        # Existing CLI logic
        run_downloads()
```

### Main Window Implementation (`ui/main_window.py`)
```python
import tkinter as tk
from tkinter import ttk, messagebox
from config_panel import ConfigPanel
import threading
import queue

class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("CoupaDownloads - Download Manager")
        self.root.geometry("800x600")
        
        # Communication queue with core
        self.status_queue = queue.Queue()
        
        self.setup_menu()
        self.setup_toolbar()
        self.setup_main_frame()
        self.setup_status_bar()
        
        # Start status update thread
        self.update_thread = threading.Thread(target=self.update_status, daemon=True)
        self.update_thread.start()
    
    def setup_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open Config", command=self.load_config)
        file_menu.add_command(label="Save Config", command=self.save_config)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Show Monitor", command=self.show_monitor)
        view_menu.add_command(label="Show Logs", command=self.show_logs)
        menubar.add_cascade(label="View", menu=view_menu)
    
    def setup_toolbar(self):
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        
        self.start_btn = ttk.Button(toolbar, text="Start", command=self.start_downloads)
        self.start_btn.pack(side=tk.LEFT, padx=2, pady=2)
        
        self.stop_btn = ttk.Button(toolbar, text="Stop", command=self.stop_downloads, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=2, pady=2)
    
    def setup_main_frame(self):
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Configuration tab
        config_frame = ttk.Frame(self.notebook)
        self.notebook.add(config_frame, text="Configuration")
        self.config_panel = ConfigPanel(config_frame)
        
        # Placeholder for Monitor tab (Phase 2)
        monitor_frame = ttk.Frame(self.notebook)
        self.notebook.add(monitor_frame, text="Monitor")
        ttk.Label(monitor_frame, text="Monitor panel - To be implemented in Phase 2").pack(pady=20)
    
    def setup_status_bar(self):
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def start_downloads(self):
        # Get config from panel
        config = self.config_panel.get_config()
        
        # Launch downloads in separate thread/process
        self.download_thread = threading.Thread(target=self.run_downloads, args=(config,), daemon=True)
        self.download_thread.start()
        
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_var.set("Running downloads...")
    
    def stop_downloads(self):
        # Signal stop
        self.status_var.set("Stopping...")
        # Implementation for stopping downloads
    
    def update_status(self):
        # Poll for status updates
        while True:
            try:
                status = self.status_queue.get(timeout=1)
                self.status_var.set(status)
            except queue.Empty:
                continue
    
    def load_config(self):
        # Load config file
        pass
    
    def save_config(self):
        # Save config file
        pass
    
    def show_monitor(self):
        self.notebook.select(1)  # Monitor tab
    
    def show_logs(self):
        # Show log window
        pass

def launch_ui():
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()
```

### Configuration Panel (`ui/config_panel.py`)
```python
import tkinter as tk
from tkinter import ttk, filedialog

class ConfigPanel:
    def __init__(self, parent):
        self.parent = parent
        self.setup_widgets()
    
    def setup_widgets(self):
        # Worker settings
        worker_frame = ttk.LabelFrame(self.parent, text="Worker Settings")
        worker_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(worker_frame, text="Number of workers:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.workers_var = tk.IntVar(value=4)
        ttk.Spinbox(worker_frame, from_=1, to=10, textvariable=self.workers_var).grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(worker_frame, text="Download directory:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.download_dir_var = tk.StringVar(value="./downloads")
        ttk.Entry(worker_frame, textvariable=self.download_dir_var).grid(row=1, column=1, padx=5, pady=2)
        ttk.Button(worker_frame, text="Browse", command=self.browse_download_dir).grid(row=1, column=2, padx=5, pady=2)
        
        # CSV settings
        csv_frame = ttk.LabelFrame(self.parent, text="CSV Settings")
        csv_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(csv_frame, text="Input CSV file:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.input_csv_var = tk.StringVar()
        ttk.Entry(csv_frame, textvariable=self.input_csv_var).grid(row=0, column=1, padx=5, pady=2)
        ttk.Button(csv_frame, text="Browse", command=self.browse_input_csv).grid(row=0, column=2, padx=5, pady=2)
        
        # Retry settings
        retry_frame = ttk.LabelFrame(self.parent, text="Retry Settings")
        retry_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(retry_frame, text="Max retries:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.max_retries_var = tk.IntVar(value=3)
        ttk.Spinbox(retry_frame, from_=0, to=10, textvariable=self.max_retries_var).grid(row=0, column=1, padx=5, pady=2)
    
    def browse_download_dir(self):
        dirname = filedialog.askdirectory()
        if dirname:
            self.download_dir_var.set(dirname)
    
    def browse_input_csv(self):
        filename = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if filename:
            self.input_csv_var.set(filename)
    
    def get_config(self):
        return {
            'workers': self.workers_var.get(),
            'download_dir': self.download_dir_var.get(),
            'input_csv': self.input_csv_var.get(),
            'max_retries': self.max_retries_var.get()
        }
```

### Dependencies Installation
Ensure the following are available (most are built-in):
- `tkinter` (usually included with Python)
- `threading` (built-in)
- `queue` (built-in)

For macOS/Linux, tkinter might need separate installation:
```bash
# macOS
brew install python-tk

# Ubuntu/Debian
sudo apt-get install python3-tk
```

### Testing the Initial UI
1. Create the files as shown above
2. Run: `python -m src.cli --ui`
3. Verify the window opens with configuration panel
4. Test basic interactions (changing values, browsing files)
5. Check that start/stop buttons work (even if downloads don't run yet)

### Integration Points
- The `run_downloads()` function in `main_window.py` should call the existing download logic
- Use the config dictionary to pass parameters to the core download system
- Status updates should be sent via the `status_queue` for real-time UI updates

## Benefits
- **Accessibility**: Makes the application accessible to non-technical users
- **Monitoring**: Provides real-time visibility into download operations
- **Configuration**: Simplifies setup and parameter tuning
- **Debugging**: Easier troubleshooting with visual log viewer

## Risks and Mitigations
- **Performance Impact**: UI runs in separate process to avoid blocking downloads
- **Complexity**: Keep UI code separate and well-documented
- **Maintenance**: Regular testing to ensure UI doesn't break with core changes
- **Dependencies**: Use only built-in libraries to avoid additional requirements

## Future Enhancements
- Dark mode support
- Customizable themes
- Export reports to PDF/CSV
- Integration with system tray
- Keyboard shortcuts
- Multi-language support
