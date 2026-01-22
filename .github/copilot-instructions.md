# CoupaDownloads Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-09-29

## Active Technologies
- Python 3.12 + Selenium WebDriver, Microsoft Edge, Poetry package managemen (001-fix-headless-mode)
- Python 3.12 + Selenium WebDriver, Microsoft Edge, Poetry package management, multiprocessing (002-fix-parallel-workers)
- File system (temporary browser profiles, download directories) (002-fix-parallel-workers)
- Python 3.12 + Selenium WebDriver >=4.0.0, Microsoft Edge browser, multiprocessing, tenacity (retry logic), structlog (structured logging) (003-parallel-profile-clone)
- Python 3.12 + Selenium WebDriver >=4.0.0, Microsoft Edge browser, multiprocessing, psutil (memory monitoring), structlog (logging) (005-persistent-worker-pool)
- File system (browser profiles, temporary downloads, configuration files) (005-persistent-worker-pool)
- Python 3.12 + pandas (CSV manipulation), multiprocessing (worker pools), structlog (structured logging), tenacity (retry logic) (007-fix-csv-handler)
- CSV files (semicolon-delimited, UTF-8 encoding) (007-fix-csv-handler)
- Python 3.12 + Tkinter (built-in), threading, queue (001-tkinter-ui-initial)
- Configuration files (JSON/INI format), no database required (001-tkinter-ui-initial)
- Python 3.12 + Tkinter (built-in), existing CLI integration (002-tkinter-ui)
- Configuration files (JSON/INI format in user home directory) (002-tkinter-ui)
- Python 3.12 + Tkinter (built-in), threading, queue, EXPERIMENTAL core system (008-enhanced-ui-feedback)
- File system (configuration files, download directories) (008-enhanced-ui-feedback)
- Python 3.12 + Tkinter (built-in), threading, queue (standard library), EXPERIMENTAL core system (008-enhanced-ui-feedback)
- N/A (UI feedback system, no persistent storage required) (008-enhanced-ui-feedback)

## Project Structure
```
src/
tests/
```

## Commands
cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style
Python 3.12: Follow standard conventions

## Recent Changes
- 008-enhanced-ui-feedback: Added Python 3.12 + Tkinter (built-in), threading, queue (standard library), EXPERIMENTAL core system
- 008-enhanced-ui-feedback: Added Python 3.12 + Tkinter (built-in), threading, queue, EXPERIMENTAL core system
- 002-tkinter-ui: Added Python 3.12 + Tkinter (built-in), existing CLI integration

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
