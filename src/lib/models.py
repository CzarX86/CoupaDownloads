"""
Data models for headless mode configuration and browser management.

This module provides the core data structures for managing headless mode
preferences and browser instances throughout the EXPERIMENTAL subproject.
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional


class ExecutionMode(Enum):
    """Supported execution paths for PO processing."""
    STANDARD = "standard"        # Full Browser (Selenium/Edge)
    FILTERED = "filtered"        # Playwright with resource blocking (No images/fonts/CSS)
    NO_JS = "no_js"              # Browser with JS/CSS disabled
    DIRECT_HTTP = "direct_http"  # Pure HTTP requests (No browser per worker)


@dataclass
class HeadlessConfiguration:
    """
    Represents the headless mode preference and its propagation through the system.
    
    This is the single source of truth for headless mode configuration,
    replacing environment variable dependencies.
    """
    
    enabled: bool
    source: str = "interactive_setup"
    retry_attempted: bool = False
    fallback_to_visible: bool = False
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not isinstance(self.enabled, bool):
            raise ValueError("enabled must be boolean")
        
        if self.source != "interactive_setup":
            raise ValueError("source must equal 'interactive_setup'")
        
        if self.retry_attempted and not isinstance(self.retry_attempted, bool):
            raise ValueError("retry_attempted must be boolean")
        
        if self.fallback_to_visible and not isinstance(self.fallback_to_visible, bool):
            raise ValueError("fallback_to_visible must be boolean")
        
        # Business rule: fallback_to_visible only valid if retry was attempted
        if self.fallback_to_visible and not self.retry_attempted:
            raise ValueError("fallback_to_visible only valid if retry_attempted is True")
    
    def mark_retry_attempted(self) -> 'HeadlessConfiguration':
        """
        Create a new configuration marking that retry was attempted.
        
        Returns:
            New HeadlessConfiguration with retry_attempted=True
        """
        return HeadlessConfiguration(
            enabled=self.enabled,
            source=self.source,
            retry_attempted=True,
            fallback_to_visible=self.fallback_to_visible
        )
    
    def mark_fallback_to_visible(self) -> 'HeadlessConfiguration':
        """
        Create a new configuration marking fallback to visible mode.
        
        Returns:
            New HeadlessConfiguration with fallback_to_visible=True
        """
        if not self.retry_attempted:
            raise ValueError("Cannot fallback to visible without retry attempt")
        
        return HeadlessConfiguration(
            enabled=False,  # Fallback means no longer headless
            source=self.source,
            retry_attempted=True,
            fallback_to_visible=True
        )
    
    def get_effective_headless_mode(self) -> bool:
        """
        Get the effective headless mode considering fallback state.
        
        Returns:
            True if headless mode should be used, False if visible mode
        """
        if self.fallback_to_visible:
            return False
        return self.enabled
    
    def __str__(self) -> str:
        """String representation for logging."""
        mode = "headless" if self.get_effective_headless_mode() else "visible"
        status_parts = []
        
        if self.retry_attempted:
            status_parts.append("retry attempted")
        if self.fallback_to_visible:
            status_parts.append("fallback to visible")
        
        status = f" ({', '.join(status_parts)})" if status_parts else ""
        return f"HeadlessConfiguration: {mode} mode{status}"


@dataclass
class BrowserInstance:
    """
    Represents individual browser sessions with headless configuration.
    
    Tracks the state of a single browser instance including its headless
    configuration and initialization attempts.
    """
    
    headless_mode: bool
    initialization_attempts: int = 1
    process_id: Optional[str] = None
    edge_options: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate browser instance after initialization."""
        if not isinstance(self.headless_mode, bool):
            raise ValueError("headless_mode must be boolean")
        
        if not isinstance(self.initialization_attempts, int) or self.initialization_attempts < 1:
            raise ValueError("initialization_attempts must be positive integer")
        
        if self.initialization_attempts > 2:
            raise ValueError("initialization_attempts must be 1 or 2 (initial + retry)")
        
        if not isinstance(self.edge_options, dict):
            raise ValueError("edge_options must be dictionary")
    
    def increment_attempts(self) -> 'BrowserInstance':
        """
        Create a new instance with incremented initialization attempts.
        
        Returns:
            New BrowserInstance with attempts incremented
            
        Raises:
            ValueError: If already at maximum attempts (2)
        """
        if self.initialization_attempts >= 2:
            raise ValueError("Maximum initialization attempts (2) already reached")
        
        return BrowserInstance(
            headless_mode=self.headless_mode,
            initialization_attempts=self.initialization_attempts + 1,
            process_id=self.process_id,
            edge_options=self.edge_options.copy()
        )
    
    def update_headless_mode(self, new_headless_mode: bool) -> 'BrowserInstance':
        """
        Create a new instance with updated headless mode.
        
        Args:
            new_headless_mode: New headless mode setting
            
        Returns:
            New BrowserInstance with updated headless mode
        """
        return BrowserInstance(
            headless_mode=new_headless_mode,
            initialization_attempts=self.initialization_attempts,
            process_id=self.process_id,
            edge_options=self.edge_options.copy()
        )
    
    def is_process_worker(self) -> bool:
        """Check if this instance belongs to a process worker."""
        return self.process_id is not None
    
    def __str__(self) -> str:
        """String representation for logging."""
        mode = "headless" if self.headless_mode else "visible"
        worker_info = f" (worker: {self.process_id})" if self.process_id else ""
        attempts_info = f" attempts: {self.initialization_attempts}"
        return f"BrowserInstance: {mode} mode{worker_info}{attempts_info}"


@dataclass
class InteractiveSetupSession:
    """
    Represents user configuration session including headless preference.
    
    Captures the user's choices during interactive setup and tracks
    whether the configuration was successfully applied.
    """
    
    headless_preference: bool
    ui_mode: str = "standard" # "standard" (Rich) or "premium" (Textual)
    execution_mode: ExecutionMode = ExecutionMode.STANDARD
    session_timestamp: datetime = field(default_factory=datetime.now)
    configuration_applied: bool = False
    
    def __post_init__(self):
        """Validate setup session after initialization."""
        if not isinstance(self.headless_preference, bool):
            raise ValueError("headless_preference must be boolean")
        
        if self.ui_mode not in ("standard", "premium"):
            raise ValueError("ui_mode must be 'standard' or 'premium'")
        
        if not isinstance(self.execution_mode, ExecutionMode):
            raise ValueError("execution_mode must be an ExecutionMode enum")
        
        if not isinstance(self.session_timestamp, datetime):
            raise ValueError("session_timestamp must be datetime")
        
        if not isinstance(self.configuration_applied, bool):
            raise ValueError("configuration_applied must be boolean")
    
    def create_headless_configuration(self) -> HeadlessConfiguration:
        """
        Create a HeadlessConfiguration from this setup session.
        
        Returns:
            HeadlessConfiguration based on user preference
        """
        return HeadlessConfiguration(
            enabled=self.headless_preference,
            source="interactive_setup"
        )
    
    def mark_configuration_applied(self) -> 'InteractiveSetupSession':
        """
        Create a new session marking configuration as applied.
        
        Returns:
            New InteractiveSetupSession with configuration_applied=True
        """
        return InteractiveSetupSession(
            headless_preference=self.headless_preference,
            ui_mode=self.ui_mode,
            execution_mode=self.execution_mode,
            session_timestamp=self.session_timestamp,
            configuration_applied=True
        )
    
    def __str__(self) -> str:
        """String representation for logging."""
        preference = "headless" if self.headless_preference else "visible"
        status = "applied" if self.configuration_applied else "pending"
        timestamp_str = self.session_timestamp.strftime("%Y-%m-%d %H:%M:%S")
        return f"InteractiveSetupSession: {preference} preference, {status} ({timestamp_str})"


# Factory functions for common scenarios

def create_headless_configuration(enabled: bool) -> HeadlessConfiguration:
    """
    Factory function to create a standard HeadlessConfiguration.
    
    Args:
        enabled: Whether headless mode is enabled
        
    Returns:
        HeadlessConfiguration with standard settings
    """
    return HeadlessConfiguration(enabled=enabled)


def create_browser_instance_for_main_process(headless_config: HeadlessConfiguration) -> BrowserInstance:
    """
    Factory function to create a BrowserInstance for the main process.
    
    Args:
        headless_config: HeadlessConfiguration to apply
        
    Returns:
        BrowserInstance configured for main process
    """
    return BrowserInstance(
        headless_mode=headless_config.get_effective_headless_mode(),
        process_id=None
    )


def create_browser_instance_for_worker(headless_config: HeadlessConfiguration, 
                                     worker_id: str) -> BrowserInstance:
    """
    Factory function to create a BrowserInstance for a process worker.
    
    Args:
        headless_config: HeadlessConfiguration to apply
        worker_id: Identifier for the process worker
        
    Returns:
        BrowserInstance configured for process worker
    """
    return BrowserInstance(
        headless_mode=headless_config.get_effective_headless_mode(),
        process_id=worker_id
    )


def create_interactive_setup_session(headless_preference: bool) -> InteractiveSetupSession:
    """
    Factory function to create an InteractiveSetupSession.
    
    Args:
        headless_preference: User's headless mode preference
        
    Returns:
        InteractiveSetupSession with current timestamp
    """
    return InteractiveSetupSession(headless_preference=headless_preference)