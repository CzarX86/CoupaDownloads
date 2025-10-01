"""
Models package for persistent worker pool.
Provides core data entities and enums for worker pool management.
"""

from .profile import Profile, ProfileStatus
from .tab import Tab, TabStatus, TabError, POTask
from .browser_session import BrowserSession, SessionStatus, SessionError
from .worker import Worker, WorkerConfiguration, WorkerStatus, WorkerError
from .worker_pool import PersistentWorkerPool, PoolConfiguration, PoolStatus, PoolError

__all__ = [
    # Profile entities
    'Profile',
    'ProfileStatus',
    
    # Tab entities
    'Tab',
    'TabStatus', 
    'TabError',
    'POTask',
    
    # Browser session entities
    'BrowserSession',
    'SessionStatus',
    'SessionError',
    
    # Worker entities
    'Worker',
    'WorkerConfiguration',
    'WorkerStatus',
    'WorkerError',
    
    # Worker pool entities
    'PersistentWorkerPool',
    'PoolConfiguration',
    'PoolStatus',
    'PoolError'
]