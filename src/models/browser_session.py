"""
BrowserSession entity for persistent browser management.
Represents a long-running browser instance with multiple tabs.
"""

import time
import psutil
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum
from .profile import Profile
from .tab import Tab, POTask


class SessionStatus(Enum):
    """Status of a browser session."""
    STARTING = "starting"
    READY = "ready"
    ACTIVE = "active"
    IDLE = "idle"
    ERROR = "error"
    CRASHED = "crashed"
    STOPPING = "stopping"
    STOPPED = "stopped"


class SessionError(Enum):
    """Types of session errors."""
    BROWSER_LAUNCH_FAILED = "browser_launch_failed"
    BROWSER_CRASHED = "browser_crashed"
    PROFILE_CORRUPTED = "profile_corrupted"
    MEMORY_EXHAUSTED = "memory_exhausted"
    NETWORK_DISCONNECTED = "network_disconnected"
    AUTHENTICATION_EXPIRED = "authentication_expired"
    WEBDRIVER_ERROR = "webdriver_error"
    SYSTEM_RESOURCE_ERROR = "system_resource_error"


@dataclass
class BrowserSession:
    """
    Browser session entity for persistent browser management.
    
    Manages a browser instance with multiple tabs for PO processing.
    Maintains session state, authentication, and resource monitoring.
    """
    
    session_id: str
    profile: Profile
    status: SessionStatus = SessionStatus.STARTING
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    last_activity_at: float = field(default_factory=time.time)
    browser_process_id: Optional[int] = None
    webdriver_port: Optional[int] = None
    tabs: Dict[str, Tab] = field(default_factory=dict)
    max_tabs: int = 5
    error_count: int = 0
    last_error: Optional[SessionError] = None
    last_error_message: Optional[str] = None
    last_error_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Resource monitoring
    memory_usage_bytes: int = 0
    cpu_usage_percent: float = 0.0
    network_activity: Dict[str, Any] = field(default_factory=dict)
    
    # Performance metrics
    total_tabs_created: int = 0
    total_tasks_processed: int = 0
    session_uptime_seconds: float = 0.0
    average_tab_lifetime: float = 0.0
    
    def __post_init__(self):
        """Initialize session state."""
        if not self.session_id:
            raise ValueError("session_id is required")
        if not isinstance(self.profile, Profile):
            raise ValueError("profile must be a Profile instance")
            
    @property
    def is_active(self) -> bool:
        """Check if session is active and ready for work."""
        return self.status in [SessionStatus.READY, SessionStatus.ACTIVE, SessionStatus.IDLE]
        
    @property
    def is_error_state(self) -> bool:
        """Check if session is in an error state."""
        return self.status in [SessionStatus.ERROR, SessionStatus.CRASHED]
        
    @property
    def has_browser_process(self) -> bool:
        """Check if session has an active browser process."""
        if self.browser_process_id is None:
            return False
            
        try:
            process = psutil.Process(self.browser_process_id)
            return process.is_running()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
            
    @property
    def idle_seconds(self) -> float:
        """Seconds since last activity."""
        return time.time() - self.last_activity_at
        
    @property
    def age_seconds(self) -> float:
        """Age of session in seconds."""
        return time.time() - self.created_at
        
    @property
    def uptime_seconds(self) -> float:
        """Uptime since session started."""
        if self.started_at is None:
            return 0.0
        return time.time() - self.started_at
        
    @property
    def active_tabs(self) -> List[Tab]:
        """Get list of active tabs."""
        return [tab for tab in self.tabs.values() if not tab.status.value.endswith('closed')]
        
    @property
    def available_tabs(self) -> List[Tab]:
        """Get list of tabs available for new tasks."""
        return [tab for tab in self.active_tabs if tab.is_available]
        
    @property
    def processing_tabs(self) -> List[Tab]:
        """Get list of tabs currently processing tasks."""
        return [tab for tab in self.active_tabs if tab.is_processing]
        
    @property
    def can_create_tab(self) -> bool:
        """Check if session can create a new tab."""
        return len(self.active_tabs) < self.max_tabs and self.is_active
        
    def start_browser(self, process_id: int, webdriver_port: Optional[int] = None) -> None:
        """Mark session as started with browser process information."""
        self.browser_process_id = process_id
        self.webdriver_port = webdriver_port
        self.started_at = time.time()
        self.status = SessionStatus.READY
        self.last_activity_at = time.time()
        
    def create_tab(self, tab_id: Optional[str] = None) -> Tab:
        """Create a new tab in this session."""
        if not self.can_create_tab:
            raise RuntimeError(f"Cannot create tab: session has {len(self.active_tabs)} tabs (max: {self.max_tabs})")
            
        if tab_id is None:
            tab_id = f"{self.session_id}_tab_{self.total_tabs_created + 1}"
            
        if tab_id in self.tabs:
            raise ValueError(f"Tab {tab_id} already exists in session")
            
        tab = Tab(tab_id=tab_id, session_id=self.session_id)
        self.tabs[tab_id] = tab
        self.total_tabs_created += 1
        self.last_activity_at = time.time()
        
        return tab
        
    def close_tab(self, tab_id: str) -> bool:
        """Close a tab and remove it from session."""
        if tab_id not in self.tabs:
            return False
            
        tab = self.tabs[tab_id]
        tab.close()
        self.last_activity_at = time.time()
        
        return True
        
    def get_tab(self, tab_id: str) -> Optional[Tab]:
        """Get a tab by ID."""
        return self.tabs.get(tab_id)
        
    def assign_task_to_tab(self, task: POTask, tab_id: Optional[str] = None) -> Optional[Tab]:
        """
        Assign a task to an available tab.
        If tab_id is provided, assigns to that specific tab.
        Otherwise, assigns to any available tab.
        """
        if tab_id is not None:
            # Assign to specific tab
            if tab_id not in self.tabs:
                return None
            tab = self.tabs[tab_id]
            if not tab.is_available:
                return None
            tab.start_task(task)
        else:
            # Assign to any available tab
            available_tabs = self.available_tabs
            if not available_tabs:
                return None
            tab = available_tabs[0]  # Simple assignment strategy
            tab.start_task(task)
            
        self.total_tasks_processed += 1
        self.status = SessionStatus.ACTIVE
        self.last_activity_at = time.time()
        
        return tab
        
    def complete_task(self, tab_id: str, success: bool = True) -> Optional[POTask]:
        """Complete a task in the specified tab."""
        if tab_id not in self.tabs:
            return None
            
        tab = self.tabs[tab_id]
        completed_task = tab.complete_task(success)
        
        if completed_task:
            self.last_activity_at = time.time()
            
            # Update session status based on active tasks
            if not self.processing_tabs:
                self.status = SessionStatus.IDLE
                
        return completed_task
        
    def record_error(self, error: SessionError, message: str) -> None:
        """Record an error for this session."""
        self.error_count += 1
        self.last_error = error
        self.last_error_message = message
        self.last_error_at = time.time()
        self.status = SessionStatus.ERROR
        self.last_activity_at = time.time()
        
        # Store error in metadata for debugging
        if 'errors' not in self.metadata:
            self.metadata['errors'] = []
            
        self.metadata['errors'].append({
            'error': error.value,
            'message': message,
            'timestamp': time.time(),
            'browser_process_id': self.browser_process_id,
            'active_tabs': len(self.active_tabs)
        })
        
        # Keep only last 10 errors to prevent unbounded growth
        if len(self.metadata['errors']) > 10:
            self.metadata['errors'] = self.metadata['errors'][-10:]
            
    def mark_crashed(self) -> None:
        """Mark session as crashed."""
        self.status = SessionStatus.CRASHED
        self.record_error(SessionError.BROWSER_CRASHED, "Browser session crashed or became unresponsive")
        
        # Mark all active tabs as crashed
        for tab in self.active_tabs:
            tab.mark_crashed()
            
    def update_resource_usage(self) -> None:
        """Update resource usage metrics for this session."""
        if not self.has_browser_process:
            self.memory_usage_bytes = 0
            self.cpu_usage_percent = 0.0
            return
            
        try:
            process = psutil.Process(self.browser_process_id)
            
            # Memory usage
            memory_info = process.memory_info()
            self.memory_usage_bytes = memory_info.rss  # Resident Set Size
            
            # CPU usage (this call may block briefly)
            self.cpu_usage_percent = process.cpu_percent(interval=0.1)
            
            # Update activity timestamp
            self.last_activity_at = time.time()
            
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # Process no longer exists or accessible
            self.memory_usage_bytes = 0
            self.cpu_usage_percent = 0.0
            
    def cleanup_tabs(self, max_idle_minutes: int = 30) -> List[str]:
        """
        Clean up idle or problematic tabs.
        Returns list of tab IDs that were closed.
        """
        closed_tabs = []
        current_time = time.time()
        max_idle_seconds = max_idle_minutes * 60
        
        for tab_id, tab in list(self.tabs.items()):
            should_close = False
            
            # Close tabs that are too idle
            if tab.idle_seconds > max_idle_seconds and not tab.is_processing:
                should_close = True
                
            # Close crashed or error tabs
            if tab.is_error_state:
                should_close = True
                
            if should_close:
                self.close_tab(tab_id)
                closed_tabs.append(tab_id)
                
        if closed_tabs:
            self.last_activity_at = time.time()
            
        return closed_tabs
        
    def stop(self) -> None:
        """Stop the browser session gracefully."""
        self.status = SessionStatus.STOPPING
        
        # Close all tabs
        for tab_id in list(self.tabs.keys()):
            self.close_tab(tab_id)
            
        # Mark as stopped
        self.status = SessionStatus.STOPPED
        self.last_activity_at = time.time()
        
    def should_restart(self, max_errors: int = 5, max_idle_minutes: int = 60, max_uptime_hours: int = 8) -> bool:
        """
        Determine if session should be restarted based on various criteria.
        """
        # Too many errors
        if self.error_count >= max_errors:
            return True
            
        # Browser process is gone
        if not self.has_browser_process and self.status != SessionStatus.STOPPED:
            return True
            
        # Session has been idle too long
        idle_minutes = self.idle_seconds / 60
        if idle_minutes > max_idle_minutes and not self.processing_tabs:
            return True
            
        # Session has been running too long
        uptime_hours = self.uptime_seconds / 3600
        if uptime_hours > max_uptime_hours:
            return True
            
        # In error or crashed state
        if self.is_error_state:
            return True
            
        # Profile is corrupted
        if self.profile.is_corrupted:
            return True
            
        return False
        
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this session."""
        return {
            'uptime_seconds': self.uptime_seconds,
            'total_tabs_created': self.total_tabs_created,
            'active_tabs': len(self.active_tabs),
            'available_tabs': len(self.available_tabs),
            'processing_tabs': len(self.processing_tabs),
            'total_tasks_processed': self.total_tasks_processed,
            'memory_usage_bytes': self.memory_usage_bytes,
            'memory_usage_mb': round(self.memory_usage_bytes / 1024 / 1024, 2),
            'cpu_usage_percent': self.cpu_usage_percent,
            'error_count': self.error_count,
            'idle_seconds': self.idle_seconds,
            'age_seconds': self.age_seconds,
            'has_browser_process': self.has_browser_process
        }
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary representation."""
        return {
            'session_id': self.session_id,
            'profile_id': self.profile.profile_id,
            'status': self.status.value,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'last_activity_at': self.last_activity_at,
            'browser_process_id': self.browser_process_id,
            'webdriver_port': self.webdriver_port,
            'max_tabs': self.max_tabs,
            'error_count': self.error_count,
            'last_error': self.last_error.value if self.last_error else None,
            'last_error_message': self.last_error_message,
            'last_error_at': self.last_error_at,
            'memory_usage_bytes': self.memory_usage_bytes,
            'cpu_usage_percent': self.cpu_usage_percent,
            'total_tabs_created': self.total_tabs_created,
            'total_tasks_processed': self.total_tasks_processed,
            'tabs': {tab_id: tab.to_dict() for tab_id, tab in self.tabs.items()},
            'is_active': self.is_active,
            'uptime_seconds': self.uptime_seconds,
            'performance_metrics': self.get_performance_metrics(),
            'metadata': self.metadata.copy()
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any], profile: Profile) -> 'BrowserSession':
        """Create session from dictionary representation."""
        session = cls(
            session_id=data['session_id'],
            profile=profile,
            status=SessionStatus(data['status']),
            created_at=data.get('created_at', time.time()),
            started_at=data.get('started_at'),
            last_activity_at=data.get('last_activity_at', time.time()),
            browser_process_id=data.get('browser_process_id'),
            webdriver_port=data.get('webdriver_port'),
            max_tabs=data.get('max_tabs', 5),
            error_count=data.get('error_count', 0),
            last_error=SessionError(data['last_error']) if data.get('last_error') else None,
            last_error_message=data.get('last_error_message'),
            last_error_at=data.get('last_error_at'),
            memory_usage_bytes=data.get('memory_usage_bytes', 0),
            cpu_usage_percent=data.get('cpu_usage_percent', 0.0),
            total_tabs_created=data.get('total_tabs_created', 0),
            total_tasks_processed=data.get('total_tasks_processed', 0),
            metadata=data.get('metadata', {})
        )
        
        # Restore tabs
        if 'tabs' in data:
            for tab_id, tab_data in data['tabs'].items():
                tab = Tab.from_dict(tab_data)
                session.tabs[tab_id] = tab
                
        return session
        
    def __str__(self) -> str:
        """String representation of session."""
        return f"BrowserSession(id={self.session_id}, status={self.status.value}, tabs={len(self.active_tabs)})"
        
    def __repr__(self) -> str:
        """Detailed representation of session."""
        return (f"BrowserSession(session_id='{self.session_id}', profile='{self.profile.profile_id}', "
                f"status={self.status.value}, active_tabs={len(self.active_tabs)}, "
                f"browser_pid={self.browser_process_id})")