# CoupaDownloads System Overview Documentation

## Project Overview

The CoupaDownloads system is an automated web scraping and file download tool designed to extract attachments from Purchase Order (PO) pages in the Coupa procurement system. The system follows a modular architecture with clear separation of concerns, making it maintainable, testable, and extensible.

## System Architecture

The system is organized into several key components, each with a specific responsibility:

### 1. Main Orchestrator (`src/main.py`)
The main orchestrator class manages the entire workflow and coordinates between all other components.

#### CoupaDownloader Class Structure:
```
    # This is the main orchestrator class that follows the Single Responsibility Principle
    # Initialize the downloader with browser and managers
    # Create a browser manager instance for handling web browser operations
    # Initialize driver variable to store the web browser instance
    # Create download manager variable for handling file downloads
    # Create login manager variable for handling authentication
    
    # Setup method to prepare the downloader with browser and managers
    # Ensure the download folder exists before starting operations
    # Start the web browser with headless mode configuration
    # Initialize the download manager with the browser driver
    # Initialize the login manager with the browser driver
    
    # Process PO numbers from CSV file
    # Get the CSV file path from the configuration
    # Read all PO numbers from the CSV file
    # Process and validate the PO numbers
    # Limit the number of POs processed if configured
    # Print a message if limiting POs for this run
    # Check if there are any valid entries
    # Print an error message if no valid PO numbers
    # Return the list of valid PO entries
    # Print the list of POs being processed
    
    # Handle login before processing any POs to prevent race conditions
    # Print a message about checking login status
    # Try to navigate to the Coupa homepage first
    # Print a message about navigating to the homepage
    # Check if the driver exists
    # Navigate to the Coupa homepage URL
    # Raise an error if the browser driver is not initialized
    # Check if already logged in
    # Print success message if already logged in
    # Return True to indicate successful login
    # Print message that login is required
    # Wait for login completion
    # Ensure the user is logged in
    # Print success message when login is completed
    # Return True to indicate successful login
    # Raise an error if login manager is not initialized
    # Catch any login errors
    # Print error message about login failure
    # Print helpful message about ensuring login
    # Return False to indicate login failure
    
    # Download attachments for all valid PO numbers after login is confirmed
    # Check if managers are initialized
    # Raise an error if managers are not initialized
    # Handle login first before processing any POs
    # Return early if login fails
    # Print message about processing POs after successful login
    # Loop through each PO entry
    # Try to process each PO
    # Print message about processing current PO
    # Check if browser session is still valid
    # Print warning if browser session is lost
    # Attempt to recover browser session
    # Print error if cannot recover browser session
    # Break the loop if recovery fails
    # Process the PO in the current tab
    # Print success message for completed PO
    # Catch any download errors
    # Print error message for failed PO
    # Check if it's a browser session error
    # Print message about browser session error
    # Attempt to recover browser session
    # Print error if cannot recover browser session
    # Break the loop if recovery fails
    # Continue with next PO
    # Navigate back to home page after processing all POs
    # Print message about navigating back to homepage
    # Try to navigate back to homepage
    # Check if driver exists and session is valid
    # Navigate to the Coupa homepage
    # Print success message
    # Catch any navigation errors
    # Print warning about navigation failure
    
    # Check if the browser session is still valid
    # Check if driver exists
    # Return False if no driver
    # Try to get the current URL to test if session is valid
    # Return True if successful
    # Catch any exceptions
    # Return False if session is invalid
    
    # Attempt to recover the browser session by restarting the browser
    # Try to restart browser session
    # Print message about restarting browser session
    # Clean up old session
    # Check if browser manager exists
    # Force cleanup of old browser processes
    # Restart browser
    # Start new browser instance
    # Reinitialize managers with new driver
    # Create new download manager
    # Create new login manager
    # Try to handle login again
    # Print success message for recovery
    # Return True to indicate successful recovery
    # Print error message for login failure
    # Return False to indicate recovery failure
    # Catch any recovery errors
    # Print error message about recovery failure
    # Return False to indicate recovery failure
    
    # Main execution method
    # Try to start the main execution
    # Print message about starting Coupa Downloader
    # Create backup of CSV before processing
    # Call the backup method
    # Setup the downloader
    # Process PO numbers
    # Check if there are valid entries
    # Print message if no POs to process
    # Return early if no POs
    # Download attachments for all POs
    # Generate final summary report
    # Print completion message
    # Call the summary report method
    # Catch keyboard interrupt
    # Print message about user interruption
    # Catch any unexpected errors
    # Import configuration
    # Print error message
    # Check if Edge crash stacktrace should be shown
    # Import system modules
    # Import traceback module
    # Get exception information
    # Format the exception traceback
    # Filter out Edge driver crash lines
    # Print filtered traceback
    # Finally block for cleanup
    # Import configuration
    # Print debug information about browser closing
    # Print debug information about keeping browser open
    # Check if browser should be closed after execution
    # Clean up browser
    # Print message about browser closure
    # Check if browser should be kept open
    # Ensure browser is on homepage before leaving open
    # Try to navigate to homepage
    # Check if driver exists and session is valid
    # Navigate to Coupa homepage
    # Print message about parking browser
    # Catch any navigation errors
    # Print warning about navigation failure
    # Keep browser open
    # Clean up browser
    
    # Main entry point
    # Create a new CoupaDownloader instance
    # Run the downloader
    
    # Check if this is the main module
    # Call the main function
```

### 2. Configuration Management (`src/core/config.py`)
The configuration module centralizes all system settings, environment variables, and constants.

#### Config Class Structure:
```
    # Configuration class following Single Responsibility Principle
    
    # Base URLs and paths
    # Define the base URL template for Coupa PO pages
    # Set the default download folder path
    # Set the path to the Edge WebDriver executable
    
    # File settings
    # Define list of allowed file extensions for download
    
    # Environment variables with defaults
    # Get page delay from environment or use default
    # Get Edge user profile directory from environment or use default
    # Get Edge profile name from environment or use default
    # Get login timeout from environment or use default
    # Get headless mode setting from environment or use default
    # Set keep browser open flag
    # Set whether to close browser after execution
    # Get maximum POs to process from environment or use default
    
    # Browser settings
    # Define browser preferences for downloads
    # Set download directory
    # Disable download prompts
    # Enable directory upgrade
    # Disable safe browsing
    
    # CSS Selectors
    # Define selector for finding attachment elements
    # Define multiple CSS selectors for supplier name extraction
    # Try semantic selectors first
    # Try structural selectors
    # Define generic fallbacks
    # Define XPath as final fallback for supplier name
    
    # Timeouts
    # Set page load timeout
    # Set attachment wait timeout
    # Set download wait timeout
    # Toggle Edge WebDriver crash stacktrace reporting
    
    # Class method to ensure download folder exists
    # Check if download folder exists
    # Create the folder if it doesn't exist
    
    # Class method to get CSV file path
    # Navigate from current directory to project root
    # Return the path to the input CSV file
```

### 3. Browser Management (`src/core/browser.py`)
The browser manager handles WebDriver setup, cleanup, and process management.

#### BrowserManager Class Structure:
```
    # Manages browser lifecycle following Single Responsibility Principle
    
    # Initialize browser manager
    # Set driver variable to None initially
    # Setup signal handlers for graceful shutdown
    
    # Setup signal handlers for graceful shutdown
    # Register signal handler for interrupt signals
    # Register signal handler for termination signals
    
    # Handle interrupt signals for graceful shutdown
    # Print message about received signal
    # Clean up browser processes
    # Exit the program
    
    # Kill all Edge browser processes to ensure clean shutdown
    # Try to kill Edge processes
    # Check platform type
    # Kill Microsoft Edge processes on macOS
    # Kill msedge processes on macOS
    # Kill msedge processes on Windows
    # Kill microsoft-edge processes on Linux
    # Kill msedge processes on Linux
    # Print success message
    # Catch any cleanup errors
    # Print warning about cleanup failure
    
    # Check for existing Edge processes and kill them before starting
    # Try to check for existing processes
    # Check platform type
    # Check for Edge processes on macOS
    # If processes found, clean them up
    # Wait for processes to close
    # Check for Edge processes on Windows
    # If processes found, clean them up
    # Wait for processes to close
    # Check for Edge processes on Linux
    # If processes found, clean them up
    # Wait for processes to close
    # Catch any checking errors
    # Print warning about checking failure
    
    # Create and configure browser options
    # Create new Edge options object
    # Set profile options first
    # Check if profile directory is configured
    # Add user data directory argument
    # Add profile directory argument
    # Ensure browser remains open after script ends
    # Add detach experimental option
    # Add other browser options
    # Add start maximized argument
    # Use custom download directory if provided
    # Set browser preferences
    # Set download directory
    # Disable download prompts
    # Enable directory upgrade
    # Disable safe browsing
    # Add experimental options
    # Exclude automation switches
    # Disable automation extension
    # Add headless argument if requested
    # Print debug information about options
    # Return the configured options
    
    # Initialize the WebDriver with proper error handling
    # Check if local driver exists
    # Raise error if driver not found
    # Try to create driver
    # Create browser options
    # Create Edge service
    # Create Edge driver
    # Print success message
    # Return the driver
    # Catch any initialization errors
    # Check if it's a profile directory error
    # Print warning about profile directory
    # Retry without profile options
    # Create options without profile
    # Create Edge service
    # Create Edge driver
    # Print success message
    # Return the driver
    # Print error message
    # Re-raise the error
    
    # Create browser options without profile selection
    # Create new Edge options object
    # Ensure browser remains open after script ends
    # Add detach experimental option
    # Add other browser options
    # Add start maximized argument
    # Use custom download directory if provided
    # Set browser preferences
    # Set download directory
    # Disable download prompts
    # Enable directory upgrade
    # Disable safe browsing
    # Add experimental options
    # Exclude automation switches
    # Disable automation extension
    # Add headless argument if requested
    # Return the configured options
    
    # Start the browser with cleanup of existing processes
    # Comment out process cleanup to avoid interfering with profile sessions
    # Return the initialized driver
    
    # Clean up browser processes and close driver
    # Clean up browser processes
    # Check if driver exists
    # Try to quit the driver
    # Print success message
    # Catch any cleanup errors
    # Print warning about cleanup failure
    # Print message if no driver to close
    
    # Create a new tab and return its handle
    # Check if driver is initialized
    # Raise error if driver not initialized
    # Store current window handle
    # Create new tab using JavaScript
    # Switch to the new tab
    # Find the new handle
    # Loop through window handles
    # Check if handle is different from original
    # Set new handle
    # Break the loop
    # Check if new handle was found
    # Switch to new window
    # Print success message
    # Return the new handle
    # Raise error if tab creation failed
    
    # Close the current tab and switch back to the main tab
    # Check if driver is initialized
    # Raise error if driver not initialized
    # Try to close current tab
    # Get current window handle
    # Get all window handles
    # Check if only one tab remains
    # Print warning about single tab
    # Return early
    # Close current tab
    # Print success message
    # Switch to the first remaining tab
    # Get remaining handles
    # Check if there are remaining handles
    # Switch to first remaining handle
    # Print success message
    # Print warning if no remaining tabs
    # Catch any tab closing errors
    # Print error message
    # Try to switch to any available tab
    # Check if there are window handles
    # Switch to first available handle
    # Print recovery message
    # Catch any recovery errors
    # Print error about recovery failure
    
    # Switch to the main tab (first tab)
    # Check if driver is initialized
    # Raise error if driver not initialized
    # Check if there are window handles
    # Get main handle
    # Switch to main window
    # Print success message
    
    # Switch to a specific tab by handle
    # Check if driver is initialized
    # Raise error if driver not initialized
    # Check if tab handle exists
    # Switch to the specified window
    # Print success message
    # Raise error if tab handle not found
    
    # Keep the browser open instead of closing it
    # Check if driver exists
    # Print message about keeping browser open
    # Print helpful message about manual closure
    # Don't call cleanup - let browser stay open
    # Print message if no browser instance
    
    # Force cleanup and close browser
    # Call the cleanup method
    
    # Check if the browser is still responsive
    # Check if driver exists
    # Return False if no driver
    # Try to get current URL to test responsiveness
    # Return True if successful
    # Catch any exceptions
    # Return False if not responsive
    
    # Ensure browser is responsive, try to recover if not
    # Check if browser is responsive
    # Print warning if not responsive
    # Try to recover
    # Try to switch to any available window
    # Check if driver and window handles exist
    # Switch to first available window
    # Print success message
    # Return True
    # Print error if no windows available
    # Return False
    # Catch any recovery errors
    # Print error message
    # Return False
    # Return True if responsive
```

### 4. Download Management (`src/core/downloader.py`)
The download manager handles file operations, attachment downloading, and renaming.

#### FileManager Class Structure:
```
    # Manages file operations following Single Responsibility Principle
    
    # Get list of supported file extensions
    # Return the list of allowed extensions from configuration
    
    # Check if file has supported extension
    # Check if filename ends with any supported extension
    # Return True if supported, False otherwise
    
    # Extract filename from aria-label attribute
    # Check if aria-label exists
    # Return default filename if no aria-label
    # Search for filename pattern in aria-label
    # Return extracted filename or default
    
    # Rename only the newly downloaded files with PO prefix
    # Try to rename files
    # Loop through each filename
    # Clean the filename to remove any existing PO prefix
    # Check if filename starts with PO
    # Remove any existing PO prefix from filename
    # Split on first underscore
    # Check if parts exist and first part starts with PO
    # Take everything after the first PO_
    # Remove first occurrence of PO
    # Create proper filename with PO prefix
    # Extract clean PO number
    # Create new filename with PO prefix
    # Create old and new file paths
    # Try to rename the file
    # Print success message
    # Catch any rename errors
    # Print error message
    # Catch any general errors
    # Print error message
    
    # Clean up existing files with double PO prefixes
    # Try to clean up files
    # Loop through files in download folder
    # Check if filename starts with POPO
    # Extract the part after the second PO
    # Remove the first "PO"
    # Create old and new file paths
    # Try to rename the file
    # Print success message
    # Catch any rename errors
    # Print error message
    # Check for other double PO patterns
    # Split filename by underscores
    # Check if second part starts with PO
    # Remove the second PO prefix
    # Create old and new file paths
    # Try to rename the file
    # Print success message
    # Catch any rename errors
    # Print error message
    # Catch any general errors
    # Print error message
    
    # Check for and fix any files that don't have PO prefixes
    # Try to check for unnamed files
    # Create list for unnamed files
    # Loop through files in download folder
    # Check if file exists and doesn't start with PO
    # Add to unnamed files list
    # Check if unnamed files were found
    # Print warning with count and list
    # Print helpful message about fixing
    # Catch any checking errors
    # Print error message
```

#### DownloadManager Class Structure:
```
    # Manages download operations following Single Responsibility Principle
    
    # Initialize download manager
    # Store the browser driver
    # Create file manager instance
    
    # Wait for all .crdownload files to disappear
    # Record start time
    # Loop while within timeout period
    # Check if any .crdownload files exist
    # Return if no .crdownload files
    # Wait one second
    # Raise timeout exception if downloads not completed
    
    # Wait for attachments to load on the page
    # Try to wait for attachments
    # Wait for element to be present
    # Use attachment selector from configuration
    # Catch timeout exception
    # Raise timeout exception with message
    
    # Find all attachment elements on the page
    # Find elements using CSS selector
    # Print count of attachments found
    # Debug: Print details of each attachment
    # Loop through attachments
    # Try to get attachment attributes
    # Get aria-label attribute
    # Get role attribute
    # Get class attribute
    # Print attachment details
    # Catch any attribute errors
    # Print error message
    # Return the list of attachments
    
    # Download a single attachment
    # Try to download attachment
    # Get filename from aria-label
    # Extract filename using file manager
    # Print processing message
    # Skip unsupported file types
    # Check if file is supported
    # Print skip message
    # Return early
    # Check if element is clickable
    # Check if element is enabled
    # Print warning if not enabled
    # Return early
    # Check if element is displayed
    # Print warning if not displayed
    # Return early
    # Try to click the attachment
    # Scroll element into view first
    # Wait briefly after scrolling
    # Try regular click first
    # Print success message
    # Catch click errors
    # Print fallback message
    # Try JavaScript click
    # Print success message
    # Wait briefly between downloads
    # Catch any download errors
    # Print error message
    # Print aria-label information
    
    # Download all attachments for a specific PO and update CSV status
    # Import required modules
    # Print processing message
    # Try to process PO
    # Navigate to PO page
    # Create PO URL
    # Print navigation message
    # Navigate to URL
    # Check if page exists
    # Check for page not found indicators
    # Print error message
    # Update CSV status
    # Return early
    # Wait for page to load
    # Wait for body element to be present
    # Check for login redirect
    # Check if redirected to login page
    # Print login required message
    # Update CSV status
    # Raise exception for retry mechanism
    # Find attachments
    # Find attachment elements
    # Count attachments found
    # Check if no attachments found
    # Print no attachments message
    # Update CSV status
    # Return early
    # Print download message
    # Extract supplier name for folder organization
    # Track downloads before starting
    # Count existing files
    # Use temporary directory approach for clean downloads
    # Count files after download
    # Calculate downloaded count
    # Update CSV status based on results
    # Check if all attachments downloaded
    # Set status to completed
    # Print success message
    # Check if some attachments downloaded
    # Set status to partial
    # Print partial success message
    # Set status to failed
    # Print failure message
    # Update CSV with results
    # Catch timeout exception
    # Print timeout message
    # Update CSV status
    # Catch any other exceptions
    # Check if login-related exception
    # Re-raise for retry mechanism
    # Print error message
    # Update CSV status
    
    # Extract supplier name from the PO page using cascading selector approach
    # Import required modules
    # Try CSS selectors first
    # Loop through CSS selectors
    # Try current selector
    # Wait for element to be present
    # Get supplier name text
    # Check if supplier name is valid
    # Clean the folder name
    # Print success message
    # Return cleaned name
    # Print warning about short text
    # Catch any selector errors
    # Print error message
    # Continue to next selector
    # Fallback to XPath
    # Try XPath extraction
    # Print fallback message
    # Wait for element to be present
    # Get supplier name text
    # Check if supplier name exists
    # Clean the folder name
    # Print success message
    # Return cleaned name
    # Print warning about empty text
    # Catch any XPath errors
    # Print error message
    # Final fallback
    # Print fallback message
    # Return default supplier name
    
    # Clean a name to be safe for use as a folder name
    # Import regular expression module
    # Replace spaces and invalid characters with underscores
    # Remove multiple underscores and trim
    # Limit length to avoid filesystem issues
    # Check if name is too long
    # Truncate and remove trailing underscores
    # Ensure it's not empty
    # Check if cleaned name is empty
    # Set default name
    # Return cleaned name
    
    # Create and return the path to the supplier-specific folder
    # Create supplier folder path
    # Try to create folder
    # Check if folder doesn't exist
    # Create the folder
    # Print success message
    # Print existing folder message
    # Return folder path
    # Catch any creation errors
    # Print warning message
    # Print fallback message
    # Return main download folder
    
    # Download attachments using only the temporary directory method
    # Print method message
    # Create supplier folder
    # Try temporary directory method
    
    # Fallback to temporary directory method
    # Import required modules
    # Create temporary directory for this PO
    # Print temporary directory message
    # Use CDP to change download directory
    # Try to change download directory
    # Execute CDP command
    # Print success message
    # Catch any CDP errors
    # Print warning message
    # Fall back to file tracking method
    # Try to download attachments
    # Loop through attachments
    # Download each attachment
    # Wait for downloads to complete
    # Move files with proper names
    # Restore original download directory
    # Try to restore directory
    # Execute CDP command
    # Print success message
    # Catch any restore errors
    # Print warning message
    
    # Download a single attachment with simplified logic
    # Try to download attachment
    # Get filename from aria-label
    # Extract filename using file manager
    # Print processing message
    # Skip unsupported file types
    # Check if file is supported
    # Print skip message
    # Return early
    # Check if element is clickable
    # Check if element is enabled and displayed
    # Print warning if not clickable
    # Return early
    # Try to click the attachment
    # Scroll element into view
    # Wait briefly
    # Click the element
    # Print success message
    # Catch click errors
    # Print fallback message
    # Try JavaScript click
    # Print success message
    # Wait briefly between downloads
    # Catch any download errors
    # Print error message
    
    # Move files from temp directory to final destination with proper PO prefixes
    # Import required module
    # Try to move files
    # Get list of files in temp directory
    # Check if no files downloaded
    # Print warning message
    # Return early
    # Print moving message
    # Loop through files
    # Clean the filename to remove any existing PO prefix
    # Check if filename starts with PO
    # Remove any existing PO prefix from filename
    # Split on first underscore
    # Check if parts exist and first part starts with PO
    # Take everything after the first PO_
    # Remove first occurrence of PO
    # Create proper filename with PO prefix
    # Extract clean PO number
    # Create proper filename
    # Create source and destination paths
    # Handle duplicate filenames
    # Initialize counter
    # Check if destination file exists
    # Split filename and extension
    # Create new filename with counter
    # Update destination path
    # Increment counter
    # Move file with proper name
    # Print success message
    # Catch any moving errors
    # Print error message
    
    # Fallback to the old method if CDP doesn't work
    # Print fallback message
    # Track files before download
    # Get list of files before download
    # Download each attachment
    # Loop through attachments
    # Download each attachment
    # Wait for downloads to complete
    # Track files after download and rename new ones
    # Get list of files after download
    # Calculate new files
    # Rename new files if any
    # Check if new files exist
    # Rename downloaded files
    # Clean up any issues
    # Clean up double PO prefixes
    
    # Count existing files in supplier folder
    # Try to count files
    # Create supplier folder path
    # Check if folder exists
    # Count files in folder
    # Return count
    # Return 0 if folder doesn't exist
    # Catch any counting errors
    # Return 0
```

#### LoginManager Class Structure:
```
    # Manages login detection and monitoring
    
    # Initialize login manager
    # Store the browser driver
    
    # Detect Coupa login page and automatically monitor for successful login
    # Check if on login page
    # Check URL for login indicators
    # Check title for login indicators
    # Print login detection message
    # Monitor for successful login indicators
    # Set maximum wait time
    # Record start time
    # Loop while within timeout period
    # Try to check login status
    # Get current URL
    # Define success indicators
    # List of URLs that indicate logged-in state
    # Check if on logged-in page
    # Loop through success indicators
    # Check if indicator in current URL
    # Print success message
    # Return if logged in
    # Check if still on login page
    # Check URL for login indicators
    # Print waiting message
    # Wait one second
    # Continue monitoring
    # Check if not on login page
    # Check if not on login page
    # Print success message
    # Return if logged in
    # Catch any checking errors
    # Print error message
    # Wait one second
    # Continue monitoring
    # Print timeout message
    # Print helpful message
    # Raise timeout exception
    # Print already logged in message
    
    # Check if currently logged in to Coupa
    # Try to check login status
    # Get current URL
    # Check if on login pages
    # Check URL for login indicators
    # Return False if on login page
    # Check if on logged-in pages
    # Define success indicators
    # List of URLs that indicate logged-in state
    # Check if on logged-in page
    # Loop through success indicators
    # Check if indicator in current URL
    # Return True if on logged-in page
    # Check if not on login page
    # Check if not on login page
    # Return True if not on login page
    # Catch any checking errors
    # Return False if cannot determine
```

### 5. CSV Processing (`src/core/csv_processor.py`)
The CSV processor handles reading, validating, and processing PO numbers from CSV files.

#### CSVProcessor Class Structure:
```
    # CSV processor class following Single Responsibility Principle
    
    # Read PO numbers from CSV file
    # Check if file exists
    # Raise error if file not found
    # Create empty list for PO entries
    # Open CSV file with proper newline handling
    # Create CSV reader object
    # Try to read header row
    # Skip header if exists
    # Catch end of file exception
    # Continue if file is empty
    # Loop through each row in CSV
    # Check if row is not empty
    # Get first column value and remove spaces
    # Add to PO entries list
    # Return the list of PO entries
    
    # Validate PO number format
    # Remove "PO" prefix from PO number
    # Remove extra spaces
    # Check if remaining string contains only digits
    # Return True if valid, False otherwise
    
    # Clean PO number for use in URLs
    # Remove "PO" prefix from PO number
    # Remove extra spaces
    # Return cleaned PO number
    
    # Process PO numbers and return valid ones
    # Create empty list for valid entries
    # Loop through each PO number
    # Check if PO number is valid
    # Clean the PO number
    # Create tuple with original and cleaned PO
    # Add to valid entries list
    # Print warning for invalid PO
    # Return list of valid PO pairs
    
    # Get CSV file path from configuration
    # Ask configuration module for file path
    # Return the file path
    
    # Backup CSV file before processing
    # Import required modules
    # Get current timestamp
    # Create backup filename
    # Get source file path
    # Create backup file path
    # Copy source file to backup
    # Print success message
    # Catch any backup errors
    # Print error message
    
    # Update PO status in CSV file
    # Import required modules
    # Get current timestamp
    # Read existing CSV data
    # Get CSV file path
    # Open CSV file for reading
    # Create CSV reader
    # Read all rows
    # Find and update PO entry
    # Loop through rows
    # Check if this is the target PO
    # Update PO data
    # Set status
    # Set supplier if provided
    # Set attachments found if provided
    # Set attachments downloaded if provided
    # Set last processed timestamp
    # Set error message if provided
    # Set download folder if provided
    # Set Coupa URL if provided
    # Break loop when found
    # Write updated data back to CSV
    # Open CSV file for writing
    # Create CSV writer
    # Write header row
    # Write all data rows
    # Print success message
    # Catch any update errors
    # Print error message
    
    # Print summary report of processing results
    # Import required modules
    # Get CSV file path
    # Initialize counters
    # Read CSV data
    # Open CSV file
    # Create CSV reader
    # Skip header row
    # Loop through data rows
    # Count total POs
    # Count by status
    # Check status and increment counter
    # Print summary report
    # Print total POs processed
    # Print completed count
    # Print failed count
    # Print partial count
    # Print no attachments count
    # Catch any reading errors
    # Print error message
```

## System Workflow

The system follows this high-level workflow:

1. **Initialization**: The main orchestrator sets up the browser, managers, and configuration
2. **CSV Processing**: PO numbers are read from the input CSV file and validated
3. **Login Management**: The system checks login status and handles authentication
4. **PO Processing**: Each PO is processed sequentially with error handling and recovery
5. **File Download**: Attachments are downloaded with proper naming and organization
6. **Status Tracking**: Progress is tracked and reported in the CSV file
7. **Cleanup**: Browser processes are cleaned up and final reports are generated

## Key Features

### Error Handling and Recovery
- **Browser Session Recovery**: Automatically restarts browser if session is lost
- **Login Detection**: Monitors for login requirements and handles authentication
- **File Naming**: Automatically renames downloaded files with PO prefixes
- **Duplicate Handling**: Prevents duplicate downloads and handles naming conflicts

### Configuration Management
- **Environment Variables**: Supports configuration via environment variables
- **Profile Management**: Uses Edge browser profiles for persistent sessions
- **Download Organization**: Creates supplier-specific folders for file organization

### Monitoring and Reporting
- **Progress Tracking**: Real-time progress updates during processing
- **Status Updates**: Updates CSV file with processing status and results
- **Error Reporting**: Detailed error messages and recovery suggestions
- **Summary Reports**: Final summary of processing results

## File Organization

The system organizes downloaded files in a structured manner:

```
~/Downloads/CoupaDownloads/
├── Supplier_Name_1/
│   ├── PO15262984_document1.pdf
│   ├── PO15262984_document2.docx
│   └── PO15327452_invoice.pdf
├── Supplier_Name_2/
│   ├── PO15362783_contract.pdf
│   └── PO15362783_terms.docx
└── Unknown_Supplier/
    └── PO15826591_file.pdf
```

## Integration Points

The system integrates with several external components:

1. **Coupa Web Interface**: Navigates and extracts data from Coupa PO pages
2. **Edge WebDriver**: Controls Microsoft Edge browser for automation
3. **File System**: Manages downloads, file organization, and naming
4. **CSV Files**: Reads input data and tracks processing status
5. **Environment Configuration**: Uses system environment variables for settings

## Testing and Quality Assurance

The system includes comprehensive testing:

1. **Unit Tests**: Individual component testing with pytest
2. **Integration Tests**: End-to-end workflow testing
3. **Error Handling Tests**: Validation of error recovery mechanisms
4. **Performance Tests**: Monitoring of download speeds and resource usage

## Security Considerations

1. **Session Management**: Uses browser profiles for secure session handling
2. **File Permissions**: Respects system file permissions and security settings
3. **Error Logging**: Avoids logging sensitive information in error messages
4. **Resource Cleanup**: Ensures proper cleanup of browser processes and temporary files

## Performance Optimizations

1. **Parallel Processing**: Supports concurrent downloads where possible
2. **Session Persistence**: Maintains browser sessions to reduce login overhead
3. **File Tracking**: Efficient tracking of downloaded files to prevent duplicates
4. **Memory Management**: Proper cleanup of browser resources and temporary files

## Maintenance and Extensibility

The modular architecture makes the system easy to maintain and extend:

1. **Single Responsibility**: Each class has a single, well-defined purpose
2. **Configuration Driven**: Most settings are externalized to configuration files
3. **Error Isolation**: Errors in one component don't affect others
4. **Testable Design**: Each component can be tested independently
5. **Documentation**: Comprehensive documentation for all components and workflows

This system provides a robust, maintainable solution for automating Coupa attachment downloads while handling the complexities of web automation, file management, and error recovery. 