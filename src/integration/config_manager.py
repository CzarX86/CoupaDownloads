"""
Configuration manager for worker pool integration.

This module provides the ConfigurationManager class for managing
configuration settings across the worker pool system with support for:
- Hierarchical configuration loading
- Environment variable overrides
- Configuration validation
- Dynamic reconfiguration
- Configuration persistence
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, asdict
import structlog

from ..workers.models import PoolConfig

logger = structlog.get_logger(__name__)


@dataclass
class IntegrationConfig:
    """
    Configuration for integration adapters.
    
    Defines settings for CSV processing, result handling,
    progress tracking, and system integration.
    """
    
    # CSV/Excel processing
    csv_delimiter: str = ','
    csv_encoding: str = 'utf-8'
    excel_sheet_name: Union[str, int] = 0
    po_number_column: str = 'po_number'
    priority_column: str = 'priority'
    max_csv_rows: int = 10000
    
    # Result handling
    result_export_formats: Optional[List[str]] = None
    result_export_dir: str = 'results'
    auto_export_results: bool = True
    result_retention_days: int = 7
    
    # Progress tracking
    progress_update_interval: float = 1.0  # seconds
    enable_progress_file: bool = True
    progress_file_path: str = 'progress.json'
    max_progress_history: int = 1000
    
    # Error handling
    max_retry_attempts: int = 3
    retry_backoff_factor: float = 2.0
    error_notification_enabled: bool = False
    error_notification_email: Optional[str] = None
    
    # Performance tuning
    batch_size: int = 50
    max_concurrent_batches: int = 3
    processing_timeout_seconds: int = 300
    
    # Logging and monitoring
    log_level: str = 'INFO'
    enable_structured_logging: bool = True
    metrics_collection_enabled: bool = True
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.result_export_formats is None:
            self.result_export_formats = ['json', 'csv', 'summary']
        
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration values."""
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive")
        
        if self.max_concurrent_batches <= 0:
            raise ValueError("max_concurrent_batches must be positive")
        
        if self.processing_timeout_seconds <= 0:
            raise ValueError("processing_timeout_seconds must be positive")
        
        if self.result_retention_days < 0:
            raise ValueError("result_retention_days cannot be negative")
        
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.log_level.upper() not in valid_log_levels:
            raise ValueError(f"log_level must be one of {valid_log_levels}")


class ConfigurationManager:
    """
    Manager for configuration settings across the worker pool system.
    
    Provides centralized configuration management with validation,
    environment overrides, and dynamic updates.
    """
    
    def __init__(self, config_file: Optional[Union[str, Path]] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Path to configuration file (optional)
        """
        self.config_file = Path(config_file) if config_file else None
        self.integration_config = IntegrationConfig()
        self.pool_config = PoolConfig()
        
        # Configuration change callbacks
        self.change_callbacks: List[Callable[[str, Any, Any], None]] = []
        
        # Load configuration
        self._load_config()
        
        logger.info("ConfigurationManager initialized", 
                   config_file=str(self.config_file) if self.config_file else None)
    
    def add_change_callback(self, callback: Callable[[str, Any, Any], None]) -> None:
        """
        Add callback for configuration changes.
        
        Args:
            callback: Function called when config changes (key, old_value, new_value)
        """
        self.change_callbacks.append(callback)
        logger.debug("Configuration change callback added")
    
    def remove_change_callback(self, callback: Callable[[str, Any, Any], None]) -> None:
        """
        Remove configuration change callback.
        
        Args:
            callback: Callback function to remove
        """
        if callback in self.change_callbacks:
            self.change_callbacks.remove(callback)
            logger.debug("Configuration change callback removed")
    
    def _load_config(self) -> None:
        """Load configuration from file and environment."""
        # Load from file if specified
        if self.config_file and self.config_file.exists():
            self._load_from_file()
        
        # Override with environment variables
        self._load_from_environment()
        
        # Validate final configuration
        self._validate_all_configs()
    
    def _load_from_file(self) -> None:
        """Load configuration from JSON file."""
        if not self.config_file:
            return
            
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Load integration config
            integration_data = config_data.get('integration', {})
            for key, value in integration_data.items():
                if hasattr(self.integration_config, key):
                    setattr(self.integration_config, key, value)
            
            # Load pool config
            pool_data = config_data.get('worker_pool', {})
            for key, value in pool_data.items():
                if hasattr(self.pool_config, key):
                    setattr(self.pool_config, key, value)
            
            logger.info("Configuration loaded from file", 
                       file=str(self.config_file))
            
        except Exception as e:
            logger.warning("Failed to load configuration from file", 
                          file=str(self.config_file), error=str(e))
    
    def _load_from_environment(self) -> None:
        """Load configuration overrides from environment variables."""
        # Integration config environment variables
        env_mappings = {
            'COUPA_CSV_DELIMITER': ('integration_config', 'csv_delimiter'),
            'COUPA_CSV_ENCODING': ('integration_config', 'csv_encoding'),
            'COUPA_PO_COLUMN': ('integration_config', 'po_number_column'),
            'COUPA_PRIORITY_COLUMN': ('integration_config', 'priority_column'),
            'COUPA_BATCH_SIZE': ('integration_config', 'batch_size', int),
            'COUPA_MAX_WORKERS': ('pool_config', 'worker_count', int),
            'COUPA_MEMORY_THRESHOLD': ('pool_config', 'memory_threshold', float),
            'COUPA_LOG_LEVEL': ('integration_config', 'log_level'),
        }
        
        for env_var, (config_type, attr_name, *type_hint) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Convert type if specified
                if type_hint:
                    converter = type_hint[0]
                    try:
                        value = converter(value)
                    except ValueError:
                        logger.warning("Invalid environment variable value", 
                                     env_var=env_var, value=value)
                        continue
                
                # Set the value
                config_obj = getattr(self, config_type)
                old_value = getattr(config_obj, attr_name)
                setattr(config_obj, attr_name, value)
                
                logger.debug("Configuration set from environment", 
                           env_var=env_var, attr=f"{config_type}.{attr_name}", value=value)
    
    def _validate_all_configs(self) -> None:
        """Validate all configuration objects."""
        try:
            # Re-initialize dataclasses to trigger validation
            integration_dict = asdict(self.integration_config)
            self.integration_config = IntegrationConfig(**integration_dict)
            
            # PoolConfig validation is done in its __post_init__
            pool_dict = asdict(self.pool_config)
            self.pool_config = PoolConfig(**pool_dict)
            
        except Exception as e:
            logger.error("Configuration validation failed", error=str(e))
            raise
    
    def get_integration_config(self) -> IntegrationConfig:
        """Get integration configuration."""
        return self.integration_config
    
    def get_pool_config(self) -> PoolConfig:
        """Get worker pool configuration."""
        return self.pool_config
    
    def update_integration_config(self, updates: Dict[str, Any]) -> None:
        """
        Update integration configuration.
        
        Args:
            updates: Dictionary of configuration updates
        """
        old_values = {}
        for key, value in updates.items():
            if hasattr(self.integration_config, key):
                old_values[key] = getattr(self.integration_config, key)
                setattr(self.integration_config, key, value)
        
        # Validate and notify
        self._validate_all_configs()
        self._notify_changes('integration_config', old_values, updates)
        
        logger.info("Integration configuration updated", updates=updates)
    
    def update_pool_config(self, updates: Dict[str, Any]) -> None:
        """
        Update worker pool configuration.
        
        Args:
            updates: Dictionary of configuration updates
        """
        old_values = {}
        for key, value in updates.items():
            if hasattr(self.pool_config, key):
                old_values[key] = getattr(self.pool_config, key)
                setattr(self.pool_config, key, value)
        
        # Validate and notify
        self._validate_all_configs()
        self._notify_changes('pool_config', old_values, updates)
        
        logger.info("Pool configuration updated", updates=updates)
    
    def _notify_changes(self, config_type: str, old_values: Dict[str, Any], 
                       new_values: Dict[str, Any]) -> None:
        """Notify callbacks of configuration changes."""
        for key, new_value in new_values.items():
            old_value = old_values.get(key)
            if old_value != new_value:
                for callback in self.change_callbacks:
                    try:
                        callback(f"{config_type}.{key}", old_value, new_value)
                    except Exception as e:
                        logger.warning("Configuration change callback failed", 
                                     error=str(e))
    
    def save_config(self, file_path: Optional[Union[str, Path]] = None) -> None:
        """
        Save current configuration to file.
        
        Args:
            file_path: File path to save to (uses config_file if not specified)
        """
        save_path = Path(file_path) if file_path else self.config_file
        if not save_path:
            raise ValueError("No configuration file path specified")
        
        config_data = {
            'integration': asdict(self.integration_config),
            'worker_pool': asdict(self.pool_config),
            'metadata': {
                'saved_at': str(Path(__file__).parent),
                'version': '1.0.0'
            }
        }
        
        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            logger.info("Configuration saved", file=str(save_path))
            
        except Exception as e:
            logger.error("Failed to save configuration", 
                        file=str(save_path), error=str(e))
            raise
    
    def reload_config(self) -> None:
        """Reload configuration from file and environment."""
        logger.info("Reloading configuration")
        self._load_config()
    
    def get_all_config(self) -> Dict[str, Any]:
        """
        Get all configuration as dictionary.
        
        Returns:
            Dictionary containing all configuration
        """
        return {
            'integration': asdict(self.integration_config),
            'worker_pool': asdict(self.pool_config)
        }
    
    def validate_config(self) -> List[str]:
        """
        Validate current configuration.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        try:
            self._validate_all_configs()
        except Exception as e:
            errors.append(f"Configuration validation failed: {str(e)}")
        
        # Additional cross-config validation
        if self.integration_config.batch_size > self.pool_config.worker_count * 10:
            errors.append("Batch size seems too large compared to worker count")
        
        if self.integration_config.processing_timeout_seconds < 30:
            errors.append("Processing timeout is very short, may cause premature failures")
        
        return errors
    
    def create_default_config_file(self, file_path: Union[str, Path]) -> None:
        """
        Create a default configuration file.
        
        Args:
            file_path: Path to create the configuration file
        """
        file_path = Path(file_path)
        
        # Create default configs
        default_integration = IntegrationConfig()
        default_pool = PoolConfig()
        
        config_data = {
            'integration': asdict(default_integration),
            'worker_pool': asdict(default_pool),
            'metadata': {
                'description': 'Default Coupa Downloads configuration',
                'created_by': 'ConfigurationManager',
                'version': '1.0.0'
            }
        }
        
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            logger.info("Default configuration file created", file=str(file_path))
            
        except Exception as e:
            logger.error("Failed to create default configuration file", 
                        file=str(file_path), error=str(e))
            raise
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        Get configuration summary for monitoring.
        
        Returns:
            Dictionary with configuration summary
        """
        return {
            'integration': {
                'batch_size': self.integration_config.batch_size,
                'max_concurrent_batches': self.integration_config.max_concurrent_batches,
                'processing_timeout_seconds': self.integration_config.processing_timeout_seconds,
                'result_export_formats': self.integration_config.result_export_formats,
                'auto_export_results': self.integration_config.auto_export_results
            },
            'worker_pool': {
                'worker_count': self.pool_config.worker_count,
                'memory_threshold': self.pool_config.memory_threshold,
                'shutdown_timeout': self.pool_config.shutdown_timeout,
                'headless_mode': self.pool_config.headless_mode
            },
            'validation_errors': self.validate_config()
        }