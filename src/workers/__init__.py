"""
Persistent Worker Pool Implementation.

This package provides a comprehensive worker pool system for parallel
PO processing with browser automation, featuring:

- PersistentWorkerPool: Main orchestrator for worker management
- WorkerProcess: Individual worker lifecycle management
- BrowserSession: Persistent browser sessions with tab management
- ProfileManager: Browser profile isolation and corruption detection
- TaskQueue: Priority-based task scheduling
- GracefulShutdown: Signal-based graceful shutdown coordination

Core Features:
- Async/await support for non-blocking operations
- Thread-safe resource management
- Context manager support
- Comprehensive error handling and recovery
- Structured logging throughout
- Health monitoring and statistics

Legacy Components (for backward compatibility):
- WorkerPool: Original worker pool implementation
- ProfileManager: Original profile management
- TaskQueue: Original task queue
"""

# New persistent worker pool implementation
try:
    from .persistent_pool import PersistentWorkerPool
    from .worker_process import WorkerProcess
    from .browser_session import BrowserSession
    from .shutdown_handler import GracefulShutdown
    
    # Import models for convenience
    from .models import (
        # Worker management
        Worker, WorkerStatus,
        
        # Profile management
        Profile, ProfileStatus,
        
        # Task management
        POTask, TaskStatus, TaskPriority,
        Tab, TabStatus,
        BrowserSession as BrowserSessionModel,
        SessionStatus,
        
        # Configuration
        PoolConfig, TaskHandle
    )
    
    NEW_IMPLEMENTATION_AVAILABLE = True
    
except ImportError as e:
    NEW_IMPLEMENTATION_AVAILABLE = False
    print(f"New implementation not available: {e}")

# Legacy implementation (for backward compatibility)
try:
    from .exceptions import (
        ParallelProcessingError,
        WorkerError,
        ProfileError,
        TaskQueueError,
    )

    from .profile_manager import ProfileManager as LegacyProfileManager
    from .task_queue import TaskQueue as LegacyTaskQueue, ProcessingTask
    from .worker_pool import WorkerPool, WorkerInstance
    
    LEGACY_IMPLEMENTATION_AVAILABLE = True
    
except ImportError:
    # Handle direct script execution
    try:
        from .exceptions import (
            ParallelProcessingError,
            WorkerError,
            ProfileError,
            TaskQueueError,
        )

        from .profile_manager import ProfileManager as LegacyProfileManager
        from .task_queue import TaskQueue as LegacyTaskQueue, ProcessingTask
        from .worker_pool import WorkerPool, WorkerInstance
        
        LEGACY_IMPLEMENTATION_AVAILABLE = True
    except ImportError:
        LEGACY_IMPLEMENTATION_AVAILABLE = False

# Build __all__ list based on available implementations
__all__ = []

if NEW_IMPLEMENTATION_AVAILABLE:
    __all__.extend([
        # Core classes
        'PersistentWorkerPool',
        'WorkerProcess', 
        'BrowserSession',
        'GracefulShutdown',
        
        # Data models
        'Worker',
        'WorkerStatus',
        'Profile',
        'ProfileStatus',
        'POTask',
        'TaskStatus', 
        'TaskPriority',
        'Tab',
        'TabStatus',
        'BrowserSessionModel',
        'SessionStatus',
        'PoolConfig',
        'TaskHandle'
    ])

if LEGACY_IMPLEMENTATION_AVAILABLE:
    __all__.extend([
        'ParallelProcessingError',
        'WorkerError', 
        'ProfileError',
        'TaskQueueError',
        'LegacyProfileManager',
        'LegacyTaskQueue',
        'ProcessingTask',
        'WorkerPool',
        'WorkerInstance',
    ])

# Version information
__version__ = "2.0.0"  # Incremented for new persistent worker pool
__author__ = "CoupaDownloads Team"
__description__ = "Persistent Worker Pool for PO Processing"
