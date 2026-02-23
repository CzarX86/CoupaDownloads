"""
Centralized constants for CoupaDownloads.

All magic numbers and hardcoded values are defined here with documentation
explaining their purpose and how they were determined.
"""

from typing import Final


# =============================================================================
# PROCESSING TIMEOUTS
# =============================================================================

#: Maximum time to wait for a single PO task to complete (seconds)
#: Based on typical Coupa response times + download time for large attachments
TASK_COMPLETION_TIMEOUT: Final[int] = 120

#: Maximum time to wait for all POs in a batch to complete (seconds)
#: Allows for multiple POs to be processed sequentially if needed
BATCH_COMPLETION_TIMEOUT: Final[int] = 600

#: Timeout for individual browser operations (navigation, click, etc.)
#: Long enough for slow network conditions but not infinite
BROWSER_OPERATION_TIMEOUT: Final[int] = 30

#: Timeout for waiting for downloads to complete (seconds)
#: Large files may take time to download
DOWNLOAD_COMPLETION_TIMEOUT: Final[int] = 300

#: Grace period before forcing shutdown during emergency (seconds)
EMERGENCY_SHUTDOWN_TIMEOUT: Final[int] = 3

#: Normal graceful shutdown timeout (seconds)
GRACEFUL_SHUTDOWN_TIMEOUT: Final[int] = 60


# =============================================================================
# WORKER MANAGEMENT
# =============================================================================

#: Delay between starting workers to prevent resource spikes (seconds)
#: Allows each worker to initialize browser before next one starts
WORKER_STAGGER_DELAY: Final[float] = 0.5

#: Delay between worker status checks (seconds)
WORKER_STATUS_POLL_INTERVAL: Final[float] = 1.0

#: Maximum number of retries for transient worker errors
#: Covers network blips, temporary Coupa unavailability
MAX_WORKER_RETRY_COUNT: Final[int] = 3

#: Backoff multiplier for retry delays (exponential backoff)
RETRY_BACKOFF_MULTIPLIER: Final[float] = 2.0


# =============================================================================
# COMMUNICATION & METRICS
# =============================================================================

#: Maximum metrics to buffer in memory before dropping old ones
#: Balances memory usage with having recent history available
MAX_METRICS_BUFFER_SIZE: Final[int] = 500

#: Maximum recent metrics to show in UI logs
MAX_RECENT_LOGS: Final[int] = 50

#: Throttle limit for draining metrics queue (prevents UI freezing)
METRICS_DRAIN_THROTTLE: Final[int] = 100

#: Interval for batch folder finalization (seconds)
BATCH_FINALIZATION_INTERVAL: Final[int] = 5


# =============================================================================
# RESOURCE THRESHOLDS
# =============================================================================

#: Estimated RAM usage per worker (MB) - Edge browser + Python process
#: Based on empirical measurements of typical worker memory footprint
ESTIMATED_RAM_PER_WORKER_MB: Final[int] = 400

#: Estimated CPU load per worker (as fraction of one core)
ESTIMATED_CPU_LOAD_PER_WORKER: Final[float] = 0.5

#: Minimum free RAM to keep available for system (GB)
#: Below this, system may become unresponsive
MIN_FREE_RAM_GB: Final[float] = 0.3

#: Critical free RAM threshold (GB) - trigger aggressive warnings
CRITICAL_FREE_RAM_GB: Final[float] = 0.5

#: CPU-based worker limit multiplier (workers = cpu_count * this)
CPU_WORKER_MULTIPLIER: Final[int] = 3


# =============================================================================
# BROWSER & DRIVER
# =============================================================================

#: Maximum browser initialization attempts
#: Allows for transient failures (port conflicts, race conditions)
MAX_BROWSER_INIT_ATTEMPTS: Final[int] = 2

#: Delay between browser init retries (seconds)
BROWSER_INIT_RETRY_DELAY: Final[float] = 1.0

#: Timeout for login page load (seconds)
LOGIN_TIMEOUT: Final[int] = 60

#: Timeout for capability verification (seconds)
CAPABILITY_CHECK_TIMEOUT: Final[int] = 5

#: Timeout for authentication verification (seconds)
AUTH_CHECK_TIMEOUT: Final[int] = 10


# =============================================================================
# CSV & PERSISTENCE
# =============================================================================

#: Timeout for CSV writer thread shutdown (seconds)
CSV_WRITER_SHUTDOWN_TIMEOUT: Final[float] = 15.0

#: Delay between CSV write attempts on conflict (seconds)
CSV_WRITE_RETRY_DELAY: Final[float] = 0.5

#: Maximum CSV write retries
CSV_WRITE_MAX_RETRIES: Final[int] = 3


# =============================================================================
# UI & USER INTERACTION
# =============================================================================

#: Frame rate for UI animations (seconds per frame)
UI_FRAME_TIME: Final[float] = 0.016  # ~60 FPS

#: Timeout for user input prompts (seconds) - 0 for infinite
USER_INPUT_TIMEOUT: Final[int] = 0

#: Default UI mode for interactive sessions
DEFAULT_UI_MODE: Final[str] = "premium"

#: Default execution mode
DEFAULT_EXECUTION_MODE: Final[str] = "standard"


# =============================================================================
# ERROR HANDLING
# =============================================================================

#: Maximum error message length in logs (prevents log flooding)
MAX_ERROR_MESSAGE_LENGTH: Final[int] = 450

#: Maximum attachment name length in CSV
MAX_ATTACHMENT_NAME_LENGTH: Final[int] = 255

#: Default folder status when no attachments found
NO_ATTACHMENTS_STATUS: Final[str] = "NO_ATTACHMENTS"

#: Folder suffix for completed downloads
COMPLETED_FOLDER_SUFFIX: Final[str] = "_COMPLETED"

#: Folder suffix for failed downloads
FAILED_FOLDER_SUFFIX: Final[str] = "_FAILED"

#: Folder suffix for partial downloads
PARTIAL_FOLDER_SUFFIX: Final[str] = "_PARTIAL"

#: Working folder suffix (temporary)
WORK_FOLDER_SUFFIX: Final[str] = "__WORK"


# =============================================================================
# PERFORMANCE TUNING
# =============================================================================

#: Stagger delay for high-risk resource scenarios (seconds)
HIGH_RISK_STAGGER_DELAY: Final[float] = 2.0

#: Maximum workers for 8GB systems (empirically determined safe limit)
MAX_WORKERS_8GB_SYSTEM: Final[int] = 4

#: Profile cleanup delay to ensure processes exit (seconds)
PROFILE_CLEANUP_DELAY: Final[float] = 0.5


# =============================================================================
# LOGGING
# =============================================================================

#: Maximum log message length (prevents log file bloat)
MAX_LOG_MESSAGE_LENGTH: Final[int] = 1000

#: Number of log entries to keep in memory for UI
IN_MEMORY_LOG_HISTORY: Final[int] = 100

#: Default log level
DEFAULT_LOG_LEVEL: Final[str] = "INFO"
