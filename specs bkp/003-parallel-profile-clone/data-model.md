# Data Model: Parallel Profile Management

## Core Entities

### ProfileManager
**Purpose**: Manages creation, verification, and cleanup of browser profiles for parallel workers

**Fields**:
- `base_profile_path: pathlib.Path` - Path to the default Edge profile directory
- `temp_directory: pathlib.Path` - Base directory for temporary profile clones
- `max_concurrent_clones: int` - Maximum number of simultaneous profile cloning operations
- `clone_timeout: float` - Maximum time allowed for profile cloning operation (seconds)
- `verification_config: VerificationConfig` - Configuration for profile verification

**Methods**:
- `create_worker_profile(worker_id: int) -> WorkerProfile` - Creates isolated profile for worker
- `verify_profile(profile: WorkerProfile) -> VerificationResult` - Verifies profile state
- `cleanup_profile(profile: WorkerProfile) -> None` - Removes temporary profile
- `get_base_profile_status() -> ProfileStatus` - Checks base profile availability

**State Transitions**:
```
ProfileManager: INITIALIZED → ACTIVE → SHUTDOWN
WorkerProfile: CREATING → READY → VERIFIED → IN_USE → CLEANUP → DESTROYED
```

### WorkerProfile
**Purpose**: Represents a browser profile instance assigned to a specific worker

**Fields**:
- `worker_id: int` - Unique identifier for the worker using this profile
- `profile_type: ProfileType` - Either BASE (default profile) or CLONE (temporary copy)
- `profile_path: pathlib.Path` - Filesystem path to the profile directory
- `created_at: datetime` - Timestamp when profile was created/assigned
- `verified_at: Optional[datetime]` - Timestamp of last successful verification
- `verification_status: VerificationStatus` - Current verification state
- `selenium_options: List[str]` - WebDriver command-line options for this profile

**Validation Rules**:
- `worker_id` must be positive integer
- `profile_path` must exist and be readable
- Only one BASE profile allowed per ProfileManager instance
- CLONE profiles must have unique temporary paths

**Methods**:
- `get_selenium_options() -> List[str]` - Returns WebDriver configuration
- `is_ready() -> bool` - Checks if profile is ready for browser startup
- `get_verification_summary() -> Dict[str, Any]` - Returns verification details

### VerificationConfig
**Purpose**: Configuration for profile verification strategies and timeouts

**Fields**:
- `enabled_methods: List[VerificationMethod]` - Which verification methods to use
- `capability_timeout: float` - Timeout for WebDriver capability checks (seconds)
- `auth_check_timeout: float` - Timeout for authentication verification (seconds)
- `auth_check_url: str` - URL for authentication verification endpoint
- `file_verification_enabled: bool` - Whether to verify critical profile files
- `retry_config: RetryConfig` - Retry policy for failed verifications

**Validation Rules**:
- At least one verification method must be enabled
- All timeout values must be positive
- `auth_check_url` must be valid URL when auth verification enabled

### VerificationResult
**Purpose**: Results of profile verification process

**Fields**:
- `worker_id: int` - Worker whose profile was verified
- `overall_status: VerificationStatus` - Overall verification result
- `method_results: Dict[VerificationMethod, MethodResult]` - Per-method results
- `started_at: datetime` - Verification start time
- `completed_at: datetime` - Verification completion time
- `error_details: Optional[str]` - Error message if verification failed
- `retry_count: int` - Number of retry attempts made

**Methods**:
- `is_success() -> bool` - True if all enabled methods passed
- `get_failed_methods() -> List[VerificationMethod]` - Lists failed verification methods
- `get_duration() -> timedelta` - Total verification time

### RetryConfig
**Purpose**: Configuration for retry logic when profile operations fail

**Fields**:
- `max_attempts: int` - Maximum number of retry attempts
- `base_delay: float` - Base delay between retries (seconds)
- `max_delay: float` - Maximum delay between retries (seconds)
- `exponential_backoff: bool` - Whether to use exponential backoff
- `jitter: bool` - Whether to add random jitter to delays

**Validation Rules**:
- `max_attempts` must be at least 1
- `base_delay` and `max_delay` must be positive
- `max_delay` must be >= `base_delay`

## Enumerations

### ProfileType
```python
class ProfileType(Enum):
    BASE = "base"      # Default Edge profile (read-only access)
    CLONE = "clone"    # Temporary profile copy (full access)
```

### VerificationMethod
```python
class VerificationMethod(Enum):
    CAPABILITY_CHECK = "capability"     # WebDriver profile path verification
    AUTH_CHECK = "authentication"      # Session authentication verification
    FILE_VERIFICATION = "file"         # Critical file comparison
```

### VerificationStatus
```python
class VerificationStatus(Enum):
    PENDING = "pending"         # Verification not yet started
    IN_PROGRESS = "in_progress" # Verification currently running
    SUCCESS = "success"         # All verifications passed
    PARTIAL = "partial"         # Some verifications failed
    FAILED = "failed"           # All verifications failed
    TIMEOUT = "timeout"         # Verification timed out
```

### ProfileStatus
```python
class ProfileStatus(Enum):
    AVAILABLE = "available"     # Profile ready for use
    LOCKED = "locked"          # Profile in use by another process
    CORRUPTED = "corrupted"    # Profile appears damaged
    MISSING = "missing"        # Profile directory not found
    PERMISSION_DENIED = "permission_denied"  # Insufficient permissions
```

## Relationships

### ProfileManager → WorkerProfile
- **Type**: One-to-Many
- **Cardinality**: 1 ProfileManager manages 0..N WorkerProfiles
- **Constraint**: Maximum one BASE profile per ProfileManager

### WorkerProfile → VerificationResult
- **Type**: One-to-Many  
- **Cardinality**: 1 WorkerProfile has 0..N VerificationResults (historical)
- **Constraint**: Most recent VerificationResult determines current status

### VerificationConfig → RetryConfig
- **Type**: One-to-One
- **Cardinality**: 1 VerificationConfig has exactly 1 RetryConfig
- **Constraint**: RetryConfig is embedded within VerificationConfig

## Data Flow

### Profile Creation Flow
```
1. ProfileManager.create_worker_profile(worker_id)
2. Determine ProfileType (BASE for worker_id=1, CLONE for others)
3. If CLONE: Copy base_profile_path to temporary directory
4. Create WorkerProfile instance with profile_path
5. Return WorkerProfile in READY state
```

### Verification Flow
```
1. ProfileManager.verify_profile(worker_profile)
2. For each enabled VerificationMethod:
   a. Execute verification with timeout
   b. Record MethodResult
3. Aggregate results into VerificationResult
4. Update WorkerProfile.verification_status
5. Return VerificationResult
```

### Cleanup Flow
```
1. ProfileManager.cleanup_profile(worker_profile)
2. If ProfileType.CLONE: Remove temporary directory
3. If ProfileType.BASE: No filesystem cleanup
4. Update WorkerProfile state to DESTROYED
5. Remove from ProfileManager tracking
```

## Error Handling

### Profile Creation Errors
- **ProfileLockedException**: Base profile is locked by another process
- **InsufficientSpaceException**: Not enough disk space for profile clone
- **PermissionDeniedException**: Cannot read base profile or write to temp directory
- **ProfileCorruptedException**: Base profile appears damaged or incomplete

### Verification Errors
- **VerificationTimeoutException**: Verification exceeded configured timeout
- **AuthenticationFailedException**: Authentication check failed
- **CapabilityMismatchException**: WebDriver reports different profile path
- **FileVerificationException**: Critical profile files missing or corrupted

### Recovery Strategies
- **Profile corruption**: Attempt re-clone from base profile
- **Authentication failure**: Retry with exponential backoff
- **Timeout errors**: Increase timeout and retry once
- **Permission errors**: Fall back to read-only profile access if possible