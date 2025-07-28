# Browser Module Documentation

## Overview

The `browser.py` file is the **browser manager** of the project. Think of it as the "driver" who controls the web browser - starting it, configuring it, and making sure it's properly cleaned up when we're done. This module handles all the complex interactions with Microsoft Edge browser.

## What This Module Does

This module is responsible for:
- Starting and stopping the Microsoft Edge browser
- Configuring browser settings (download location, security, etc.)
- Cleaning up browser processes to prevent memory leaks
- Handling graceful shutdown when the user interrupts the script
- Managing browser profiles for saved logins

## The BrowserManager Class

The `BrowserManager` class follows the **Single Responsibility Principle** - its only job is to manage the browser lifecycle.

### Key Components Explained

#### 1. **Initialization (`__init__`)**
```python
def __init__(self):
    self.driver: Optional[webdriver.Edge] = None
    self._setup_signal_handlers()
```

**In Plain English:** When we create a browser manager:
- We start with no browser open yet (`driver = None`)
- We set up "emergency stop" buttons (signal handlers) so we can clean up if something goes wrong

#### 2. **Signal Handlers (`_setup_signal_handlers`)**
```python
def _setup_signal_handlers(self) -> None:
    signal.signal(signal.SIGINT, self._signal_handler)
    signal.signal(signal.SIGTERM, self._signal_handler)
```

**In Plain English:** This sets up "panic buttons" that respond when:
- You press Ctrl+C (SIGINT)
- The system tries to shut down the program (SIGTERM)
- It ensures the browser is properly closed even if something goes wrong

#### 3. **Browser Process Cleanup (`cleanup_browser_processes`)**
```python
def cleanup_browser_processes(self) -> None:
    if sys.platform == "darwin":  # macOS
        subprocess.run(["pkill", "-f", "Microsoft Edge"], capture_output=True)
        subprocess.run(["pkill", "-f", "msedge"], capture_output=True)
    elif sys.platform == "win32":  # Windows
        subprocess.run(["taskkill", "/f", "/im", "msedge.exe"], capture_output=True)
    else:  # Linux
        subprocess.run(["pkill", "-f", "microsoft-edge"], capture_output=True)
```

**In Plain English:** This is like a "cleanup crew" that:
- Finds any leftover Edge browser processes
- Forces them to close completely
- Works on different operating systems (Windows, Mac, Linux)
- Prevents browser instances from staying open in the background

#### 4. **Browser Options Creation (`_create_browser_options`)**
```python
def _create_browser_options(self, headless: bool = False) -> EdgeOptions:
    options = EdgeOptions()
    options.add_argument("--disable-extensions")
    options.add_argument("--start-maximized")
    options.add_experimental_option("prefs", Config.BROWSER_OPTIONS)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    if headless:
        options.add_argument("--headless=new")
```

**In Plain English:** This configures how the browser should behave:
- `--disable-extensions`: Turn off browser extensions that might interfere
- `--start-maximized`: Open the browser window at full size
- `--headless=new`: Run the browser in the background (no visible window)
- `excludeSwitches`: Hide automation indicators
- `prefs`: Set download preferences (where to save files, etc.)

#### 5. **Driver Initialization (`initialize_driver`)**
```python
def initialize_driver(self, headless: bool = False) -> webdriver.Edge:
    if not Config.DRIVER_PATH or not os.path.exists(Config.DRIVER_PATH):
        raise FileNotFoundError(f"WebDriver not found at {Config.DRIVER_PATH}")
    
    try:
        options = self._create_browser_options(headless=headless)
        service = EdgeService(executable_path=Config.DRIVER_PATH)
        self.driver = webdriver.Edge(service=service, options=options)
        return self.driver
    except Exception as e:
        print(f"Driver initialization failed: {e}")
        raise
```

**In Plain English:** This is like "starting the engine":
- Check if the browser driver exists on your computer
- Create the browser configuration
- Start the actual browser
- Return the browser object so other parts can control it

#### 6. **Start Method (`start`)**
```python
def start(self, headless: bool = False) -> webdriver.Edge:
    self.check_and_kill_existing_edge_processes()
    return self.initialize_driver(headless=headless)
```

**In Plain English:** This is the main "start button":
- First, clean up any existing browser processes
- Then start a fresh browser
- Return the browser object ready to use

#### 7. **Cleanup Method (`cleanup`)**
```python
def cleanup(self) -> None:
    self.cleanup_browser_processes()
    
    if self.driver:
        try:
            self.driver.quit()
            print("✅ Browser closed successfully.")
        except Exception as e:
            print(f"⚠️ Warning: Could not close browser cleanly: {e}")
```

**In Plain English:** This is the "shutdown procedure":
- Kill any browser processes
- Close the browser properly
- Show success or warning messages

## Key Libraries Used

### 1. **Selenium** (`from selenium import webdriver`)
- **What it is:** A library for controlling web browsers programmatically
- **Why we use it:** To automate browser actions like clicking, typing, navigating
- **Think of it as:** A remote control for web browsers

### 2. **subprocess** (`import subprocess`)
- **What it is:** Python's way of running system commands
- **Why we use it:** To kill browser processes using system commands
- **Think of it as:** A way to send commands to your operating system

### 3. **signal** (`import signal`)
- **What it is:** Python's signal handling system
- **Why we use it:** To respond to system signals like Ctrl+C
- **Think of it as:** An emergency stop button system

### 4. **os** (`import os`)
- **What it is:** Python's operating system interface
- **Why we use it:** To check if files exist and work with file paths
- **Think of it as:** A tool to interact with your computer's file system

## Cross-Platform Support

The module works on different operating systems:

### Windows
```python
subprocess.run(["taskkill", "/f", "/im", "msedge.exe"], capture_output=True)
```

### macOS
```python
subprocess.run(["pkill", "-f", "Microsoft Edge"], capture_output=True)
subprocess.run(["pkill", "-f", "msedge"], capture_output=True)
```

### Linux
```python
subprocess.run(["pkill", "-f", "microsoft-edge"], capture_output=True)
subprocess.run(["pkill", "-f", "msedge"], capture_output=True)
```

## Headless Mode

The browser can run in two modes:

### Visible Mode (Default)
- Browser window is visible
- You can see what the automation is doing
- Useful for debugging and understanding the process

### Headless Mode
- Browser runs in the background
- No visible window
- Faster and uses fewer resources
- Good for production use

## Error Handling

The module includes comprehensive error handling:

1. **File Not Found**: If the browser driver is missing
2. **Process Cleanup**: If browser processes can't be killed
3. **Driver Initialization**: If the browser fails to start
4. **Graceful Shutdown**: Always tries to clean up properly

## Best Practices Used

1. **Single Responsibility**: This class only handles browser management
2. **Cross-Platform**: Works on Windows, Mac, and Linux
3. **Error Handling**: Comprehensive error handling and cleanup
4. **Signal Handling**: Responds to system signals for graceful shutdown
5. **Resource Management**: Ensures browser processes are properly cleaned up
6. **Configuration**: Uses external configuration for flexibility

## Benefits of This Approach

1. **Reliability**: Browser processes are always cleaned up
2. **Cross-Platform**: Works on different operating systems
3. **Flexibility**: Supports both visible and headless modes
4. **Safety**: Graceful shutdown even if something goes wrong
5. **Maintainability**: Clear separation of browser management concerns
