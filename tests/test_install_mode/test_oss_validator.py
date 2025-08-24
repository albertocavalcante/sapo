"""Tests for Artifactory OSS configuration validator."""

from sapo.cli.install_mode.validator.oss_validator import ArtifactoryOSSValidator


class TestArtifactoryOSSValidator:
    """Test the Artifactory OSS configuration validator."""

    def test_initialization(self):
        """Test validator initialization."""
        validator = ArtifactoryOSSValidator()

        # Check that constants are properly set
        assert isinstance(validator.INVALID_OSS_KEYS, set)
        assert isinstance(validator.REQUIRED_KEYS, dict)
        assert isinstance(validator.RECOMMENDED_KEYS, dict)

        # Verify some known invalid keys
        assert "artifactory.primary" in validator.INVALID_OSS_KEYS
        assert "artifactory.pool" in validator.INVALID_OSS_KEYS

        # Verify some required keys
        assert "configVersion" in validator.REQUIRED_KEYS
        assert "shared.security.joinKey" in validator.REQUIRED_KEYS

    def test_valid_minimal_config(self):
        """Test validation with minimal valid OSS configuration."""
        validator = ArtifactoryOSSValidator()

        config = {
            "configVersion": 1,
            "shared": {
                "security": {"joinKey": "valid.key.encrypted123"},
                "node": {"id": "node-1"},
                "database": {"type": "derby"},
            },
        }

        result = validator.validate(config)

        assert result.is_valid is True
        assert len(result.errors) == 0
        # May have warnings for missing recommended keys
        assert all("Recommended" in warning for warning in result.warnings)

    def test_valid_full_postgresql_config(self):
        """Test validation with full PostgreSQL configuration."""
        validator = ArtifactoryOSSValidator()

        config = {
            "configVersion": 1,
            "shared": {
                "security": {"joinKey": "artifactory.v1.encrypted_join_key_value"},
                "node": {
                    "id": "artifactory-node-1",
                    "ip": "192.168.1.100",
                    "haEnabled": False,
                },
                "database": {
                    "type": "postgresql",
                    "driver": "org.postgresql.Driver",
                    "url": "jdbc:postgresql://localhost:5432/artifactory",
                    "username": "artifactory",
                    "password": "password123",
                },
            },
        }

        result = validator.validate(config)

        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_invalid_oss_keys_error(self):
        """Test validation fails with invalid OSS keys."""
        validator = ArtifactoryOSSValidator()

        config = {
            "configVersion": 1,
            "shared": {
                "security": {"joinKey": "valid.key.encrypted123"},
                "node": {"id": "node-1"},
                "database": {"type": "derby"},
            },
            "artifactory": {
                "primary": True,  # Invalid for OSS
                "pool": {  # Invalid for OSS
                    "maxPoolSize": 100
                },
                "javaOpts": "-Xms1g",  # Invalid for OSS
            },
        }

        result = validator.validate(config)

        assert result.is_valid is False
        assert len(result.errors) >= 3

        # Check for specific error messages
        error_messages = " ".join(result.errors)
        assert "artifactory.primary" in error_messages
        assert "artifactory.pool" in error_messages
        assert "artifactory.javaOpts" in error_messages
        assert "OSS version" in error_messages

    def test_missing_required_keys_error(self):
        """Test validation fails with missing required keys."""
        validator = ArtifactoryOSSValidator()

        config = {
            "configVersion": 1,
            # Missing shared.security.joinKey
            # Missing shared.node.id
            # Missing shared.database.type
        }

        result = validator.validate(config)

        assert result.is_valid is False
        assert len(result.errors) == 3

        # Check for specific missing key errors
        error_messages = " ".join(result.errors)
        assert "shared.security.joinKey" in error_messages
        assert "shared.node.id" in error_messages
        assert "shared.database.type" in error_messages
        assert "missing" in error_messages.lower()

    def test_incorrect_required_key_types(self):
        """Test validation fails with incorrect types for required keys."""
        validator = ArtifactoryOSSValidator()

        config = {
            "configVersion": "1",  # Should be int/float, not string
            "shared": {
                "security": {
                    "joinKey": 12345  # Should be string, not int
                },
                "node": {
                    "id": ["node-1"]  # Should be string, not list
                },
                "database": {
                    "type": True  # Should be string, not bool
                },
            },
        }

        result = validator.validate(config)

        assert result.is_valid is False
        assert len(result.errors) >= 4  # May have additional validation errors

        # Check for type error messages
        error_messages = " ".join(result.errors)
        assert "must be of type" in error_messages
        assert "configVersion" in error_messages
        assert "joinKey" in error_messages
        assert "node.id" in error_messages
        assert "database.type" in error_messages

    def test_missing_recommended_keys_warnings(self):
        """Test warnings for missing recommended keys."""
        validator = ArtifactoryOSSValidator()

        config = {
            "configVersion": 1,
            "shared": {
                "security": {"joinKey": "valid.key.encrypted123"},
                "node": {
                    "id": "node-1"
                    # Missing recommended: ip, haEnabled
                },
                "database": {
                    "type": "derby"
                    # Missing recommended: driver, url, username, password
                },
            },
        }

        result = validator.validate(config)

        assert result.is_valid is True  # Still valid, just warnings
        assert len(result.errors) == 0
        assert len(result.warnings) > 0

        # Check for specific recommended key warnings
        warning_messages = " ".join(result.warnings)
        assert "Recommended" in warning_messages
        assert "shared.node.ip" in warning_messages
        assert "shared.node.haEnabled" in warning_messages

    def test_config_version_validation(self):
        """Test configVersion specific validation."""
        validator = ArtifactoryOSSValidator()

        config = {
            "configVersion": 2,  # Not version 1
            "shared": {
                "security": {"joinKey": "valid.key.encrypted123"},
                "node": {"id": "node-1"},
                "database": {"type": "derby"},
            },
        }

        result = validator.validate(config)

        assert result.is_valid is True  # Still valid, just warning
        assert len(result.warnings) > 0

        # Check for version warning
        warning_messages = " ".join(result.warnings)
        assert "configVersion 2" in warning_messages
        assert "Version 1 is recommended" in warning_messages

    def test_invalid_database_type_error(self):
        """Test validation fails with invalid database type."""
        validator = ArtifactoryOSSValidator()

        config = {
            "configVersion": 1,
            "shared": {
                "security": {"joinKey": "valid.key.encrypted123"},
                "node": {"id": "node-1"},
                "database": {
                    "type": "mysql"  # Invalid database type
                },
            },
        }

        result = validator.validate(config)

        assert result.is_valid is False
        assert len(result.errors) >= 1

        # Check for database type error
        error_messages = " ".join(result.errors)
        assert "mysql" in error_messages
        assert "not supported" in error_messages
        assert "postgresql" in error_messages
        assert "derby" in error_messages

    def test_invalid_join_key_format_error(self):
        """Test validation fails with invalid join key format."""
        validator = ArtifactoryOSSValidator()

        invalid_join_keys = [
            "invalid_key_format",  # No dots
            "two.parts",  # Only two parts
            "..empty.parts",  # Empty parts
            "valid.",  # Ends with dot
            ".starts.with.dot",  # Starts with dot
        ]

        for invalid_key in invalid_join_keys:
            config = {
                "configVersion": 1,
                "shared": {
                    "security": {"joinKey": invalid_key},
                    "node": {"id": "node-1"},
                    "database": {"type": "derby"},
                },
            }

            result = validator.validate(config)

            assert result.is_valid is False, f"Should reject join key: {invalid_key}"

            # Check for join key format error
            error_messages = " ".join(result.errors)
            assert "Invalid joinKey format" in error_messages
            assert "prefix.algorithm.encryptedValue" in error_messages

    def test_valid_join_key_formats(self):
        """Test validation passes with valid join key formats."""
        validator = ArtifactoryOSSValidator()

        valid_join_keys = [
            "prefix.algorithm.encryptedValue",
            "artifactory.v1.longencryptedvaluehere",
            "myprefix.sha256.base64encodedvalue",
            "a.b.c.d.e",  # More than 3 parts is okay
        ]

        for valid_key in valid_join_keys:
            config = {
                "configVersion": 1,
                "shared": {
                    "security": {"joinKey": valid_key},
                    "node": {"id": "node-1"},
                    "database": {"type": "derby"},
                },
            }

            result = validator.validate(config)

            # Should not have join key format errors
            join_key_errors = [
                error for error in result.errors if "joinKey format" in error
            ]
            assert len(join_key_errors) == 0, f"Should accept join key: {valid_key}"

    def test_postgresql_specific_requirements(self):
        """Test PostgreSQL-specific validation requirements."""
        validator = ArtifactoryOSSValidator()

        config = {
            "configVersion": 1,
            "shared": {
                "security": {"joinKey": "valid.key.encrypted123"},
                "node": {"id": "node-1"},
                "database": {
                    "type": "postgresql"
                    # Missing PostgreSQL-specific keys
                },
            },
        }

        result = validator.validate(config)

        assert result.is_valid is False
        assert len(result.errors) >= 4

        # Check for PostgreSQL-specific required keys
        error_messages = " ".join(result.errors)
        assert "PostgreSQL requires" in error_messages
        assert "shared.database.driver" in error_messages
        assert "shared.database.url" in error_messages
        assert "shared.database.username" in error_messages
        assert "shared.database.password" in error_messages

    def test_derby_does_not_require_additional_config(self):
        """Test Derby database type doesn't require additional config."""
        validator = ArtifactoryOSSValidator()

        config = {
            "configVersion": 1,
            "shared": {
                "security": {"joinKey": "valid.key.encrypted123"},
                "node": {"id": "node-1"},
                "database": {
                    "type": "derby"
                    # No additional config needed for Derby
                },
            },
        }

        result = validator.validate(config)

        assert result.is_valid is True

        # Should not have PostgreSQL-specific errors
        pg_errors = [error for error in result.errors if "PostgreSQL requires" in error]
        assert len(pg_errors) == 0

    def test_nested_invalid_oss_keys(self):
        """Test validation catches nested invalid OSS keys."""
        validator = ArtifactoryOSSValidator()

        config = {
            "configVersion": 1,
            "shared": {
                "security": {"joinKey": "valid.key.encrypted123"},
                "node": {"id": "node-1"},
                "database": {
                    "type": "derby",
                    "properties": {  # Invalid nested key
                        "maxActive": 100
                    },
                },
            },
        }

        result = validator.validate(config)

        assert result.is_valid is False
        assert len(result.errors) >= 1

        # Check for nested key error
        error_messages = " ".join(result.errors)
        assert "shared.database.properties" in error_messages
        assert "OSS version" in error_messages

    def test_empty_config_validation(self):
        """Test validation with completely empty configuration."""
        validator = ArtifactoryOSSValidator()

        result = validator.validate({})

        assert result.is_valid is False
        assert len(result.errors) >= len(validator.REQUIRED_KEYS)

        # Should have errors for all required keys
        error_messages = " ".join(result.errors)
        for required_key in validator.REQUIRED_KEYS:
            assert required_key in error_messages

    def test_is_valid_join_key_edge_cases(self):
        """Test join key validation with edge cases."""
        validator = ArtifactoryOSSValidator()

        # Test non-string types
        assert validator._is_valid_join_key(None) is False
        assert validator._is_valid_join_key(123) is False
        assert validator._is_valid_join_key([]) is False
        assert validator._is_valid_join_key({}) is False
        assert validator._is_valid_join_key(True) is False

        # Test edge case strings
        assert validator._is_valid_join_key("") is False
        assert validator._is_valid_join_key("..") is False
        assert validator._is_valid_join_key("a..b") is False
        assert validator._is_valid_join_key("a.b.") is False
        assert validator._is_valid_join_key(".a.b") is False

        # Test valid cases
        assert validator._is_valid_join_key("a.b.c") is True
        assert validator._is_valid_join_key("prefix.algo.value") is True

    def test_find_keys_recursive_functionality(self):
        """Test the _find_keys_recursive helper method functionality."""
        validator = ArtifactoryOSSValidator()

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

    def test_get_value_helper_method(self):
        """Test the _get_value helper method."""
        validator = ArtifactoryOSSValidator()

        config = {"simple": "value", "nested": {"key": "nested_value"}}

        # Test existing values
        assert validator._get_value(config, "simple") == "value"
        assert validator._get_value(config, "nested.key") == "nested_value"

        # Test non-existing values
        assert validator._get_value(config, "non_existing") is None
        assert validator._get_value(config, "nested.non_existing") is None
