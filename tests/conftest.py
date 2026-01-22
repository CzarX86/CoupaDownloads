"""
Test configuration and fixtures for core interface tests.

This module provides shared test infrastructure for testing the three core interfaces:
ConfigurationManager, ProcessingController, and StatusManager.
"""

import pytest
import sys
from pathlib import Path
from typing import Dict, Any

# Add src to path for imports
project_root = Path(__file__).resolve().parents[1]
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
    print(f"CONFTEST LOADED: Added {src_path} to sys.path")
    print(f"Current sys.path: {[p for p in sys.path if 'CoupaDownloads' in p]}")


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def sample_config_dict() -> Dict[str, Any]:
    """Sample configuration dictionary for testing."""
    return {
        "headless_mode": True,
        "enable_parallel": True,
        "max_workers": 4,
        "download_folder": "/tmp/downloads",
        "input_file_path": "/tmp/input.csv",
        "csv_enabled": True,
        "csv_path": "/tmp/input.csv"
    }


@pytest.fixture
def invalid_config_dict() -> Dict[str, Any]:
    """Invalid configuration dictionary for testing error cases."""
    return {
        "headless_mode": "not_a_boolean",
        "enable_parallel": 123,
        "max_workers": -1,
        "download_folder": "",  # Empty path
        "input_file_path": "/nonexistent/path",
    }


@pytest.fixture
def minimal_config_dict() -> Dict[str, Any]:
    """Minimal valid configuration dictionary."""
    return {
        "headless_mode": False,
        "enable_parallel": False,
        "max_workers": 1,
        "download_folder": "/tmp",
        "input_file_path": "/tmp/test.csv",
    }


@pytest.fixture
def mock_status_callback():
    """Mock status callback for testing."""
    def callback(update):
        callback.calls.append(update)
    callback.calls = []
    return callback


# =============================================================================
# TEST UTILITIES
# =============================================================================

def assert_config_dict_format(config: Dict[str, Any]) -> None:
    """
    Assert that a configuration dictionary follows the expected format.

    Args:
        config: Configuration dictionary to validate.

    Raises:
        AssertionError: If config doesn't match expected format.
    """
    required_keys = {
        "headless_mode", "enable_parallel", "max_workers",
        "download_folder", "input_file_path"
    }

    assert isinstance(config, dict), "Config must be a dictionary"
    assert required_keys.issubset(config.keys()), f"Missing required keys: {required_keys - config.keys()}"

    # Type checks
    assert isinstance(config["headless_mode"], bool), "headless_mode must be bool"
    assert isinstance(config["enable_parallel"], bool), "enable_parallel must be bool"
    assert isinstance(config["max_workers"], int), "max_workers must be int"
    assert isinstance(config["download_folder"], str), "download_folder must be str"
    assert isinstance(config["input_file_path"], str), "input_file_path must be str"

    # Value checks
    assert config["max_workers"] >= 1, "max_workers must be >= 1"
    assert config["download_folder"].strip(), "download_folder cannot be empty"
    assert config["input_file_path"].strip(), "input_file_path cannot be empty"


def assert_validation_result_format(result: Dict[str, Any]) -> None:
    """
    Assert that a validation result follows the expected format.

    Args:
        result: Validation result dictionary to validate.

    Raises:
        AssertionError: If result doesn't match expected format.
    """
    assert isinstance(result, dict), "Validation result must be a dictionary"
    assert "valid" in result, "Validation result must have 'valid' key"
    assert isinstance(result["valid"], bool), "'valid' must be bool"

    if "errors" in result:
        assert isinstance(result["errors"], list), "'errors' must be list"
        assert all(isinstance(e, str) for e in result["errors"]), "All errors must be strings"

    if "warnings" in result:
        assert isinstance(result["warnings"], list), "'warnings' must be list"
        assert all(isinstance(w, str) for w in result["warnings"]), "All warnings must be strings"


def assert_status_dict_format(status: Dict[str, Any]) -> None:
    """
    Assert that a status dictionary follows the expected format.

    Args:
        status: Status dictionary to validate.

    Raises:
        AssertionError: If status doesn't match expected format.
    """
    required_keys = {"session_id", "status", "total_tasks", "completed_tasks", "failed_tasks"}

    assert isinstance(status, dict), "Status must be a dictionary"
    assert required_keys.issubset(status.keys()), f"Missing required keys: {required_keys - status.keys()}"

    # Type checks
    assert isinstance(status["session_id"], (str, type(None))), "session_id must be str or None"
    assert isinstance(status["status"], str), "status must be str"
    assert isinstance(status["total_tasks"], int), "total_tasks must be int"
    assert isinstance(status["completed_tasks"], int), "completed_tasks must be int"
    assert isinstance(status["failed_tasks"], int), "failed_tasks must be int"

    # Value checks
    assert status["total_tasks"] >= 0, "total_tasks must be >= 0"
    assert status["completed_tasks"] >= 0, "completed_tasks must be >= 0"
    assert status["failed_tasks"] >= 0, "failed_tasks must be >= 0"
    assert status["completed_tasks"] + status["failed_tasks"] <= status["total_tasks"], "completed + failed cannot exceed total"


# =============================================================================
# PYTEST CONFIGURATION
# =============================================================================

@pytest.fixture(autouse=True)
def clean_imports():
    """Clean up any cached imports between tests."""
    # This helps ensure test isolation
    modules_to_clean = [
        'src.core.config_interface',
        'src.core.processing_controller',
        'src.core.status_manager',
    ]

    for module in modules_to_clean:
        if module in sys.modules:
            del sys.modules[module]