"""Validator for Artifactory OSS configuration."""

from typing import Any

from .base import BaseValidator, ValidationResult


class ArtifactoryOSSValidator(BaseValidator):
    """Validates system.yaml for OSS compatibility."""

    # Keys that are not supported in OSS version
    INVALID_OSS_KEYS = {
        "artifactory.primary",
        "artifactory.pool",
        "artifactory.javaOpts",
        "artifactory.network",
        "artifactory.cache",
        "artifactory.security",
        "artifactory.access",
        "shared.database.properties",
    }

    # Required keys with their expected types
    REQUIRED_KEYS: dict[str, type[Any] | tuple[type[Any], ...]] = {
        "configVersion": (int, float),
        "shared.security.joinKey": str,
        "shared.node.id": str,
        "shared.database.type": str,
    }

    # Optional but recommended keys
    RECOMMENDED_KEYS: dict[str, type[Any] | tuple[type[Any], ...]] = {
        "shared.node.ip": str,
        "shared.node.haEnabled": bool,
        "shared.database.driver": str,
        "shared.database.url": str,
        "shared.database.username": str,
        "shared.database.password": str,
    }

    def validate(self, config: dict[str, Any]) -> ValidationResult:
        """Validate configuration for OSS edition.

        Args:
            config: Configuration dictionary to validate

        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult(errors=[], warnings=[])

        # Check for invalid keys
        self._check_invalid_keys(config, result)

        # Check required keys
        self._check_required_keys(config, result)

        # Check recommended keys
        self._check_recommended_keys(config, result)

        # Validate specific values
        self._validate_values(config, result)

        return result

    def _check_invalid_keys(
        self, config: dict[str, Any], result: ValidationResult
    ) -> None:
        """Check for keys that are invalid in OSS version."""
        all_keys = set(self._find_keys_recursive(config))

        for invalid_key in self.INVALID_OSS_KEYS:
            # Check both exact match and prefix match
            matching_keys = [
                key
                for key in all_keys
                if key == invalid_key or key.startswith(f"{invalid_key}.")
            ]

            for key in matching_keys:
                result.add_error(
                    f"Key '{key}' is not supported in OSS version. "
                    "This key is only available in Pro/Enterprise editions."
                )

    def _check_required_keys(
        self, config: dict[str, Any], result: ValidationResult
    ) -> None:
        """Check that all required keys are present."""
        for key_path, expected_types in self.REQUIRED_KEYS.items():
            if not self._key_exists(config, key_path):
                result.add_error(f"Required key '{key_path}' is missing")
            else:
                # Validate type
                value = self._get_value(config, key_path)
                if value is not None and not isinstance(value, expected_types):
                    if isinstance(expected_types, tuple):
                        type_names = " or ".join(t.__name__ for t in expected_types)
                    else:
                        type_names = expected_types.__name__
                    result.add_error(
                        f"Key '{key_path}' must be of type {type_names}, "
                        f"got {type(value).__name__}"
                    )

    def _check_recommended_keys(
        self, config: dict[str, Any], result: ValidationResult
    ) -> None:
        """Check for recommended keys and add warnings if missing."""
        for key_path, expected_type in self.RECOMMENDED_KEYS.items():
            if not self._key_exists(config, key_path):
                result.add_warning(
                    f"Recommended key '{key_path}' is missing. "
                    "This may affect functionality."
                )

    def _validate_values(
        self, config: dict[str, Any], result: ValidationResult
    ) -> None:
        """Validate specific configuration values."""
        # Validate configVersion
        config_version = self._get_value(config, "configVersion")
        if config_version is not None and config_version != 1:
            result.add_warning(
                f"configVersion {config_version} may not be fully supported. "
                "Version 1 is recommended for OSS."
            )

        # Validate database type
        db_type = self._get_value(config, "shared.database.type")
        if db_type and db_type not in ["postgresql", "derby"]:
            result.add_error(
                f"Database type '{db_type}' is not supported. "
                "Use 'postgresql' or 'derby'."
            )

        # Validate joinKey format
        join_key = self._get_value(config, "shared.security.joinKey")
        if join_key and not self._is_valid_join_key(join_key):
            result.add_error(
                "Invalid joinKey format. It should be an encrypted string "
                "in the format: 'prefix.algorithm.encryptedValue'"
            )

        # Check for PostgreSQL-specific requirements
        if db_type == "postgresql":
            pg_keys = [
                "shared.database.driver",
                "shared.database.url",
                "shared.database.username",
                "shared.database.password",
            ]
            for key in pg_keys:
                if not self._key_exists(config, key):
                    result.add_error(f"PostgreSQL requires '{key}' to be configured")

    def _is_valid_join_key(self, join_key: str | int | float | bool | None) -> bool:
        """Check if join key has valid format."""
        if not isinstance(join_key, str):
            return False

        # Join key should have format: prefix.algorithm.encryptedValue
        parts = join_key.split(".")
        return len(parts) >= 3 and all(part for part in parts)
