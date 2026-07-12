"""
Exception Hierarchy for SEO/GEO Framework.
Provides comprehensive error handling with categorization and retry logic.
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List


class SEOFrameworkError(Exception):
    """Base exception for all SEO/GEO framework errors.
    
    Attributes:
        message: Human-readable error description
        error_code: Unique error code in format [Category][3-digit-number]
        details: Additional context about the error
        timestamp: UTC timestamp when error occurred
        retryable: Whether the operation can be safely retried
    """
    error_code_prefix: str = "SE"
    retryable: bool = False
    
    def __init__(
        self, 
        message: str, 
        error_code: str = "SE000", 
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization."""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
            "retryable": self.retryable
        }
    
    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r}, error_code={self.error_code!r})"


# ============================================================================
# Operational Errors (OP prefix)
# ============================================================================

class OperationalError(SEOFrameworkError):
    """Errors in framework operations.
    
    Base class for errors that occur during normal framework operation
    that are not related to data or security issues.
    """
    error_code_prefix: str = "OP"


class ConfigurationError(OperationalError):
    """Configuration-related errors.
    
    Raised when framework configuration is missing, invalid, or
    cannot be loaded properly.
    """
    error_code_prefix: str = "CF"
    
    def __init__(
        self, 
        message: str, 
        config_key: Optional[str] = None,
        error_code: str = "CF001",
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if config_key:
            details["config_key"] = config_key
        super().__init__(message, error_code, details)


class FatalError(OperationalError):
    """Fatal errors requiring manual intervention.
    
    These errors cannot be automatically recovered and require
    human intervention to resolve.
    """
    error_code_prefix: str = "FT"
    retryable: bool = False
    
    def __init__(
        self, 
        message: str, 
        error_code: str = "FT001",
        recovery_steps: Optional[List[str]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if recovery_steps:
            details["recovery_steps"] = recovery_steps
        super().__init__(message, error_code, details)


# ============================================================================
# Data Errors (DA prefix)
# ============================================================================

class DataError(SEOFrameworkError):
    """Errors related to data processing.
    
    Base class for errors that occur during data validation,
    transformation, or processing operations.
    """
    error_code_prefix: str = "DA"


class ValidationError(DataError):
    """Data validation failures.
    
    Raised when input data fails validation rules.
    """
    error_code_prefix: str = "VL"
    
    def __init__(
        self, 
        message: str, 
        field: Optional[str] = None,
        value: Optional[Any] = None,
        error_code: str = "VL001",
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if field:
            details["field"] = field
        if value is not None:
            details["invalid_value"] = str(value)[:200]  # Truncate long values
        super().__init__(message, error_code, details)


class SchemaValidationError(ValidationError):
    """Schema.org validation errors.
    
    Raised when structured data does not conform to Schema.org
    specifications or framework schema requirements.
    """
    error_code_prefix: str = "SC"
    
    def __init__(
        self, 
        message: str, 
        schema_type: Optional[str] = None,
        validation_errors: Optional[List[Dict[str, Any]]] = None,
        error_code: str = "SC001",
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if schema_type:
            details["schema_type"] = schema_type
        if validation_errors:
            details["validation_errors"] = validation_errors
        super().__init__(message, error_code=error_code, details=details)


class DataIntegrityError(DataError):
    """Data integrity violations.
    
    Raised when data corruption or integrity issues are detected.
    """
    error_code_prefix: str = "DI"
    
    def __init__(
        self, 
        message: str, 
        table: Optional[str] = None,
        record_id: Optional[str] = None,
        error_code: str = "DI001",
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if table:
            details["table"] = table
        if record_id:
            details["record_id"] = record_id
        super().__init__(message, error_code, details)


# ============================================================================
# Security Errors (SE prefix)
# ============================================================================

class SecurityError(SEOFrameworkError):
    """Security-related errors.
    
    Base class for security violations, authentication failures,
    and authorization issues.
    """
    error_code_prefix: str = "SX"
    retryable: bool = False
    
    def __init__(
        self, 
        message: str, 
        error_code: str = "SX001",
        details: Optional[Dict[str, Any]] = None
    ):
        # Sanitize details to prevent logging sensitive data
        sanitized_details = self._sanitize_details(details or {})
        super().__init__(message, error_code, sanitized_details)
    
    def _sanitize_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive information from details."""
        sensitive_keys = {"password", "token", "secret", "api_key", "credential"}
        return {
            k: "[REDACTED]" if k.lower() in sensitive_keys else v
            for k, v in details.items()
        }


class AuthenticationError(SecurityError):
    """Authentication failures.
    
    Raised when authentication credentials are invalid or expired.
    """
    error_code_prefix: str = "AU"
    
    def __init__(
        self, 
        message: str = "Authentication failed",
        auth_type: Optional[str] = None,
        error_code: str = "AU001",
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if auth_type:
            details["auth_type"] = auth_type
        super().__init__(message, error_code, details)


class AuthorizationError(SecurityError):
    """Authorization failures.
    
    Raised when user/service lacks required permissions.
    """
    error_code_prefix: str = "AZ"
    
    def __init__(
        self, 
        message: str = "Access denied",
        required_permission: Optional[str] = None,
        error_code: str = "AZ001",
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if required_permission:
            details["required_permission"] = required_permission
        super().__init__(message, error_code, details)


class InputSanitizationError(SecurityError):
    """Input sanitization failures.
    
    Raised when potentially malicious input is detected.
    """
    error_code_prefix: str = "IS"
    
    def __init__(
        self, 
        message: str = "Invalid input detected",
        input_type: Optional[str] = None,
        error_code: str = "IS001",
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if input_type:
            details["input_type"] = input_type
        # Never include the actual malicious input
        super().__init__(message, error_code, details)


# ============================================================================
# Transient Errors (TR prefix) - Retryable
# ============================================================================

class TransientError(SEOFrameworkError):
    """Transient errors that may be retried.
    
    Base class for errors that are temporary and the operation
    may succeed if retried after a delay.
    """
    error_code_prefix: str = "TR"
    retryable: bool = True
    
    def __init__(
        self, 
        message: str, 
        error_code: str = "TR001",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if retry_after is not None:
            details["retry_after_seconds"] = retry_after
        self.retry_after = retry_after
        super().__init__(message, error_code, details)


class RateLimitError(TransientError):
    """API rate limit exceeded.
    
    Raised when an external API rate limit is hit.
    """
    error_code_prefix: str = "RL"
    
    def __init__(
        self, 
        message: str = "Rate limit exceeded",
        service: Optional[str] = None,
        retry_after: int = 60,
        limit: Optional[int] = None,
        error_code: str = "RL001",
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if service:
            details["service"] = service
        if limit is not None:
            details["rate_limit"] = limit
        super().__init__(message, error_code, retry_after, details)


class NetworkError(TransientError):
    """Network connectivity issues.
    
    Raised when network operations fail due to connectivity problems.
    """
    error_code_prefix: str = "NW"
    
    def __init__(
        self, 
        message: str = "Network error occurred",
        endpoint: Optional[str] = None,
        retry_after: int = 5,
        error_code: str = "NW001",
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if endpoint:
            details["endpoint"] = endpoint
        super().__init__(message, error_code, retry_after, details)


class TimeoutError(TransientError):
    """Operation timeout errors.
    
    Raised when an operation exceeds its allowed time limit.
    """
    error_code_prefix: str = "TO"
    
    def __init__(
        self, 
        message: str = "Operation timed out",
        operation: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        retry_after: int = 10,
        error_code: str = "TO001",
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if operation:
            details["operation"] = operation
        if timeout_seconds is not None:
            details["timeout_seconds"] = timeout_seconds
        super().__init__(message, error_code, retry_after, details)


class ServiceUnavailableError(TransientError):
    """External service unavailable.
    
    Raised when an external service is temporarily unavailable.
    """
    error_code_prefix: str = "SU"
    
    def __init__(
        self, 
        message: str = "Service temporarily unavailable",
        service: Optional[str] = None,
        retry_after: int = 30,
        error_code: str = "SU001",
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if service:
            details["service"] = service
        super().__init__(message, error_code, retry_after, details)


# ============================================================================
# Helper Functions
# ============================================================================

def is_retryable_error(error: Exception) -> bool:
    """Check if an error is retryable.
    
    Args:
        error: The exception to check
        
    Returns:
        True if the error can be safely retried, False otherwise
    """
    if isinstance(error, SEOFrameworkError):
        return getattr(error, "retryable", False)
    
    # Check for standard library exceptions that are typically retryable
    retryable_types = (
        ConnectionError,
        TimeoutError,
        OSError,
    )
    return isinstance(error, retryable_types)


def get_error_category(error: Exception) -> str:
    """Get the error category for an exception.
    
    Args:
        error: The exception to categorize
        
    Returns:
        Category string: "operational", "data", "security", "transient", or "unknown"
    """
    if isinstance(error, FatalError):
        return "fatal"
    elif isinstance(error, OperationalError):
        return "operational"
    elif isinstance(error, DataError):
        return "data"
    elif isinstance(error, SecurityError):
        return "security"
    elif isinstance(error, TransientError):
        return "transient"
    elif isinstance(error, SEOFrameworkError):
        return "framework"
    else:
        return "unknown"


def format_error_for_logging(error: Exception) -> Dict[str, Any]:
    """Format an exception for structured logging.
    
    Args:
        error: The exception to format
        
    Returns:
        Dictionary containing structured error information
    """
    if isinstance(error, SEOFrameworkError):
        base_dict = error.to_dict()
        base_dict["category"] = get_error_category(error)
        base_dict["is_retryable"] = is_retryable_error(error)
        return base_dict
    
    # Handle standard Python exceptions
    return {
        "error_type": error.__class__.__name__,
        "error_code": "PY000",
        "message": str(error),
        "details": {},
        "timestamp": datetime.utcnow().isoformat(),
        "category": get_error_category(error),
        "is_retryable": is_retryable_error(error),
        "retryable": is_retryable_error(error)
    }


def get_retry_delay(error: Exception, attempt: int = 1) -> int:
    """Calculate retry delay with exponential backoff.
    
    Args:
        error: The exception that triggered the retry
        attempt: Current attempt number (1-indexed)
        
    Returns:
        Delay in seconds before next retry
    """
    base_delay = 1
    max_delay = 300  # 5 minutes max
    
    if isinstance(error, RateLimitError) and error.retry_after:
        return min(error.retry_after, max_delay)
    
    if isinstance(error, TransientError) and error.retry_after:
        base_delay = error.retry_after
    
    # Exponential backoff: base * 2^(attempt-1)
    delay = base_delay * (2 ** (attempt - 1))
    return min(delay, max_delay)


# ============================================================================
# Exception Aliases for Common Cases
# ============================================================================

__all__ = [
    # Base
    "SEOFrameworkError",
    
    # Operational
    "OperationalError",
    "ConfigurationError",
    "FatalError",
    
    # Data
    "DataError",
    "ValidationError",
    "SchemaValidationError",
    "DataIntegrityError",
    
    # Security
    "SecurityError",
    "AuthenticationError",
    "AuthorizationError",
    "InputSanitizationError",
    
    # Transient
    "TransientError",
    "RateLimitError",
    "NetworkError",
    "TimeoutError",
    "ServiceUnavailableError",
    
    # Helpers
    "is_retryable_error",
    "get_error_category",
    "format_error_for_logging",
    "get_retry_delay",
]
