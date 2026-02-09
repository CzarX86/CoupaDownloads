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
"""

from .persistent_pool import PersistentWorkerPool
from .worker_process import WorkerProcess
from .browser_session import BrowserSession
from .shutdown_handler import GracefulShutdown
from .profile_manager import ProfileManager
from .task_queue import TaskQueue, ProcessingTask

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

from .exceptions import (
    ParallelProcessingError,
    WorkerError,
    ProfileError,
    TaskQueueError,
)

# Build __all__ list
__all__ = [
    # Core classes
    'PersistentWorkerPool',
    'WorkerProcess', 
    'BrowserSession',
    'GracefulShutdown',
    'ProfileManager',
    'TaskQueue',
    'ProcessingTask',
    
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
    'TaskHandle',
    
    # Exceptions
    'ParallelProcessingError',
    'WorkerError', 
    'ProfileError',
    'TaskQueueError',
]

# Version information
__version__ = "2.0.0"
__author__ = "CoupaDownloads Team"
__description__ = "Persistent Worker Pool for PO Processing"
