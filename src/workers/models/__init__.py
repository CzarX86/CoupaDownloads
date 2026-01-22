"""
Enhanced data models for the persistent worker pool.

This package provides comprehensive data models for:
- Worker process management and status tracking
- Browser profile management with corruption detection
- Tab lifecycle management for PO processing
- Browser session state preservation
- Task management with priority and retry logic
- Pool configuration and validation
"""

from .worker import Worker, WorkerStatus
from .profile import Profile, ProfileStatus
from .tab import Tab, TabStatus
from .browser_session import BrowserSession, SessionStatus
from .po_task import POTask, TaskStatus, TaskPriority
from .config import PoolConfig, TaskHandle

__all__ = [
    # Worker management
    'Worker',
    'WorkerStatus',
    
    # Profile management
    'Profile', 
    'ProfileStatus',
    
    # Tab management
    'Tab',
    'TabStatus',
    
    # Session management
    'BrowserSession',
    'SessionStatus',
    
    # Task management
    'POTask',
    'TaskStatus',
    'TaskPriority',
    
    # Configuration
    'PoolConfig',
    'TaskHandle'
]