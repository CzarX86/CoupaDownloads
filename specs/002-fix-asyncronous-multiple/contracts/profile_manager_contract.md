# ProfileManager API Contract

**Module**: `EXPERIMENTAL.corelib.profile_manager`  
**Class**: `ProfileManager`

## Constructor

```python
def __init__(
    self,
    base_profile_path: Optional[str] = None,
    cleanup_on_exit: bool = True,
    max_profiles: int = 8,
    profile_size_limit_mb: int = 500
) -> None:
    """Initialize profile manager for temporary browser profiles.
    
    Args:
        base_profile_path: Template profile to copy (optional)
        cleanup_on_exit: Auto-cleanup profiles on manager destruction
        max_profiles: Maximum concurrent profiles allowed
        profile_size_limit_mb: Maximum profile size in MB
        
    Raises:
        ValueError: If max_profiles < 1 or > 16
        FileNotFoundError: If base_profile_path specified but doesn't exist
        PermissionError: If base_profile_path not readable
    """
```

## Core Methods

### create_profile
```python
def create_profile(self, worker_id: str) -> str:
    """Create temporary browser profile for worker.
    
    Args:
        worker_id: Unique identifier for the worker
        
    Returns:
        str: Absolute path to created profile directory
        
    Raises:
        ValueError: If worker_id already has profile or is invalid
        OSError: If profile creation fails (disk space, permissions)
        ProfileLimitError: If max_profiles limit exceeded
        
    Side Effects:
        - Creates temporary directory in system temp location
        - Copies base profile if configured
        - Sets appropriate permissions for browser access
        - Registers profile for cleanup tracking
    """
```

### copy_base_profile
```python
def copy_base_profile(self, worker_id: str) -> bool:
    """Copy base profile template to worker's profile directory.
    
    Args:
        worker_id: Worker identifier whose profile to populate
        
    Returns:
        bool: True if base profile was copied successfully
        
    Note:
        Only copies if base_profile_path was configured
        Skips large cache files and temporary data
        Preserves essential settings and extensions
    """
```

### cleanup_profile
```python
def cleanup_profile(self, worker_id: str) -> bool:
    """Remove temporary profile for specified worker.
    
    Args:
        worker_id: Worker identifier whose profile to remove
        
    Returns:
        bool: True if profile was removed successfully
        
    Note:
        Returns True if profile doesn't exist (idempotent)
        Handles locked files and permission issues gracefully
        Logs warnings for cleanup issues but doesn't fail
        
    Side Effects:
        - Removes profile directory and all contents
        - Updates internal tracking
        - Retries cleanup for locked files (Windows compatibility)
    """
```

### cleanup_all_profiles
```python
def cleanup_all_profiles(self) -> int:
    """Remove all temporary profiles managed by this instance.
    
    Returns:
        int: Number of profiles successfully removed
        
    Side Effects:
        - Removes all tracked profile directories
        - Clears internal tracking state
        - Logs cleanup summary and any failures
        - Attempts cleanup even for partially failed profiles
    """
```

### get_profile_path
```python
def get_profile_path(self, worker_id: str) -> Optional[str]:
    """Get profile path for specified worker.
    
    Args:
        worker_id: Worker identifier to lookup
        
    Returns:
        Optional[str]: Profile path if exists, None otherwise
    """
```

### validate_profile
```python
def validate_profile(self, worker_id: str) -> bool:
    """Validate profile exists and is accessible for browser use.
    
    Args:
        worker_id: Worker identifier to validate
        
    Returns:
        bool: True if profile is valid and accessible
        
    Checks:
        - Profile directory exists and is readable
        - Permissions allow browser access
        - Essential profile structure is intact
        - No corruption or locking issues
    """
```

### get_profile_size
```python
def get_profile_size(self, worker_id: str) -> int:
    """Calculate disk usage of worker's profile directory.
    
    Args:
        worker_id: Worker identifier to check
        
    Returns:
        int: Profile size in bytes, 0 if profile doesn't exist
        
    Note:
        May be slow for large profiles, use sparingly
        Used for monitoring and cleanup decisions
    """
```

### list_profiles
```python
def list_profiles(self) -> Dict[str, Dict[str, Any]]:
    """Get all currently managed profiles with metadata.
    
    Returns:
        Dict[str, Dict[str, Any]]: Mapping of worker_id to profile info:
            - path: str - Profile directory path
            - size_mb: float - Profile size in MB
            - created_at: datetime - Creation timestamp
            - last_accessed: datetime - Last access time
            - is_valid: bool - Profile validation status
    """
```

## Resource Management

### Profile Creation
- Profiles created in system temporary directory
- Unique subdirectory per worker using worker_id and UUID suffix
- Optional copying from base profile template (preserves settings)
- Proper permissions set for browser access
- Size limits enforced during creation

### Profile Cleanup
- Automatic cleanup on manager destruction (if enabled)
- Robust handling of locked browser files and Windows file locking
- Retry logic for cleanup operations
- Comprehensive logging of cleanup operations and failures
- Graceful handling of permission issues

### Resource Limits
- Maximum concurrent profiles enforced
- Disk space validation before profile creation
- Profile size monitoring and limits
- Memory usage tracking for large profile operations

## Error Handling

### Custom Exceptions
```python
class ProfileCreationError(Exception):
    """Raised when profile creation fails"""
    def __init__(self, worker_id: str, reason: str):
        self.worker_id = worker_id
        self.reason = reason
        super().__init__(f"Profile creation failed for {worker_id}: {reason}")

class ProfileLimitError(Exception):
    """Raised when max profiles limit exceeded"""
    def __init__(self, current_count: int, max_allowed: int):
        self.current_count = current_count
        self.max_allowed = max_allowed
        super().__init__(f"Profile limit exceeded: {current_count}/{max_allowed}")

class ProfileCleanupError(Exception):
    """Raised when profile cleanup fails"""
    def __init__(self, worker_id: str, reason: str):
        self.worker_id = worker_id
        self.reason = reason
        super().__init__(f"Profile cleanup failed for {worker_id}: {reason}")
```

### Recovery Strategies
- Retry profile creation with different temp directory on failure
- Graceful degradation when cleanup partially fails
- Detailed error logging for debugging and monitoring
- Safe handling of concurrent access from multiple workers
- Fallback to sequential mode if profile creation fails repeatedly

## Thread Safety

ProfileManager must be thread-safe for concurrent worker access:
- Profile creation from multiple workers simultaneously
- Cleanup operations during worker shutdown
- Status queries and validation during processing
- Resource monitoring and limit enforcement

## Performance Requirements

- Profile creation: < 10 seconds (including base copy if configured)
- Profile cleanup: < 5 seconds per profile
- Profile validation: < 1 second
- Size calculation: < 2 seconds (cached where possible)
- List operations: < 100ms

## Integration Requirements

### Browser Compatibility
- Support Edge browser profile format and structure
- Preserve essential browser settings and preferences
- Handle profile version migrations gracefully
- Maintain download directory preferences and security settings

### System Compatibility
- Windows file locking behavior and retry logic
- macOS permission restrictions and sandbox compatibility
- Linux temp directory conventions and permissions
- Cross-platform path handling and normalization

### EXPERIMENTAL Integration
- Compatible with existing HeadlessConfiguration settings
- Integration with BrowserManager for profile path configuration
- Preservation of existing download directory organization
- Support for existing logging and monitoring infrastructure

---

*Contract defines expected behavior for ProfileManager implementation*