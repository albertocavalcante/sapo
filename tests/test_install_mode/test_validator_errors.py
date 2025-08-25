"""Tests for validator custom exception classes."""

import pytest

from sapo.cli.install_mode.validator.errors import ConfigurationError, ValidationError


class TestValidationError:
    """Test the ValidationError exception class."""

    def test_initialization_basic(self):
        """Test basic initialization with message only."""
        message = "Validation failed"
        error = ValidationError(message)

        assert str(error) == message
        assert error.errors == []

    def test_initialization_with_errors_list(self):
        """Test initialization with message and errors list."""
        message = "Multiple validation errors occurred"
        errors = ["Error 1", "Error 2", "Error 3"]

        error = ValidationError(message, errors)

        assert str(error) == message
        assert error.errors == errors
        assert len(error.errors) == 3

    def test_initialization_with_none_errors(self):
        """Test initialization with None errors (should default to empty list)."""
        message = "Validation failed"
        error = ValidationError(message, None)

        assert str(error) == message
        assert error.errors == []

    def test_initialization_with_empty_errors(self):
        """Test initialization with empty errors list."""
        message = "Validation failed"
        error = ValidationError(message, [])

        assert str(error) == message
        assert error.errors == []

    def test_inheritance_from_exception(self):
        """Test that ValidationError properly inherits from Exception."""
        error = ValidationError("Test message")

        assert isinstance(error, Exception)
        assert isinstance(error, ValidationError)

    def test_raising_and_catching(self):
        """Test raising and catching ValidationError."""
        message = "Custom validation error"
        errors = ["Field A is required", "Field B is invalid"]

        with pytest.raises(ValidationError) as exc_info:
            raise ValidationError(message, errors)

        caught_error = exc_info.value
        assert str(caught_error) == message
        assert caught_error.errors == errors

    def test_errors_attribute_modification(self):
        """Test that the errors attribute can be modified after initialization."""
        error = ValidationError("Test")

        # Add errors after creation
        error.errors.append("New error 1")
        error.errors.append("New error 2")

        assert len(error.errors) == 2
        assert "New error 1" in error.errors
        assert "New error 2" in error.errors

    def test_with_different_error_types(self):
        """Test ValidationError with different types of errors."""
        # Mix of strings and other types
        mixed_errors = [
            "String error",
            {"field": "value", "error": "Invalid value"},
            123,
            None,
        ]

        error = ValidationError("Mixed error types", mixed_errors)

        assert len(error.errors) == 4
        assert error.errors[0] == "String error"
        assert error.errors[1] == {"field": "value", "error": "Invalid value"}
        assert error.errors[2] == 123
        assert error.errors[3] is None

    def test_empty_message(self):
        """Test ValidationError with empty message."""
        error = ValidationError("")

        assert str(error) == ""
        assert error.errors == []

    def test_message_with_special_characters(self):
        """Test ValidationError with message containing special characters."""
        message = "Validation failed: 'key.nested' must be of type str, got int"
        error = ValidationError(message)

        assert str(error) == message

    def test_repr_string(self):
        """Test string representation of ValidationError."""
        message = "Test error message"
        errors = ["Error 1", "Error 2"]
        error = ValidationError(message, errors)

        # Basic check that repr works and contains the message
        repr_str = repr(error)
        assert "ValidationError" in repr_str
        assert message in repr_str


class TestConfigurationError:
    """Test the ConfigurationError exception class."""

    def test_initialization_basic(self):
        """Test basic initialization with message only."""
        message = "Configuration is invalid"
        error = ConfigurationError(message)

        assert str(error) == message

    def test_initialization_no_message(self):
        """Test initialization without message."""
        error = ConfigurationError()

        assert str(error) == ""

    def test_inheritance_from_exception(self):
        """Test that ConfigurationError properly inherits from Exception."""
        error = ConfigurationError("Test message")

        assert isinstance(error, Exception)
        assert isinstance(error, ConfigurationError)

    def test_raising_and_catching(self):
        """Test raising and catching ConfigurationError."""
        message = "Invalid configuration structure"

        with pytest.raises(ConfigurationError) as exc_info:
            raise ConfigurationError(message)

        caught_error = exc_info.value
        assert str(caught_error) == message

    def test_different_message_types(self):
        """Test ConfigurationError with different message types."""
        # Test with string
        error1 = ConfigurationError("String message")
        assert str(error1) == "String message"

        # Test with None (should work but convert to string)
        error2 = ConfigurationError(None)
        assert str(error2) == "None"

        # Test with number
        error3 = ConfigurationError(12345)
        assert str(error3) == "12345"

    def test_empty_string_message(self):
        """Test ConfigurationError with empty string message."""
        error = ConfigurationError("")

        assert str(error) == ""

    def test_multiline_message(self):
        """Test ConfigurationError with multiline message."""
        message = """Configuration error occurred:
        - Missing required field 'database.url'
        - Invalid field 'database.port'"""

        error = ConfigurationError(message)

        assert str(error) == message
        assert "Missing required field" in str(error)
        assert "Invalid field" in str(error)

    def test_message_with_special_characters(self):
        """Test ConfigurationError with message containing special characters."""
        message = "Config error: field 'shared.security.joinKey' has invalid format"
        error = ConfigurationError(message)

        assert str(error) == message

    def test_repr_string(self):
        """Test string representation of ConfigurationError."""
        message = "Test configuration error"
        error = ConfigurationError(message)

        # Basic check that repr works and contains the message
        repr_str = repr(error)
        assert "ConfigurationError" in repr_str
        assert message in repr_str


class TestErrorsInteraction:
    """Test interaction between different error types."""

    def test_different_error_types_can_coexist(self):
        """Test that different error types can be used together."""
        validation_errors = ["Field A invalid", "Field B missing"]

        try:
            # Raise ValidationError
            raise ValidationError("Validation failed", validation_errors)
        except ValidationError as ve:
            # Caught ValidationError, now raise ConfigurationError
            try:
                raise ConfigurationError("Configuration structure is wrong")
            except ConfigurationError as ce:
                # Both exceptions should be different types
                assert type(ve) is not type(ce)
                assert isinstance(ve, ValidationError)
                assert isinstance(ce, ConfigurationError)
                assert ve.errors == validation_errors
                assert str(ce) == "Configuration structure is wrong"

    def test_both_inherit_from_exception(self):
        """Test that both error types inherit from Exception."""
        validation_error = ValidationError("Validation failed")
        config_error = ConfigurationError("Config failed")

        assert isinstance(validation_error, Exception)
        assert isinstance(config_error, Exception)

        # They should be catchable by Exception
        errors_caught = []

        for error in [validation_error, config_error]:
            try:
                raise error
            except Exception as e:
                errors_caught.append(type(e).__name__)

        assert "ValidationError" in errors_caught
        assert "ConfigurationError" in errors_caught

    def test_can_catch_specific_error_types(self):
        """Test that specific error types can be caught independently."""

        def raise_validation_error():
            raise ValidationError("Validation failed", ["Error 1"])

        def raise_configuration_error():
            raise ConfigurationError("Config failed")

        # Catch ValidationError specifically
        with pytest.raises(ValidationError) as ve_info:
            raise_validation_error()

        assert len(ve_info.value.errors) == 1
        assert ve_info.value.errors[0] == "Error 1"

        # Catch ConfigurationError specifically
        with pytest.raises(ConfigurationError) as ce_info:
            raise_configuration_error()

        assert str(ce_info.value) == "Config failed"
