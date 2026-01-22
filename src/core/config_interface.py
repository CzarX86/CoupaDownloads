"""
ConfigurationManager interface implementation.

Provides clean configuration management without exposing internal complexity.
All methods use only built-in types (dict, str, bool) for UI serialization compatibility.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import asdict

from .types import (
    ConfigurationManagerInterface,
    ConfigurationData,
    ConfigurationError,
)


class ConfigurationManager(ConfigurationManagerInterface):
    """
    Configuration manager for CoupaDownloads.

    Provides clean configuration management interface that wraps existing
    configuration systems without exposing internal complexity.
    """

    # Default configuration values
    DEFAULT_CONFIG = {
        "headless_mode": False,
        "enable_parallel": True,
        "max_workers": 4,
        "download_folder": "~/Downloads/CoupaDownloads",
        "input_file_path": "~/Downloads/input.xlsx",
        "csv_enabled": False,
        "csv_path": None,
    }

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize ConfigurationManager.

        Args:
            config_file: Path to configuration file. If None, uses default location.
        """
        self.config_file = config_file or self._get_default_config_path()
        self._config = self._load_config()

    def _get_default_config_path(self) -> str:
        """Get default configuration file path."""
        config_dir = Path.home() / ".coupadownloads"
        config_dir.mkdir(exist_ok=True)
        return str(config_dir / "config.json")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file, falling back to defaults."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)

                # Merge with defaults to ensure all keys exist
                config = self.DEFAULT_CONFIG.copy()
                config.update(loaded)
                return config
        except (json.JSONDecodeError, IOError) as e:
            # Log error but continue with defaults
            print(f"Warning: Failed to load config from {self.config_file}: {e}")

        return self.DEFAULT_CONFIG.copy()

    def _save_config_to_file(self, config: Dict[str, Any]) -> bool:
        """Save configuration to file."""
        try:
            # Ensure config directory exists
            config_path = Path(self.config_file)
            config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            return True
        except IOError as e:
            print(f"Error saving config to {self.config_file}: {e}")
            return False

    def get_config(self) -> Dict[str, Any]:
        """
        Get current configuration as a dictionary.

        Returns:
            Dictionary containing all configuration settings using only
            built-in types (dict, str, bool, int, float, list).
        """
        # Return a copy to prevent external modification
        return self._config.copy()

    def save_config(self, config: Dict[str, Any]) -> bool:
        """
        Save configuration from dictionary.

        Args:
            config: Dictionary with configuration settings.

        Returns:
            True if saved successfully, False otherwise.
        """
        # Validate before saving
        validation = self.validate_config(config)
        if not validation["valid"]:
            return False

        # Update internal config
        self._config = config.copy()

        # Save to file
        return self._save_config_to_file(config)

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate configuration dictionary.

        Args:
            config: Configuration dictionary to validate.

        Returns:
            Dictionary with validation results:
            {
                "valid": bool,
                "errors": List[str],  # Empty if valid
                "warnings": List[str]  # Optional warnings
            }
        """
        errors = []
        warnings = []

        # Required keys check
        required_keys = {"headless_mode", "enable_parallel", "max_workers", "download_folder", "input_file_path"}
        missing_keys = required_keys - config.keys()
        if missing_keys:
            errors.append(f"Missing required configuration keys: {', '.join(missing_keys)}")

        # Type validation
        if "headless_mode" in config and not isinstance(config["headless_mode"], bool):
            errors.append("headless_mode must be a boolean")

        if "enable_parallel" in config and not isinstance(config["enable_parallel"], bool):
            errors.append("enable_parallel must be a boolean")

        if "max_workers" in config:
            if not isinstance(config["max_workers"], int):
                errors.append("max_workers must be an integer")
            elif config["max_workers"] < 1:
                errors.append("max_workers must be >= 1")

        if "download_folder" in config:
            if not isinstance(config["download_folder"], str):
                errors.append("download_folder must be a string")
            elif not config["download_folder"].strip():
                errors.append("download_folder cannot be empty")
            else:
                # Check if path is valid (warning only)
                try:
                    expanded_path = os.path.expanduser(config["download_folder"])
                    if not os.path.exists(expanded_path):
                        warnings.append(f"download_folder path does not exist: {expanded_path}")
                except Exception:
                    warnings.append("download_folder contains invalid path characters")

        if "input_file_path" in config:
            if not isinstance(config["input_file_path"], str):
                errors.append("input_file_path must be a string")
            elif not config["input_file_path"].strip():
                errors.append("input_file_path cannot be empty")

        # Optional fields validation
        if "csv_enabled" in config and not isinstance(config["csv_enabled"], bool):
            errors.append("csv_enabled must be a boolean")

        if "csv_path" in config and config["csv_path"] is not None:
            if not isinstance(config["csv_path"], str):
                errors.append("csv_path must be a string or null")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def reset_to_defaults(self) -> bool:
        """
        Reset configuration to default values.

        Returns:
            True if reset successfully, False otherwise.
        """
        self._config = self.DEFAULT_CONFIG.copy()
        return self._save_config_to_file(self._config)