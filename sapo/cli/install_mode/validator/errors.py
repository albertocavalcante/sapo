"""Custom exceptions for configuration validation."""

from typing import List, Optional, Any


class ValidationError(Exception):
    """Raised when configuration validation fails."""

    def __init__(self, message: str, errors: Optional[List[Any]] = None):
        """Initialize validation error.

        Args:
            message: Error message
            errors: List of specific validation errors
        """
        super().__init__(message)
        self.errors = errors or []


class ConfigurationError(Exception):
    """Raised when configuration structure is invalid."""

    pass
