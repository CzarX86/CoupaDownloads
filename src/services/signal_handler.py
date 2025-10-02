"""
SignalHandler service for graceful shutdown signal handling.
Handles system signals (SIGTERM, SIGINT) and coordinates graceful shutdown.
"""

import signal
import threading
import time
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class ShutdownHandler:
    """Configuration for shutdown handling."""
    name: str
    callback: Callable[[], bool]  # Should return True if shutdown successful
    timeout: int = 30
    priority: int = 5  # Lower numbers = higher priority
    

class SignalHandler:
    """
    Service for handling system signals and coordinating graceful shutdown.
    
    Responsibilities:
    - Register signal handlers for SIGTERM, SIGINT, etc.
    - Coordinate shutdown sequence with multiple components
    - Enforce shutdown timeouts and escalation
    - Provide shutdown status and progress tracking
    - Handle emergency shutdown scenarios
    """
    
    def __init__(self, 
                 shutdown_timeout: int = 60,
                 force_kill_timeout: int = 10):
        """
        Initialize SignalHandler.
        
        Args:
            shutdown_timeout: Total time allowed for graceful shutdown
            force_kill_timeout: Time to wait before force kill
        """
        self.shutdown_timeout = shutdown_timeout
        self.force_kill_timeout = force_kill_timeout
        
        # State tracking
        self.shutdown_requested = threading.Event()
        self.shutdown_complete = threading.Event()
        self.emergency_shutdown = threading.Event()
        
        # Shutdown handlers
        self.handlers: List[ShutdownHandler] = []
        self._handlers_lock = threading.RLock()
        
        # Signal tracking
        self.signals_received: List[Dict[str, Any]] = []
        self.original_handlers: Dict[int, Any] = {}
        
        # Shutdown thread
        self._shutdown_thread: Optional[threading.Thread] = None
        
        # Statistics
        self.stats = {
            'signals_received': 0,
            'shutdown_attempts': 0,
            'successful_shutdowns': 0,
            'forced_shutdowns': 0,
            'emergency_shutdowns': 0
        }
        
    def register_signals(self, signals: Optional[List[int]] = None) -> bool:
        """
        Register signal handlers.
        
        Args:
            signals: List of signals to handle (default: SIGTERM, SIGINT)
            
        Returns:
            True if signals were registered successfully
        """
        if signals is None:
            signals = [signal.SIGTERM, signal.SIGINT]
            
        try:
            for sig in signals:
                # Store original handler
                self.original_handlers[sig] = signal.signal(sig, self._signal_handler)
                
            return True
            
        except Exception:
            return False
            
    def unregister_signals(self) -> bool:
        """
        Restore original signal handlers.
        
        Returns:
            True if signals were restored successfully
        """
        try:
            for sig, original_handler in self.original_handlers.items():
                signal.signal(sig, original_handler)
                
            self.original_handlers.clear()
            return True
            
        except Exception:
            return False
            
    def register_shutdown_handler(self, 
                                   name: str,
                                   callback: Callable[[], bool],
                                   timeout: int = 30,
                                   priority: int = 5) -> None:
        """
        Register a shutdown handler.
        
        Args:
            name: Name of the handler
            callback: Function to call during shutdown
            timeout: Timeout for this handler
            priority: Priority (lower = higher priority)
        """
        with self._handlers_lock:
            handler = ShutdownHandler(
                name=name,
                callback=callback,
                timeout=timeout,
                priority=priority
            )
            
            self.handlers.append(handler)
            # Sort by priority
            self.handlers.sort(key=lambda h: h.priority)
            
    def unregister_shutdown_handler(self, name: str) -> bool:
        """
        Unregister a shutdown handler.
        
        Args:
            name: Name of handler to remove
            
        Returns:
            True if handler was removed
        """
        with self._handlers_lock:
            for i, handler in enumerate(self.handlers):
                if handler.name == name:
                    del self.handlers[i]
                    return True
            return False
            
    def request_shutdown(self, reason: str = "Signal received") -> bool:
        """
        Request graceful shutdown.
        
        Args:
            reason: Reason for shutdown request
            
        Returns:
            True if shutdown was initiated
        """
        if self.shutdown_requested.is_set():
            return False  # Already shutting down
            
        self.stats['shutdown_attempts'] += 1
        
        # Record shutdown request
        shutdown_info = {
            'reason': reason,
            'timestamp': time.time(),
            'thread_id': threading.get_ident()
        }
        self.signals_received.append(shutdown_info)
        
        # Signal shutdown
        self.shutdown_requested.set()
        
        # Start shutdown thread
        self._shutdown_thread = threading.Thread(
            target=self._execute_shutdown,
            name="GracefulShutdown",
            args=(reason,),
            daemon=True
        )
        self._shutdown_thread.start()
        
        return True
        
    def request_emergency_shutdown(self, reason: str = "Emergency") -> None:
        """
        Request immediate emergency shutdown.
        
        Args:
            reason: Reason for emergency shutdown
        """
        self.stats['emergency_shutdowns'] += 1
        
        emergency_info = {
            'reason': reason,
            'timestamp': time.time(),
            'thread_id': threading.get_ident()
        }
        self.signals_received.append(emergency_info)
        
        self.emergency_shutdown.set()
        self.shutdown_requested.set()
        
    def wait_for_shutdown(self, timeout: Optional[int] = None) -> bool:
        """
        Wait for shutdown to complete.
        
        Args:
            timeout: Maximum time to wait
            
        Returns:
            True if shutdown completed within timeout
        """
        if timeout is None:
            timeout = self.shutdown_timeout + self.force_kill_timeout
            
        return self.shutdown_complete.wait(timeout)
        
    def is_shutdown_requested(self) -> bool:
        """
        Check if shutdown has been requested.
        
        Returns:
            True if shutdown was requested
        """
        return self.shutdown_requested.is_set()
        
    def is_emergency_shutdown(self) -> bool:
        """
        Check if emergency shutdown was requested.
        
        Returns:
            True if emergency shutdown was requested
        """
        return self.emergency_shutdown.is_set()
        
    def get_status(self) -> Dict[str, Any]:
        """
        Get current signal handler status.
        
        Returns:
            Dictionary with status information
        """
        with self._handlers_lock:
            handlers_info = [
                {
                    'name': h.name,
                    'timeout': h.timeout,
                    'priority': h.priority
                }
                for h in self.handlers
            ]
            
        return {
            'shutdown_requested': self.shutdown_requested.is_set(),
            'shutdown_complete': self.shutdown_complete.is_set(),
            'emergency_shutdown': self.emergency_shutdown.is_set(),
            'registered_signals': list(self.original_handlers.keys()),
            'registered_handlers': len(self.handlers),
            'handlers': handlers_info,
            'shutdown_timeout': self.shutdown_timeout,
            'force_kill_timeout': self.force_kill_timeout,
            'signals_received': self.signals_received.copy(),
            'statistics': self.stats.copy()
        }
        
    def _signal_handler(self, signum: int, frame) -> None:
        """
        Handle incoming signals.
        
        Args:
            signum: Signal number
            frame: Stack frame
        """
        self.stats['signals_received'] += 1
        
        signal_names = {
            signal.SIGTERM.value: 'SIGTERM',
            signal.SIGINT.value: 'SIGINT'
        }
        
        signal_name = signal_names.get(signum, f'SIGNAL_{signum}')
        
        # Check if this is a second signal (emergency)
        if self.shutdown_requested.is_set():
            self.request_emergency_shutdown(f"Second {signal_name} received")
        else:
            self.request_shutdown(f"{signal_name} received")
            
    def _execute_shutdown(self, reason: str) -> None:
        """
        Execute the shutdown sequence.
        
        Args:
            reason: Reason for shutdown
        """
        start_time = time.time()
        shutdown_successful = True
        
        try:
            # Execute handlers in priority order
            with self._handlers_lock:
                handlers_to_execute = self.handlers.copy()
                
            for handler in handlers_to_execute:
                if self.emergency_shutdown.is_set():
                    break  # Skip remaining handlers for emergency shutdown
                    
                handler_start = time.time()
                elapsed = handler_start - start_time
                
                # Check if we have enough time left
                remaining_time = self.shutdown_timeout - elapsed
                if remaining_time <= 0:
                    shutdown_successful = False
                    break
                    
                # Execute handler with timeout
                handler_timeout = min(handler.timeout, remaining_time)
                handler_success = self._execute_handler_with_timeout(handler, handler_timeout)
                
                if not handler_success:
                    shutdown_successful = False
                    
            # Update statistics
            if shutdown_successful and not self.emergency_shutdown.is_set():
                self.stats['successful_shutdowns'] += 1
            else:
                self.stats['forced_shutdowns'] += 1
                
        except Exception:
            shutdown_successful = False
            self.stats['forced_shutdowns'] += 1
            
        finally:
            # Mark shutdown complete
            self.shutdown_complete.set()
            
    def _execute_handler_with_timeout(self, handler: ShutdownHandler, timeout: float) -> bool:
        """
        Execute a shutdown handler with timeout.

        Args:
            handler: Handler to execute
            timeout: Timeout in seconds
            
        Returns:
            True if handler completed successfully
        """
        result_container = {'success': False}
        
        def handler_wrapper():
            try:
                result_container['success'] = handler.callback()
            except Exception:
                result_container['success'] = False
                
        handler_thread = threading.Thread(
            target=handler_wrapper,
            name=f"Shutdown-{handler.name}"
        )
        
        handler_thread.start()
        handler_thread.join(timeout)
        
        if handler_thread.is_alive():
            # Handler timed out
            return False
            
        return result_container['success']