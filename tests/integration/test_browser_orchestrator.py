"""
Integration tests for BrowserOrchestrator.

Tests the browser orchestration layer with real browser initialization
(when possible) and comprehensive mocking.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import threading

from src.orchestrators.browser_orchestrator import BrowserOrchestrator
from src.lib.browser import BrowserManager


class TestBrowserOrchestratorInitialization:
    """Test BrowserOrchestrator initialization and basic operations."""

    def test_init_with_browser_manager(self) -> None:
        """Test orchestrator initializes with BrowserManager."""
        mock_browser_manager = Mock(spec=BrowserManager)
        orchestrator = BrowserOrchestrator(mock_browser_manager)

        assert orchestrator.browser_manager is mock_browser_manager
        assert orchestrator.driver is None
        assert orchestrator._initialized is False
        assert isinstance(orchestrator.lock, threading.Lock)

    def test_is_initialized_false_initially(self) -> None:
        """Test that orchestrator reports not initialized initially."""
        mock_browser_manager = Mock(spec=BrowserManager)
        orchestrator = BrowserOrchestrator(mock_browser_manager)

        assert orchestrator.is_initialized() is False

    def test_get_driver_none_initially(self) -> None:
        """Test that get_driver returns None initially."""
        mock_browser_manager = Mock(spec=BrowserManager)
        orchestrator = BrowserOrchestrator(mock_browser_manager)

        assert orchestrator.get_driver() is None


class TestBrowserOrchestratorInitialize:
    """Test browser initialization logic."""

    @patch.object(BrowserManager, 'initialize_driver')
    def test_initialize_browser_calls_browser_manager(
        self,
        mock_init_driver: Mock
    ) -> None:
        """Test that initialize_browser calls BrowserManager.initialize_driver."""
        mock_browser_manager = Mock(spec=BrowserManager)
        mock_browser_manager.driver = Mock()
        orchestrator = BrowserOrchestrator(mock_browser_manager)

        result = orchestrator.initialize_browser(headless=True)

        mock_init_driver.assert_called_once_with(headless=True)
        assert result is mock_browser_manager.driver
        assert orchestrator._initialized is True

    @patch.object(BrowserManager, 'initialize_driver')
    def test_initialize_browser_only_once(
        self,
        mock_init_driver: Mock
    ) -> None:
        """Test that browser is only initialized once."""
        mock_browser_manager = Mock(spec=BrowserManager)
        mock_browser_manager.driver = Mock()
        orchestrator = BrowserOrchestrator(mock_browser_manager)

        # Initialize twice
        orchestrator.initialize_browser(headless=True)
        orchestrator.initialize_browser(headless=False)

        # Should only be called once (first time)
        mock_init_driver.assert_called_once_with(headless=True)

    @patch.object(BrowserManager, 'initialize_driver')
    def test_initialize_browser_thread_safe(
        self,
        mock_init_driver: Mock
    ) -> None:
        """Test that initialization is thread-safe."""
        mock_browser_manager = Mock(spec=BrowserManager)
        mock_browser_manager.driver = Mock()
        orchestrator = BrowserOrchestrator(mock_browser_manager)

        # Simulate concurrent initialization attempts
        def try_initialize():
            orchestrator.initialize_browser(headless=True)

        threads = [threading.Thread(target=try_initialize) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should only initialize once despite concurrent calls
        mock_init_driver.assert_called_once()


class TestBrowserOrchestratorResponsive:
    """Test browser responsiveness checking."""

    def test_is_browser_responsive_false_when_not_initialized(self) -> None:
        """Test that responsiveness check returns False when not initialized."""
        mock_browser_manager = Mock(spec=BrowserManager)
        orchestrator = BrowserOrchestrator(mock_browser_manager)

        assert orchestrator.is_browser_responsive() is False

    def test_is_browser_responsive_true_when_driver_responsive(self) -> None:
        """Test responsiveness check with responsive driver."""
        mock_browser_manager = Mock(spec=BrowserManager)
        mock_driver = Mock()
        mock_driver.current_url = "https://example.com"
        orchestrator = BrowserOrchestrator(mock_browser_manager)
        orchestrator.driver = mock_driver
        orchestrator._initialized = True

        assert orchestrator.is_browser_responsive() is True

    def test_is_browser_responsive_false_when_driver_raises(self) -> None:
        """Test responsiveness check when driver raises exception."""
        mock_browser_manager = Mock(spec=BrowserManager)
        mock_driver = Mock()
        mock_driver.current_url = Mock(side_effect=Exception("Driver error"))
        orchestrator = BrowserOrchestrator(mock_browser_manager)
        orchestrator.driver = mock_driver
        orchestrator._initialized = True

        assert orchestrator.is_browser_responsive() is False


class TestBrowserOrchestratorCleanup:
    """Test browser cleanup operations."""

    @patch.object(BrowserManager, 'cleanup')
    def test_cleanup_closes_browser(
        self,
        mock_cleanup: Mock
    ) -> None:
        """Test that cleanup calls BrowserManager.cleanup."""
        mock_browser_manager = Mock(spec=BrowserManager)
        mock_browser_manager.driver = Mock()
        orchestrator = BrowserOrchestrator(mock_browser_manager)
        orchestrator.driver = Mock()
        orchestrator._initialized = True

        orchestrator.cleanup(emergency=False)

        mock_cleanup.assert_called_once()
        assert orchestrator.driver is None
        assert orchestrator._initialized is False

    @patch.object(BrowserManager, 'cleanup')
    def test_cleanup_noop_when_not_initialized(
        self,
        mock_cleanup: Mock
    ) -> None:
        """Test that cleanup is no-op when not initialized."""
        mock_browser_manager = Mock(spec=BrowserManager)
        orchestrator = BrowserOrchestrator(mock_browser_manager)

        orchestrator.cleanup(emergency=False)

        mock_cleanup.assert_not_called()

    @patch.object(BrowserManager, 'cleanup')
    def test_cleanup_emergency_continues_on_error(
        self,
        mock_cleanup: Mock
    ) -> None:
        """Test that emergency cleanup continues on error."""
        mock_browser_manager = Mock(spec=BrowserManager)
        mock_browser_manager.driver = Mock()
        mock_cleanup.side_effect = Exception("Cleanup error")
        orchestrator = BrowserOrchestrator(mock_browser_manager)
        orchestrator.driver = Mock()
        orchestrator._initialized = True

        # Should not raise in emergency mode
        orchestrator.cleanup(emergency=True)

        mock_cleanup.assert_called_once()


class TestBrowserOrchestratorExecuteWithLock:
    """Test thread-safe operation execution."""

    def test_execute_with_lock_calls_operation(self) -> None:
        """Test that execute_with_lock calls the operation."""
        mock_browser_manager = Mock(spec=BrowserManager)
        mock_driver = Mock()
        orchestrator = BrowserOrchestrator(mock_browser_manager)
        orchestrator.driver = mock_driver
        orchestrator._initialized = True

        operation = Mock(return_value="result")
        result = orchestrator.execute_with_lock(operation, "arg1", kwarg="value")

        operation.assert_called_once_with(mock_driver, "arg1", kwarg="value")
        assert result == "result"

    def test_execute_with_lock_raises_when_not_initialized(self) -> None:
        """Test that execute_with_lock raises when not initialized."""
        mock_browser_manager = Mock(spec=BrowserManager)
        orchestrator = BrowserOrchestrator(mock_browser_manager)

        operation = Mock()

        with pytest.raises(RuntimeError, match="Browser not initialized"):
            orchestrator.execute_with_lock(operation)


class TestBrowserOrchestratorUpdateDownloadDirectory:
    """Test download directory updates."""

    @patch.object(BrowserManager, 'update_download_directory')
    def test_update_download_directory_calls_browser_manager(
        self,
        mock_update: Mock
    ) -> None:
        """Test that update_download_directory calls BrowserManager."""
        mock_browser_manager = Mock(spec=BrowserManager)
        mock_browser_manager.driver = Mock()
        orchestrator = BrowserOrchestrator(mock_browser_manager)
        orchestrator.driver = Mock()

        orchestrator.update_download_directory("/path/to/downloads")

        mock_update.assert_called_once_with("/path/to/downloads")

    def test_update_download_directory_noop_when_not_initialized(self) -> None:
        """Test that update is no-op when not initialized."""
        mock_browser_manager = Mock(spec=BrowserManager)
        orchestrator = BrowserOrchestrator(mock_browser_manager)

        # Should not raise, just log warning
        orchestrator.update_download_directory("/path/to/downloads")


# Integration test with real BrowserManager (if browser available)
@pytest.mark.integration
class TestBrowserOrchestratorRealBrowser:
    """Integration tests with real browser (requires Edge installed)."""

    @pytest.mark.skip(reason="Requires Edge browser installed")
    def test_initialize_real_browser(self) -> None:
        """Test initializing a real browser."""
        browser_manager = BrowserManager()
        orchestrator = BrowserOrchestrator(browser_manager)

        try:
            driver = orchestrator.initialize_browser(headless=True)
            assert driver is not None
            assert orchestrator.is_initialized() is True
        finally:
            orchestrator.cleanup()

    @pytest.mark.skip(reason="Requires Edge browser installed")
    def test_browser_lifecycle(self) -> None:
        """Test complete browser lifecycle."""
        browser_manager = BrowserManager()
        orchestrator = BrowserOrchestrator(browser_manager)

        try:
            # Initialize
            driver = orchestrator.initialize_browser(headless=True)
            assert driver is not None

            # Check responsive
            assert orchestrator.is_browser_responsive() is True

            # Get driver
            assert orchestrator.get_driver() is driver

            # Cleanup
            orchestrator.cleanup()
            assert orchestrator.is_initialized() is False
        finally:
            # Ensure cleanup even if test fails
            try:
                orchestrator.cleanup()
            except Exception:
                pass
