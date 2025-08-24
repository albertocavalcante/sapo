"""Base validator interface for configuration validation."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Union


@dataclass
class ValidationResult:
    """Result of configuration validation."""

    errors: List[str]
    warnings: List[str]

    @property
    def is_valid(self) -> bool:
        """Check if configuration is valid (no errors)."""
        return len(self.errors) == 0

    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)


class BaseValidator(ABC):
    """Base class for configuration validators."""

    @abstractmethod
    def validate(self, config: Dict[str, Any]) -> ValidationResult:
        """Validate configuration.

        Args:
            config: Configuration dictionary to validate

        Returns:
            ValidationResult with errors and warnings
        """
        pass

    def _key_exists(self, config: Dict[str, Any], key_path: str) -> bool:
        """Check if a nested key exists in configuration.

        Args:
            config: Configuration dictionary
            key_path: Dot-separated key path (e.g., 'shared.security.joinKey')

        Returns:
            True if key exists, False otherwise
        """
        keys = key_path.split(".")
        current = config

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return False

        return True

    def _get_value(self, config: Dict[str, Any], key_path: str) -> Optional[Any]:
        """Get value from nested key path.

        Args:
            config: Configuration dictionary
            key_path: Dot-separated key path

        Returns:
            Value if exists, None otherwise
        """
        keys = key_path.split(".")
        current = config

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None

        return current

    def _find_keys_recursive(
        self,
        config: Union[Dict[str, Any], str, int, float, bool, None],
        prefix: str = "",
    ) -> List[str]:
        """Recursively find all keys in configuration.

        Args:
            config: Configuration dictionary (or other simple value)
            prefix: Current key prefix

        Returns:
            List of all key paths in dot notation
        """
        keys: List[str] = []

        if not isinstance(config, dict):
            return keys

        for key, value in config.items():
            full_key = f"{prefix}.{key}" if prefix else key
            keys.append(full_key)

            if isinstance(value, dict):
                keys.extend(self._find_keys_recursive(value, full_key))

        return keys
