"""
Services package for persistent worker pool.
Provides core business logic services for worker pool management.
"""

from .profile_manager import ProfileManager
from .memory_monitor import MemoryMonitor, MemoryThreshold
from .task_queue import TaskQueue, PriorityTask
from .signal_handler import SignalHandler, ShutdownHandler
from .graceful_shutdown import GracefulShutdown, ShutdownPhase
from .worker_manager import WorkerManager

__all__ = [
    # Profile management
    'ProfileManager',
    
    # Memory monitoring
    'MemoryMonitor',
    'MemoryThreshold',
    
    # Task management
    'TaskQueue',
    'PriorityTask',
    
    # Signal handling
    'SignalHandler',
    'ShutdownHandler',
    
    # Graceful shutdown
    'GracefulShutdown',
    'ShutdownPhase',
    
    # Worker management
    'WorkerManager'
]