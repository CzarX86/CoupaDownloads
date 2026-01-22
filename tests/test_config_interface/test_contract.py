"""
Contract tests for ConfigurationManager interface.

These tests verify that any implementation of ConfigurationManagerInterface
meets the expected contract. Tests should FAIL until the implementation is complete.

Tests are written against the abstract interface to ensure contract compliance.
"""

import pytest
import time
from typing import Dict, Any
from unittest.mock import Mock, patch

from src.core import ConfigurationManagerInterface, ConfigurationManager


# Test fixtures
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
    assert required_keys.issubset(config.keys()), f"Missing keys: {required_keys - config.keys()}"

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


class TestConfigurationManagerContract:
    """
    Contract tests for ConfigurationManager interface.

    These tests define the expected behavior of any ConfigurationManager implementation.
    All tests should initially fail until the concrete implementation is provided.
    """

    @pytest.fixture
    def config_manager(self) -> ConfigurationManagerInterface:
        """Concrete ConfigurationManager implementation for testing."""
        # This will fail until we implement ConfigurationManager
        from src.core.config_interface import ConfigurationManager
        return ConfigurationManager()

    def test_get_config_returns_dict(self, config_manager: ConfigurationManagerInterface):
        """Test that get_config returns a properly formatted dictionary."""
        config = config_manager.get_config()

        assert isinstance(config, dict), "get_config must return a dictionary"
        assert_config_dict_format(config)

    def test_get_config_contains_required_keys(self, config_manager: ConfigurationManagerInterface):
        """Test that get_config includes all required configuration keys."""
        config = config_manager.get_config()

        required_keys = {
            "headless_mode", "enable_parallel", "max_workers",
            "download_folder", "input_file_path"
        }

        assert required_keys.issubset(config.keys()), f"Missing keys: {required_keys - config.keys()}"

    def test_save_config_accepts_valid_dict(self, config_manager: ConfigurationManagerInterface, sample_config_dict: Dict[str, Any]):
        """Test that save_config accepts and returns success for valid config."""
        result = config_manager.save_config(sample_config_dict)

        assert isinstance(result, bool), "save_config must return boolean"
        assert result is True, "save_config should return True for valid config"

    def test_save_config_rejects_invalid_dict(self, config_manager: ConfigurationManagerInterface, invalid_config_dict: Dict[str, Any]):
        """Test that save_config rejects invalid configuration."""
        result = config_manager.save_config(invalid_config_dict)

        assert isinstance(result, bool), "save_config must return boolean"
        assert result is False, "save_config should return False for invalid config"

    def test_validate_config_returns_proper_format(self, config_manager: ConfigurationManagerInterface, sample_config_dict: Dict[str, Any]):
        """Test that validate_config returns properly formatted validation result."""
        result = config_manager.validate_config(sample_config_dict)

        assert_validation_result_format(result)

    def test_validate_config_accepts_valid_config(self, config_manager: ConfigurationManagerInterface, sample_config_dict: Dict[str, Any]):
        """Test that validate_config accepts valid configuration."""
        result = config_manager.validate_config(sample_config_dict)

        assert result["valid"] is True, "Valid config should be accepted"
        assert "errors" not in result or len(result.get("errors", [])) == 0, "Valid config should have no errors"

    def test_validate_config_rejects_invalid_config(self, config_manager: ConfigurationManagerInterface, invalid_config_dict: Dict[str, Any]):
        """Test that validate_config rejects invalid configuration."""
        result = config_manager.validate_config(invalid_config_dict)

        assert result["valid"] is False, "Invalid config should be rejected"
        assert "errors" in result, "Invalid config should have errors"
        assert len(result["errors"]) > 0, "Invalid config should have at least one error"

    def test_reset_to_defaults_returns_bool(self, config_manager: ConfigurationManagerInterface):
        """Test that reset_to_defaults returns a boolean."""
        result = config_manager.reset_to_defaults()

        assert isinstance(result, bool), "reset_to_defaults must return boolean"

    def test_config_persistence_across_instances(self, config_manager: ConfigurationManagerInterface, sample_config_dict: Dict[str, Any]):
        """Test that configuration persists across different instances."""
        # Save config with first instance
        success = config_manager.save_config(sample_config_dict)
        assert success, "Should be able to save config"

        # Create new instance and check if config is loaded
        from src.core.config_interface import ConfigurationManager
        new_manager = ConfigurationManager()
        loaded_config = new_manager.get_config()

        # Compare key settings (exact match depends on implementation)
        assert loaded_config["headless_mode"] == sample_config_dict["headless_mode"]
        assert loaded_config["enable_parallel"] == sample_config_dict["enable_parallel"]
        assert loaded_config["max_workers"] == sample_config_dict["max_workers"]

    def test_config_validation_error_messages(self, config_manager: ConfigurationManagerInterface):
        """Test that validation provides meaningful error messages."""
        invalid_config = {
            "headless_mode": "not_a_boolean",
            "enable_parallel": 123,
            "max_workers": -1,
            "download_folder": "",
            "input_file_path": "/nonexistent/path",
        }

        result = config_manager.validate_config(invalid_config)

        assert result["valid"] is False
        assert "errors" in result
        assert len(result["errors"]) > 0

        # Check that error messages are strings and meaningful
        for error in result["errors"]:
            assert isinstance(error, str), "Error messages must be strings"
            assert len(error.strip()) > 0, "Error messages must not be empty"

    @pytest.mark.performance
    def test_get_config_performance(self, config_manager: ConfigurationManagerInterface):
        """Test that get_config meets performance requirements (< 100ms)."""
        start_time = time.perf_counter()

        for _ in range(10):  # Test multiple calls
            config = config_manager.get_config()
            assert isinstance(config, dict)

        end_time = time.perf_counter()
        avg_time = (end_time - start_time) / 10

        assert avg_time < 0.1, ".2f"  # SC-002: ConfigurationManager operations < 100ms

    @pytest.mark.performance
    def test_save_config_performance(self, config_manager: ConfigurationManagerInterface, minimal_config_dict: Dict[str, Any]):
        """Test that save_config meets performance requirements (< 100ms)."""
        start_time = time.perf_counter()

        for _ in range(10):  # Test multiple calls
            result = config_manager.save_config(minimal_config_dict)
            assert result is True

        end_time = time.perf_counter()
        avg_time = (end_time - start_time) / 10

        assert avg_time < 0.1, ".2f"  # SC-002: ConfigurationManager operations < 100ms

    def test_config_isolation_between_instances(self, config_manager: ConfigurationManagerInterface, minimal_config_dict: Dict[str, Any]):
        """Test that configuration changes don't affect other instances."""
        original_config = config_manager.get_config()

        # Modify config in a separate instance
        from src.core.config_interface import ConfigurationManager
        other_manager = ConfigurationManager()
        other_manager.save_config(minimal_config_dict)

        # Original instance should be unchanged
        current_config = config_manager.get_config()
        assert current_config == original_config, "Configuration should be isolated between instances"

    def test_minimal_config_sufficiency(self, config_manager: ConfigurationManagerInterface, minimal_config_dict: Dict[str, Any]):
        """Test that minimal configuration is sufficient for operation."""
        # Should be able to save and load minimal config
        success = config_manager.save_config(minimal_config_dict)
        assert success, "Minimal config should be acceptable"

        loaded = config_manager.get_config()
        assert loaded["max_workers"] == minimal_config_dict["max_workers"]
        assert loaded["headless_mode"] == minimal_config_dict["headless_mode"]