"""
Error mapping and handling for worker pool integration.

This module provides the ErrorMapper class for categorizing,
mapping, and handling errors across the worker pool system with support for:
- Error categorization and classification
- Error mapping to user-friendly messages
- Error recovery strategies
- Error reporting and aggregation
- Integration with external error handling systems
"""

import re
from typing import Dict, List, Any, Optional, Union, Callable, Pattern
from dataclasses import dataclass
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class ErrorCategory(Enum):
    """Categories for classifying errors."""
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    RESOURCE = "resource"
    TIMEOUT = "timeout"
    PARSING = "parsing"
    VALIDATION = "validation"
    CONFIGURATION = "configuration"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """Severity levels for errors."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorMapping:
    """Mapping definition for error patterns."""
    pattern: Union[str, Pattern]
    category: ErrorCategory
    severity: ErrorSeverity
    user_message: str
    recovery_action: Optional[str] = None
    retryable: bool = False
    max_retries: int = 0


@dataclass
class MappedError:
    """Mapped error with categorization and handling information."""
    original_error: str
    category: ErrorCategory
    severity: ErrorSeverity
    user_message: str
    technical_details: str
    recovery_action: Optional[str] = None
    retryable: bool = False
    suggested_retry_delay: Optional[float] = None
    error_code: Optional[str] = None


class ErrorMapper:
    """
    Mapper for categorizing and handling errors across the worker pool system.
    
    Provides comprehensive error classification, user-friendly messaging,
    and recovery strategy recommendations.
    """
    
    def __init__(self):
        """Initialize error mapper with default mappings."""
        self.error_mappings: List[ErrorMapping] = []
        self.custom_mappings: List[ErrorMapping] = []
        
        # Error change callbacks
        self.mapping_callbacks: List[Callable[[MappedError], None]] = []
        
        # Initialize default mappings
        self._initialize_default_mappings()
        
        logger.info("ErrorMapper initialized", 
                   default_mappings=len(self.error_mappings))
    
    def _initialize_default_mappings(self) -> None:
        """Initialize default error mappings."""
        default_mappings = [
            # Network errors
            ErrorMapping(
                pattern=r"(?i)(connection refused|connection reset|network is unreachable|no route to host)",
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.HIGH,
                user_message="Network connection failed. Please check your internet connection.",
                recovery_action="Check network connectivity and try again.",
                retryable=True,
                max_retries=3
            ),
            ErrorMapping(
                pattern=r"(?i)(timeout|timed out|connection timeout)",
                category=ErrorCategory.TIMEOUT,
                severity=ErrorSeverity.MEDIUM,
                user_message="Operation timed out. The server may be busy.",
                recovery_action="Wait a moment and try again.",
                retryable=True,
                max_retries=2
            ),
            ErrorMapping(
                pattern=r"(?i)(dns|name resolution|host not found)",
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.MEDIUM,
                user_message="Unable to resolve server address. Please check the URL.",
                recovery_action="Verify the server URL is correct.",
                retryable=False
            ),
            
            # Authentication errors
            ErrorMapping(
                pattern=r"(?i)(unauthorized|authentication failed|invalid credentials|login failed)",
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.HIGH,
                user_message="Authentication failed. Please check your login credentials.",
                recovery_action="Verify username and password are correct.",
                retryable=False
            ),
            ErrorMapping(
                pattern=r"(?i)(session expired|session timeout|please log in again)",
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.MEDIUM,
                user_message="Your session has expired. Please log in again.",
                recovery_action="Re-authenticate and retry the operation.",
                retryable=True,
                max_retries=1
            ),
            
            # Permission errors
            ErrorMapping(
                pattern=r"(?i)(permission denied|access denied|forbidden|403)",
                category=ErrorCategory.PERMISSION,
                severity=ErrorSeverity.HIGH,
                user_message="Access denied. You may not have permission for this operation.",
                recovery_action="Contact your administrator for access permissions.",
                retryable=False
            ),
            ErrorMapping(
                pattern=r"(?i)(insufficient privileges|not authorized)",
                category=ErrorCategory.PERMISSION,
                severity=ErrorSeverity.MEDIUM,
                user_message="Insufficient permissions for this operation.",
                recovery_action="Request additional permissions from your administrator.",
                retryable=False
            ),
            
            # Resource errors
            ErrorMapping(
                pattern=r"(?i)(out of memory|memory error|insufficient memory)",
                category=ErrorCategory.RESOURCE,
                severity=ErrorSeverity.CRITICAL,
                user_message="System ran out of memory. Please free up system resources.",
                recovery_action="Close other applications and try again.",
                retryable=True,
                max_retries=1
            ),
            ErrorMapping(
                pattern=r"(?i)(disk full|no space left|insufficient disk space)",
                category=ErrorCategory.RESOURCE,
                severity=ErrorSeverity.CRITICAL,
                user_message="Disk storage is full. Please free up disk space.",
                recovery_action="Delete unnecessary files and try again.",
                retryable=False
            ),
            
            # Parsing errors
            ErrorMapping(
                pattern=r"(?i)(invalid format|parsing error|malformed|syntax error)",
                category=ErrorCategory.PARSING,
                severity=ErrorSeverity.MEDIUM,
                user_message="Data format is invalid. Please check the input file.",
                recovery_action="Verify the file format matches the expected structure.",
                retryable=False
            ),
            ErrorMapping(
                pattern=r"(?i)(encoding error|charset|unicode)",
                category=ErrorCategory.PARSING,
                severity=ErrorSeverity.LOW,
                user_message="File encoding issue detected.",
                recovery_action="Save the file with UTF-8 encoding and try again.",
                retryable=False
            ),
            
            # Validation errors
            ErrorMapping(
                pattern=r"(?i)(validation failed|invalid data|required field)",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                user_message="Data validation failed. Please check your input.",
                recovery_action="Review and correct the input data.",
                retryable=False
            ),
            
            # Configuration errors
            ErrorMapping(
                pattern=r"(?i)(configuration error|config not found|missing setting)",
                category=ErrorCategory.CONFIGURATION,
                severity=ErrorSeverity.MEDIUM,
                user_message="Configuration issue detected.",
                recovery_action="Check configuration files and settings.",
                retryable=False
            ),
            
            # Browser/WebDriver errors
            ErrorMapping(
                pattern=r"(?i)(webdriver|chrome|firefox|safari|browser)",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                user_message="Browser automation error occurred.",
                recovery_action="Restart the application or check browser installation.",
                retryable=True,
                max_retries=2
            ),
            
            # System errors
            ErrorMapping(
                pattern=r"(?i)(system error|internal error|unexpected error)",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                user_message="An unexpected system error occurred.",
                recovery_action="Contact technical support if the problem persists.",
                retryable=True,
                max_retries=1
            )
        ]
        
        self.error_mappings.extend(default_mappings)
    
    def add_mapping_callback(self, callback: Callable[[MappedError], None]) -> None:
        """
        Add callback for mapped errors.
        
        Args:
            callback: Function called when errors are mapped
        """
        self.mapping_callbacks.append(callback)
        logger.debug("Error mapping callback added")
    
    def remove_mapping_callback(self, callback: Callable[[MappedError], None]) -> None:
        """
        Remove error mapping callback.
        
        Args:
            callback: Callback function to remove
        """
        if callback in self.mapping_callbacks:
            self.mapping_callbacks.remove(callback)
            logger.debug("Error mapping callback removed")
    
    def add_custom_mapping(self, mapping: ErrorMapping) -> None:
        """
        Add custom error mapping.
        
        Args:
            mapping: Custom error mapping to add
        """
        self.custom_mappings.append(mapping)
        logger.debug("Custom error mapping added", category=mapping.category.value)
    
    def remove_custom_mapping(self, mapping: ErrorMapping) -> None:
        """
        Remove custom error mapping.
        
        Args:
            mapping: Custom error mapping to remove
        """
        if mapping in self.custom_mappings:
            self.custom_mappings.remove(mapping)
            logger.debug("Custom error mapping removed", category=mapping.category.value)
    
    def map_error(self, error_message: str, context: Optional[Dict[str, Any]] = None) -> MappedError:
        """
        Map an error message to categorized error information.
        
        Args:
            error_message: The original error message
            context: Optional context information
            
        Returns:
            MappedError with categorization and handling information
        """
        # Try custom mappings first
        for mapping in self.custom_mappings:
            if self._matches_pattern(error_message, mapping.pattern):
                return self._create_mapped_error(error_message, mapping, context)
        
        # Try default mappings
        for mapping in self.error_mappings:
            if self._matches_pattern(error_message, mapping.pattern):
                return self._create_mapped_error(error_message, mapping, context)
        
        # Default to unknown error
        return self._create_unknown_error(error_message, context)
    
    def _matches_pattern(self, error_message: str, pattern: Union[str, Pattern]) -> bool:
        """Check if error message matches a pattern."""
        if isinstance(pattern, str):
            return pattern.lower() in error_message.lower()
        else:
            return bool(pattern.search(error_message))
    
    def _create_mapped_error(self, error_message: str, mapping: ErrorMapping, 
                           context: Optional[Dict[str, Any]] = None) -> MappedError:
        """Create a MappedError from an ErrorMapping."""
        # Generate error code
        error_code = f"{mapping.category.value.upper()}_{mapping.severity.value.upper()}"
        
        # Calculate retry delay based on severity
        retry_delay = None
        if mapping.retryable:
            base_delay = 1.0
            if mapping.severity == ErrorSeverity.HIGH:
                base_delay = 5.0
            elif mapping.severity == ErrorSeverity.CRITICAL:
                base_delay = 30.0
            retry_delay = base_delay
        
        mapped_error = MappedError(
            original_error=error_message,
            category=mapping.category,
            severity=mapping.severity,
            user_message=mapping.user_message,
            technical_details=error_message,
            recovery_action=mapping.recovery_action,
            retryable=mapping.retryable,
            suggested_retry_delay=retry_delay,
            error_code=error_code
        )
        
        # Notify callbacks
        self._notify_callbacks(mapped_error)
        
        return mapped_error
    
    def _create_unknown_error(self, error_message: str, 
                            context: Optional[Dict[str, Any]] = None) -> MappedError:
        """Create a MappedError for unknown errors."""
        mapped_error = MappedError(
            original_error=error_message,
            category=ErrorCategory.UNKNOWN,
            severity=ErrorSeverity.MEDIUM,
            user_message="An unexpected error occurred. Please contact support if this persists.",
            technical_details=error_message,
            recovery_action="Try the operation again, or contact technical support.",
            retryable=True,
            suggested_retry_delay=5.0,
            error_code="UNKNOWN_MEDIUM"
        )
        
        # Notify callbacks
        self._notify_callbacks(mapped_error)
        
        return mapped_error
    
    def _notify_callbacks(self, mapped_error: MappedError) -> None:
        """Notify callbacks of mapped error."""
        for callback in self.mapping_callbacks:
            try:
                callback(mapped_error)
            except Exception as e:
                logger.warning("Error mapping callback failed", error=str(e))
    
    def get_error_summary(self, errors: List[MappedError]) -> Dict[str, Any]:
        """
        Generate summary statistics for a list of errors.
        
        Args:
            errors: List of MappedError instances
            
        Returns:
            Dictionary with error summary statistics
        """
        if not errors:
            return {
                'total_errors': 0,
                'categories': {},
                'severities': {},
                'retryable_count': 0,
                'most_common_category': None,
                'highest_severity': None
            }
        
        category_counts = {}
        severity_counts = {}
        retryable_count = 0
        highest_severity = ErrorSeverity.LOW
        
        for error in errors:
            # Count categories
            cat_key = error.category.value
            category_counts[cat_key] = category_counts.get(cat_key, 0) + 1
            
            # Count severities
            sev_key = error.severity.value
            severity_counts[sev_key] = severity_counts.get(sev_key, 0) + 1
            
            # Count retryable
            if error.retryable:
                retryable_count += 1
            
            # Track highest severity
            if self._severity_level(error.severity) > self._severity_level(highest_severity):
                highest_severity = error.severity
        
        # Find most common category
        most_common_category = max(category_counts.items(), key=lambda x: x[1])[0] if category_counts else None
        
        return {
            'total_errors': len(errors),
            'categories': category_counts,
            'severities': severity_counts,
            'retryable_count': retryable_count,
            'most_common_category': most_common_category,
            'highest_severity': highest_severity.value
        }
    
    def _severity_level(self, severity: ErrorSeverity) -> int:
        """Get numeric level for severity comparison."""
        levels = {
            ErrorSeverity.LOW: 1,
            ErrorSeverity.MEDIUM: 2,
            ErrorSeverity.HIGH: 3,
            ErrorSeverity.CRITICAL: 4
        }
        return levels.get(severity, 0)
    
    def suggest_recovery_strategy(self, mapped_error: MappedError) -> Dict[str, Any]:
        """
        Suggest recovery strategy for a mapped error.
        
        Args:
            mapped_error: The mapped error
            
        Returns:
            Dictionary with recovery strategy information
        """
        strategy = {
            'immediate_action': mapped_error.recovery_action,
            'retry_recommended': mapped_error.retryable,
            'retry_delay_seconds': mapped_error.suggested_retry_delay,
            'escalation_required': False,
            'contact_support': False
        }
        
        # Adjust strategy based on severity and category
        if mapped_error.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            strategy['escalation_required'] = True
            
        if mapped_error.category in [ErrorCategory.PERMISSION, ErrorCategory.CONFIGURATION]:
            strategy['contact_support'] = True
            
        if mapped_error.category == ErrorCategory.RESOURCE:
            strategy['immediate_action'] = "Free up system resources and restart the application."
            
        return strategy
    
    def batch_map_errors(self, error_messages: List[str], 
                        context: Optional[Dict[str, Any]] = None) -> List[MappedError]:
        """
        Map multiple error messages in batch.
        
        Args:
            error_messages: List of error messages to map
            context: Optional context information
            
        Returns:
            List of MappedError instances
        """
        mapped_errors = []
        for error_msg in error_messages:
            mapped_error = self.map_error(error_msg, context)
            mapped_errors.append(mapped_error)
        
        logger.debug("Batch error mapping completed", 
                    error_count=len(error_messages),
                    mapped_count=len(mapped_errors))
        
        return mapped_errors
    
    def get_error_patterns(self) -> List[Dict[str, Any]]:
        """
        Get all error patterns for inspection.
        
        Returns:
            List of error pattern dictionaries
        """
        patterns = []
        
        for mapping in self.error_mappings + self.custom_mappings:
            pattern_dict = {
                'pattern': str(mapping.pattern),
                'category': mapping.category.value,
                'severity': mapping.severity.value,
                'user_message': mapping.user_message,
                'recovery_action': mapping.recovery_action,
                'retryable': mapping.retryable,
                'max_retries': mapping.max_retries
            }
            patterns.append(pattern_dict)
        
        return patterns
    
    def create_regex_mapping(self, pattern: str, category: ErrorCategory,
                           severity: ErrorSeverity, user_message: str,
                           **kwargs) -> ErrorMapping:
        """
        Create a regex-based error mapping.
        
        Args:
            pattern: Regex pattern string
            category: Error category
            severity: Error severity
            user_message: User-friendly message
            **kwargs: Additional ErrorMapping parameters
            
        Returns:
            ErrorMapping instance
        """
        compiled_pattern = re.compile(pattern, re.IGNORECASE)
        
        mapping = ErrorMapping(
            pattern=compiled_pattern,
            category=category,
            severity=severity,
            user_message=user_message,
            **kwargs
        )
        
        return mapping
    
    def export_mappings(self, file_path: str) -> None:
        """
        Export error mappings to JSON file.
        
        Args:
            file_path: Path to export file
        """
        import json
        
        mappings_data = self.get_error_patterns()
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(mappings_data, f, indent=2, ensure_ascii=False)
            
            logger.info("Error mappings exported", file=file_path)
            
        except Exception as e:
            logger.error("Failed to export error mappings", 
                        file=file_path, error=str(e))
            raise
    
    def import_mappings(self, file_path: str) -> int:
        """
        Import error mappings from JSON file.
        
        Args:
            file_path: Path to import file
            
        Returns:
            Number of mappings imported
        """
        import json
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                mappings_data = json.load(f)
            
            imported_count = 0
            for mapping_dict in mappings_data:
                # Convert string values back to enums
                category = ErrorCategory(mapping_dict['category'])
                severity = ErrorSeverity(mapping_dict['severity'])
                
                # Create mapping
                mapping = ErrorMapping(
                    pattern=mapping_dict['pattern'],
                    category=category,
                    severity=severity,
                    user_message=mapping_dict['user_message'],
                    recovery_action=mapping_dict.get('recovery_action'),
                    retryable=mapping_dict.get('retryable', False),
                    max_retries=mapping_dict.get('max_retries', 0)
                )
                
                self.custom_mappings.append(mapping)
                imported_count += 1
            
            logger.info("Error mappings imported", 
                       file=file_path, count=imported_count)
            
            return imported_count
            
        except Exception as e:
            logger.error("Failed to import error mappings", 
                        file=file_path, error=str(e))
            raise