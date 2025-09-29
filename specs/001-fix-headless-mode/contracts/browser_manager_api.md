# Browser Manager API Contract

## Interface: BrowserManager.initialize_driver()

### Input Contract
```python
def initialize_driver(self, headless: bool = False) -> webdriver.Edge:
    """
    Initialize the WebDriver with headless mode support.
    
    Args:
        headless: Boolean flag to enable headless mode
        
    Returns:
        webdriver.Edge: Configured Edge WebDriver instance
        
    Raises:
        HeadlessInitializationError: If headless mode fails to initialize
        BrowserNotFoundError: If Edge browser is not available
        ConfigurationError: If browser options are invalid
    """
```

### Expected Behavior
- **MUST** honor the `headless` parameter in all cases
- **MUST** apply `--headless=new` argument when `headless=True`
- **MUST** retry once if headless initialization fails
- **MUST** prompt user for fallback choice after retry failure
- **MUST** return functional WebDriver instance regardless of mode

### Contract Tests
1. `test_initialize_driver_headless_true_applies_headless_options()`
2. `test_initialize_driver_headless_false_no_headless_options()`
3. `test_initialize_driver_headless_failure_retries_once()`
4. `test_initialize_driver_retry_failure_prompts_user()`

## Interface: InteractiveSetup._interactive_setup()

### Input Contract
```python
def _interactive_setup() -> None:
    """
    Interactive wizard that collects headless preference and applies it.
    
    Side Effects:
        - Collects user headless preference via input prompt
        - Passes headless configuration to browser initialization
        - No environment variable modification
    """
```

### Expected Behavior
- **MUST** prompt user for headless mode preference (Y/n)
- **MUST** pass headless preference to all browser initializations
- **MUST NOT** modify environment variables
- **MUST** provide clear feedback about headless mode status

### Contract Tests
1. `test_interactive_setup_collects_headless_preference()`
2. `test_interactive_setup_passes_headless_to_browser_init()`
3. `test_interactive_setup_no_environment_variable_modification()`

## Interface: ProcessWorker.process_po_worker()

### Input Contract
```python
def process_po_worker(args):
    """
    Process PO in isolated worker with headless configuration.
    
    Args:
        args: Tuple containing (po_data, hierarchy_cols, has_hierarchy_data, headless_config)
        
    Returns:
        dict: Processing results with headless mode confirmation
    """
```

### Expected Behavior
- **MUST** receive headless configuration as part of args tuple
- **MUST** create browser instance with correct headless setting
- **MUST** maintain headless mode throughout processing
- **MUST** log headless mode status for debugging

### Contract Tests
1. `test_process_worker_receives_headless_config()`
2. `test_process_worker_creates_headless_browser()`
3. `test_process_worker_maintains_headless_throughout_processing()`

## Error Handling Contracts

### HeadlessInitializationError
```python
class HeadlessInitializationError(Exception):
    """Raised when headless browser initialization fails."""
    
    def __init__(self, attempt_number: int, original_error: str):
        self.attempt_number = attempt_number
        self.original_error = original_error
        super().__init__(f"Headless initialization failed on attempt {attempt_number}: {original_error}")
```

### UserFallbackChoice
```python
class UserFallbackChoice:
    """Represents user's choice when headless mode fails."""
    
    VISIBLE_MODE = "visible"
    STOP_EXECUTION = "stop"
    
    @staticmethod
    def prompt_user() -> str:
        """Prompt user to choose fallback option."""
        # Returns either VISIBLE_MODE or STOP_EXECUTION
```

## Integration Contract

### End-to-End Flow
1. Interactive setup collects headless preference
2. Headless configuration passed to main execution
3. Browser manager receives explicit headless parameter
4. Process workers inherit headless configuration
5. All browser instances respect headless setting
6. Failure handling follows retry → prompt → choice pattern

### Success Criteria
- Headless mode selection affects all browser instances
- No environment variable dependencies
- Consistent behavior across execution modes
- Graceful failure handling with user control