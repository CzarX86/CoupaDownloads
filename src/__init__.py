"""
CoupaDownloads - Main package for Coupa file download automation.
"""

__version__ = "1.0.0"
__author__ = "CoupaDownloads Team"

# Persistent Worker Pool Module imports (when available)
try:
    # Models
    from .models.profile import Profile
    from .models.tab import Tab
    from .models.browser_session import BrowserSession
    from .models.worker import Worker
    from .models.worker_pool import PersistentWorkerPool

    # Services
    from .services.profile_manager import ProfileManager
    from .services.memory_monitor import MemoryMonitor
    from .services.task_queue import TaskQueue
    from .services.worker_manager import WorkerManager

    # Infrastructure
    from .lib.signal_handler import SignalHandler
    from .lib.graceful_shutdown import GracefulShutdown

    __all__ = [
        # Models
        'Profile',
        'Tab',
        'BrowserSession',
        'Worker',
        'PersistentWorkerPool',
        
        # Services
        'ProfileManager',
        'MemoryMonitor',
        'TaskQueue',
        'WorkerManager',
        
        # Infrastructure
        'SignalHandler',
        'GracefulShutdown',
    ]
except ImportError:
    # Worker pool modules not yet implemented
    __all__ = [] 