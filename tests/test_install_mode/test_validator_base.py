"""Tests for base validator classes and data structures."""

import pytest

from sapo.cli.install_mode.validator.base import BaseValidator, ValidationResult


class TestValidationResult:
    """Test the ValidationResult dataclass."""

    def test_initialization_empty(self):
        """Test initialization with empty lists."""
        result = ValidationResult(errors=[], warnings=[])

        assert result.errors == []
        assert result.warnings == []
        assert result.is_valid is True

    def test_initialization_with_data(self):
        """Test initialization with data."""
        errors = ["Error 1", "Error 2"]
        warnings = ["Warning 1"]

        result = ValidationResult(errors=errors, warnings=warnings)

        assert result.errors == errors
        assert result.warnings == warnings
        assert result.is_valid is False

    def test_is_valid_property(self):
        """Test is_valid property logic."""
        # Valid when no errors
        result = ValidationResult(errors=[], warnings=["Warning"])
        assert result.is_valid is True

        # Invalid when errors exist
        result = ValidationResult(errors=["Error"], warnings=[])
        assert result.is_valid is False

        # Invalid when both errors and warnings exist
        result = ValidationResult(errors=["Error"], warnings=["Warning"])
        assert result.is_valid is False

    def test_add_error(self):
        """Test adding error messages."""
        result = ValidationResult(errors=[], warnings=[])

        result.add_error("First error")
        assert result.errors == ["First error"]
        assert result.is_valid is False

        result.add_error("Second error")
        assert result.errors == ["First error", "Second error"]
        assert result.is_valid is False

    def test_add_warning(self):
        """Test adding warning messages."""
        result = ValidationResult(errors=[], warnings=[])

        result.add_warning("First warning")
        assert result.warnings == ["First warning"]
        assert result.is_valid is True  # Still valid with only warnings

        result.add_warning("Second warning")
        assert result.warnings == ["First warning", "Second warning"]
        assert result.is_valid is True


class ConcreteValidator(BaseValidator):
    """Concrete implementation of BaseValidator for testing."""

    def validate(self, config):
        """Simple validation implementation for testing."""
        result = ValidationResult(errors=[], warnings=[])

        if not config:
            result.add_error("Config cannot be empty")

        if "required_field" not in config:
            result.add_error("Missing required_field")

        return result


class TestBaseValidator:
    """Test the BaseValidator abstract class and its helper methods."""

    def test_abstract_validate_method(self):
        """Test that BaseValidator cannot be instantiated directly."""
        with pytest.raises(
            TypeError, match="Can't instantiate abstract class BaseValidator"
        ):
            BaseValidator()

    def test_concrete_implementation(self):
        """Test that concrete implementations work correctly."""
        validator = ConcreteValidator()

        # Test with empty config
        result = validator.validate({})
        assert result.is_valid is False
        assert "Config cannot be empty" in result.errors

        # Test with missing required field
        result = validator.validate({"some_field": "value"})
        assert result.is_valid is False
        assert "Missing required_field" in result.errors

        # Test with valid config
        result = validator.validate({"required_field": "value"})
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_key_exists_helper_simple_keys(self):
        """Test _key_exists helper method with simple keys."""
        validator = ConcreteValidator()

        config = {"existing_key": "value", "nested": {"key": "nested_value"}}

        # Test existing simple key
        assert validator._key_exists(config, "existing_key") is True

        # Test non-existing simple key
        assert validator._key_exists(config, "non_existing_key") is False

        # Test nested key
        assert validator._key_exists(config, "nested.key") is True

        # Test non-existing nested key
        assert validator._key_exists(config, "nested.non_existing") is False

    def test_key_exists_helper_deep_nesting(self):
        """Test _key_exists helper method with deep nesting."""
        validator = ConcreteValidator()

        config = {"level1": {"level2": {"level3": {"deep_key": "deep_value"}}}}

        # Test deep nested path
        assert validator._key_exists(config, "level1.level2.level3.deep_key") is True

        # Test partial paths
        assert validator._key_exists(config, "level1") is True
        assert validator._key_exists(config, "level1.level2") is True
        assert validator._key_exists(config, "level1.level2.level3") is True

        # Test non-existing deep path
        assert (
            validator._key_exists(config, "level1.level2.level3.non_existing") is False
        )
        assert (
            validator._key_exists(config, "level1.level2.non_existing.deep_key")
            is False
        )

    def test_key_exists_helper_edge_cases(self):
        """Test _key_exists helper method with edge cases."""
        validator = ConcreteValidator()

        # Empty config
        assert validator._key_exists({}, "any_key") is False

        # None values
        config = {"key_with_none": None}
        assert validator._key_exists(config, "key_with_none") is True

        # Empty string key path
        assert validator._key_exists({"": "value"}, "") is True

        # Non-dict intermediate value
        config = {"key": "string_value"}
        assert validator._key_exists(config, "key.nested") is False

    def test_get_value_helper_simple_keys(self):
        """Test _get_value helper method with simple keys."""
        validator = ConcreteValidator()

        config = {"simple_key": "simple_value", "nested": {"key": "nested_value"}}

        # Test existing simple key
        assert validator._get_value(config, "simple_key") == "simple_value"

        # Test existing nested key
        assert validator._get_value(config, "nested.key") == "nested_value"

        # Test non-existing key
        assert validator._get_value(config, "non_existing") is None

    def test_get_value_helper_deep_nesting(self):
        """Test _get_value helper method with deep nesting."""
        validator = ConcreteValidator()

        config = {
            "level1": {
                "level2": {
                    "level3": {"deep_key": "deep_value", "number": 42, "boolean": True}
                }
            }
        }

        # Test deep nested values of different types
        assert (
            validator._get_value(config, "level1.level2.level3.deep_key")
            == "deep_value"
        )
        assert validator._get_value(config, "level1.level2.level3.number") == 42
        assert validator._get_value(config, "level1.level2.level3.boolean") is True

        # Test partial paths returning dict
        expected_level3 = {"deep_key": "deep_value", "number": 42, "boolean": True}
        assert validator._get_value(config, "level1.level2.level3") == expected_level3

    def test_get_value_helper_edge_cases(self):
        """Test _get_value helper method with edge cases."""
        validator = ConcreteValidator()

        # Empty config
        assert validator._get_value({}, "any_key") is None

        # None values
        config = {"key_with_none": None}
        assert validator._get_value(config, "key_with_none") is None

        # Empty string key path
        config = {"": "empty_key_value"}
        assert validator._get_value(config, "") == "empty_key_value"

        # List values
        config = {"list_key": [1, 2, 3]}
        assert validator._get_value(config, "list_key") == [1, 2, 3]

        # Non-dict intermediate value
        config = {"key": "string_value"}
        assert validator._get_value(config, "key.nested") is None

    def test_find_keys_recursive_functionality(self):
        """Test the _find_keys_recursive helper method functionality."""
        validator = ConcreteValidator()

        config = {
            "level1": "value1",
            "nested": {"level2": "value2", "deep": {"level3": "value3"}},
        }

        keys = list(validator._find_keys_recursive(config))

        expected_keys = [
            "level1",
            "nested",
            "nested.level2",
            "nested.deep",
            "nested.deep.level3",
        ]
        assert set(keys) == set(expected_keys)

    def test_find_keys_recursive_edge_cases(self):
        """Test _find_keys_recursive with edge cases."""
        validator = ConcreteValidator()

        # Empty dict
        assert validator._find_keys_recursive({}) == []

        # Non-dict input
        assert validator._find_keys_recursive("string") == []
        assert validator._find_keys_recursive(123) == []
        assert validator._find_keys_recursive(None) == []

        # Dict with mixed value types
        config = {
            "string": "value",
            "number": 42,
            "list": [1, 2, 3],
            "nested": {"inner": "nested_value"},
            "none_value": None,
        }

        keys = validator._find_keys_recursive(config)
        expected_keys = [
            "string",
            "number",
            "list",
            "nested",
            "nested.inner",
            "none_value",
        ]
        assert set(keys) == set(expected_keys)
