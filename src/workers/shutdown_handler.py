"""
GracefulShutdown signal handling for worker pool termination.

This module provides the GracefulShutdown class for handling system
signals and coordinating graceful shutdown with support for:
- Signal handler registration
- Shutdown callback coordination
- Timeout-based forced shutdown
- Resource cleanup coordination
"""

import signal
import threading
import time
from typing import List, Callable, Optional
import structlog

logger = structlog.get_logger(__name__)


class GracefulShutdown:
    """
    Graceful shutdown coordinator.
    
    Handles system signals and coordinates graceful shutdown
    of worker pool components with timeout protection.
    """
    
    def __init__(self, shutdown_timeout: float = 60.0):
        """
        Initialize graceful shutdown handler.
        
        Args:
            shutdown_timeout: Maximum time to wait for graceful shutdown
        """
        self.shutdown_timeout = shutdown_timeout
        
        # Shutdown state
        self._shutdown_initiated = False
        self._shutdown_complete = False
        self._shutdown_start_time: Optional[float] = None
        
        # Callback management
        self._shutdown_callbacks: List[Callable[[], None]] = []
        self._callbacks_lock = threading.Lock()
        
        # Signal handling
        self._original_handlers = {}
        self._signals_installed = False
        
        logger.debug("GracefulShutdown initialized", timeout=shutdown_timeout)
    
    def register_shutdown_callback(self, callback: Callable[[], None]) -> None:
        """
        Register callback to be called during shutdown.
        
        Args:
            callback: Function to call during shutdown
        """
        if not callable(callback):
            raise ValueError("Callback must be callable")
        
        with self._callbacks_lock:
            self._shutdown_callbacks.append(callback)
        
        logger.debug("Shutdown callback registered", 
                    total_callbacks=len(self._shutdown_callbacks))
    
    def unregister_shutdown_callback(self, callback: Callable[[], None]) -> bool:
        """
        Unregister shutdown callback.
        
        Args:
            callback: Previously registered callback
            
        Returns:
            True if callback was found and removed, False otherwise
        """
        with self._callbacks_lock:
            try:
                self._shutdown_callbacks.remove(callback)
                logger.debug("Shutdown callback unregistered")
                return True
            except ValueError:
                logger.warning("Callback not found for unregistration")
                return False
    
    def install_signal_handlers(self) -> None:
        """Install signal handlers for graceful shutdown."""
        if self._signals_installed:
            logger.warning("Signal handlers already installed")
            return
        
        try:
            # Signals to handle for graceful shutdown
            shutdown_signals = [signal.SIGTERM, signal.SIGINT]
            
            # On Windows, SIGTERM might not be available
            if hasattr(signal, 'SIGTERM'):
                shutdown_signals.append(signal.SIGTERM)
            
            for sig in shutdown_signals:
                try:
                    # Store original handler
                    original_handler = signal.signal(sig, self._signal_handler)
                    self._original_handlers[sig] = original_handler
                    logger.debug("Signal handler installed", signal=sig.name)
                except (ValueError, OSError) as e:
                    # Some signals might not be available on all platforms
                    logger.warning("Could not install signal handler", 
                                 signal=sig.name, error=str(e))
            
            self._signals_installed = True
            logger.info("Signal handlers installed for graceful shutdown")
            
        except Exception as e:
            logger.error("Failed to install signal handlers", error=str(e))
            raise RuntimeError(f"Signal handler installation failed: {e}") from e
    
    def restore_signal_handlers(self) -> None:
        """Restore original signal handlers."""
        if not self._signals_installed:
            return
        
        try:
            for sig, original_handler in self._original_handlers.items():
                signal.signal(sig, original_handler)
                logger.debug("Signal handler restored", signal=sig.name)
            
            self._original_handlers.clear()
            self._signals_installed = False
            
            logger.debug("All signal handlers restored")
            
        except Exception as e:
            logger.error("Error restoring signal handlers", error=str(e))
    
    def _signal_handler(self, signum: int, frame) -> None:
        """
        Handle shutdown signals.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_name = signal.Signals(signum).name
        logger.info("Shutdown signal received", signal=signal_name)
        
        # Initiate shutdown if not already started
        if not self._shutdown_initiated:
            self.initiate_shutdown()
        else:
            logger.warning("Shutdown already in progress", signal=signal_name)
    
    def initiate_shutdown(self) -> None:
        """Initiate graceful shutdown process."""
        if self._shutdown_initiated:
            logger.warning("Shutdown already initiated")
            return
        
        logger.info("Initiating graceful shutdown")
        self._shutdown_initiated = True
        self._shutdown_start_time = time.time()
        
        # Start shutdown in separate thread to avoid blocking signal handler
        shutdown_thread = threading.Thread(
            target=self._execute_shutdown,
            name="GracefulShutdown",
            daemon=True
        )
        shutdown_thread.start()
    
    def _execute_shutdown(self) -> None:
        """Execute shutdown callbacks with timeout protection."""
        try:
            logger.info("Executing shutdown callbacks", 
                       count=len(self._shutdown_callbacks),
                       timeout=self.shutdown_timeout)
            
            start_time = time.time()
            
            # Execute callbacks in reverse order (LIFO)
            with self._callbacks_lock:
                callbacks = list(reversed(self._shutdown_callbacks))
            
            for i, callback in enumerate(callbacks):
                try:
                    # Check if we have time remaining
                    elapsed = time.time() - start_time
                    if elapsed >= self.shutdown_timeout:
                        logger.warning("Shutdown timeout reached, skipping remaining callbacks",
                                     executed=i, remaining=len(callbacks) - i)
                        break
                    
                    logger.debug("Executing shutdown callback", index=i)
                    callback()
                    logger.debug("Shutdown callback completed", index=i)
                    
                except Exception as e:
                    logger.error("Shutdown callback failed", index=i, error=str(e))
                    # Continue with other callbacks even if one fails
            
            self._shutdown_complete = True
            total_time = time.time() - start_time
            
            logger.info("Graceful shutdown completed", 
                       total_time_seconds=f"{total_time:.2f}")
            
        except Exception as e:
            logger.error("Shutdown execution failed", error=str(e))
            self._shutdown_complete = True
    
    def wait_for_shutdown(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for shutdown to complete.
        
        Args:
            timeout: Maximum time to wait, defaults to shutdown_timeout
            
        Returns:
            True if shutdown completed, False if timeout
        """
        if timeout is None:
            timeout = self.shutdown_timeout
        
        start_time = time.time()
        
        while not self._shutdown_complete:
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                logger.warning("Timeout waiting for shutdown completion")
                return False
            
            time.sleep(0.1)  # Brief sleep to avoid busy waiting
        
        logger.debug("Shutdown completion confirmed")
        return True
    
    def force_shutdown(self) -> None:
        """Force immediate shutdown without waiting for callbacks."""
        logger.warning("Forcing immediate shutdown")
        
        self._shutdown_initiated = True
        self._shutdown_complete = True
        
        # Restore signal handlers
        self.restore_signal_handlers()
        
        logger.warning("Forced shutdown completed")
    
    def is_shutdown_initiated(self) -> bool:
        """Check if shutdown has been initiated."""
        return self._shutdown_initiated
    
    def is_shutdown_complete(self) -> bool:
        """Check if shutdown has completed."""
        return self._shutdown_complete
    
    def get_shutdown_time_remaining(self) -> float:
        """
        Get remaining time before forced shutdown.
        
        Returns:
            Remaining time in seconds, 0 if no shutdown in progress
        """
        if not self._shutdown_initiated or self._shutdown_start_time is None:
            return 0.0
        
        elapsed = time.time() - self._shutdown_start_time
        remaining = max(0.0, self.shutdown_timeout - elapsed)
        
        return remaining
    
    def get_stats(self) -> dict:
        """
        Get shutdown handler statistics.
        
        Returns:
            Dictionary containing shutdown statistics
        """
        stats = {
            'shutdown_initiated': self._shutdown_initiated,
            'shutdown_complete': self._shutdown_complete,
            'shutdown_timeout': self.shutdown_timeout,
            'registered_callbacks': len(self._shutdown_callbacks),
            'signals_installed': self._signals_installed,
            'monitored_signals': list(self._original_handlers.keys()) if self._signals_installed else []
        }
        
        if self._shutdown_initiated and self._shutdown_start_time:
            stats['shutdown_elapsed_seconds'] = time.time() - self._shutdown_start_time
            stats['shutdown_time_remaining'] = self.get_shutdown_time_remaining()
        
        return stats
    
    def cleanup(self) -> None:
        """Cleanup shutdown handler resources."""
        logger.debug("Cleaning up shutdown handler")
        
        # Clear callbacks
        with self._callbacks_lock:
            self._shutdown_callbacks.clear()
        
        # Restore signal handlers
        self.restore_signal_handlers()
        
        logger.debug("Shutdown handler cleanup completed")
    
    def __enter__(self):
        """Context manager entry."""
        self.install_signal_handlers()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if not self._shutdown_initiated:
            self.initiate_shutdown()
            self.wait_for_shutdown()
        
        self.cleanup()
    
    def __del__(self):
        """Cleanup on object destruction."""
        try:
            self.cleanup()
        except:
            pass  # Avoid exceptions during garbage collection