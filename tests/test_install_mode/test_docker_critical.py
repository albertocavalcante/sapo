"""Critical tests for Docker module functionality.

These tests focus on high-risk operations including configuration file
generation, security validations, and error handling scenarios.
"""

import tempfile
from pathlib import Path
from unittest import mock

import pytest

from sapo.cli.install_mode.common import OperationStatus
from sapo.cli.install_mode.common.file_utils import safe_write_file
from sapo.cli.install_mode.docker.config import DatabaseType, DockerConfig


class TestSafeWriteFile:
    """Test safe file writing operations."""

    def test_safe_write_file_success(self):
        """Test successful file writing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            content = "test content"

            result = safe_write_file(test_file, content, non_interactive=True)

            assert result.success is True
            assert result.status == OperationStatus.SUCCESS
            assert test_file.exists()
            assert test_file.read_text() == content

    def test_safe_write_file_creates_parent_directories(self):
        """Test that parent directories are created automatically."""
        with tempfile.TemporaryDirectory() as temp_dir:
            nested_file = Path(temp_dir) / "nested" / "dir" / "test.txt"
            content = "nested content"

            result = safe_write_file(nested_file, content, non_interactive=True)

            assert result.success is True
            assert nested_file.exists()
            assert nested_file.read_text() == content

    def test_safe_write_file_handles_directory_conflict_non_interactive(self):
        """Test handling when target path is a directory in non-interactive mode."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a directory where we want to write a file
            conflict_path = Path(temp_dir) / "conflict"
            conflict_path.mkdir()

            result = safe_write_file(conflict_path, "content", non_interactive=True)

            assert result.success is False
            assert result.status == OperationStatus.ERROR
            assert conflict_path.is_dir()  # Directory should still exist

    def test_safe_write_file_handles_write_error(self):
        """Test handling of file write errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"

            # Mock Path.write_text to raise an exception
            with mock.patch.object(
                Path, "write_text", side_effect=PermissionError("Access denied")
            ):
                result = safe_write_file(test_file, "content", non_interactive=True)

                assert result.success is False
                assert result.status == OperationStatus.ERROR

    def test_safe_write_file_overwrites_existing_file_non_interactive(self):
        """Test that existing files are overwritten in non-interactive mode."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "existing.txt"
            test_file.write_text("old content")

            result = safe_write_file(test_file, "new content", non_interactive=True)

            assert result.success is True
            assert test_file.read_text() == "new content"


class TestDockerConfigSecurity:
    """Test DockerConfig security features."""

    def test_password_generation_security_properties(self):
        """Test that generated passwords meet security requirements."""
        config = DockerConfig(version="7.111.4")

        password = config.generate_password("test_key")

        # Security requirements
        assert len(password) == 20  # Expected length
        assert password.isascii()  # Only ASCII characters

        # Should contain mixed character types for strength
        has_letter = any(c.isalpha() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#%^&*()-_=+[]{}|;:,.<>/?" for c in password)

        assert has_letter, "Password should contain letters"
        assert has_digit, "Password should contain digits"
        assert has_special, "Password should contain special characters"

        # Should not contain dangerous characters for Docker/YAML
        dangerous_chars = ["$", "`", "\\", '"', "'"]
        for char in dangerous_chars:
            assert char not in password, (
                f"Password should not contain dangerous character: {char}"
            )

    def test_password_consistency(self):
        """Test that password generation is consistent for the same key."""
        config = DockerConfig(version="7.111.4")

        password1 = config.generate_password("same_key")
        password2 = config.generate_password("same_key")
        password3 = config.get_password("same_key")

        assert password1 == password2
        assert password1 == password3

    def test_password_uniqueness(self):
        """Test that different keys generate different passwords."""
        config = DockerConfig(version="7.111.4")

        password1 = config.generate_password("key1")
        password2 = config.generate_password("key2")

        assert password1 != password2

    def test_joinkey_generation_security(self):
        """Test that join keys are generated securely."""
        config = DockerConfig(version="7.111.4")

        joinkey = config.generate_joinkey()

        # Security requirements for join keys
        assert len(joinkey) == 32  # Expected length (32 hex chars for 16 bytes)
        assert all(c in "0123456789abcdef" for c in joinkey), (
            "Join key should be hexadecimal"
        )

        # Should be consistent on repeated calls
        joinkey2 = config.generate_joinkey()
        assert joinkey == joinkey2

    def test_joinkey_custom_value(self):
        """Test that custom join keys are preserved."""
        custom_key = "custom123456789abcdef"
        config = DockerConfig(version="7.111.4", joinkey=custom_key)

        assert config.generate_joinkey() == custom_key

    def test_joinkey_uniqueness_across_instances(self):
        """Test that different config instances generate different join keys."""
        config1 = DockerConfig(version="7.111.4")
        config2 = DockerConfig(version="7.111.4")

        joinkey1 = config1.generate_joinkey()
        joinkey2 = config2.generate_joinkey()

        assert joinkey1 != joinkey2


class TestDockerConfigDatabase:
    """Test DockerConfig database configuration."""

    def test_database_type_postgresql_properties(self):
        """Test PostgreSQL database configuration properties."""
        config = DockerConfig(
            version="7.111.4",
            database_type=DatabaseType.POSTGRESQL,
            postgres_user="custom_user",
            postgres_db="custom_db",
        )

        assert config.database_type == DatabaseType.POSTGRESQL
        assert config.use_postgres is True
        assert config.use_derby is False
        assert config.postgres_user == "custom_user"
        assert config.postgres_db == "custom_db"

    def test_database_type_derby_properties(self):
        """Test Derby database configuration properties."""
        config = DockerConfig(version="7.111.4", database_type=DatabaseType.DERBY)

        assert config.database_type == DatabaseType.DERBY
        assert config.use_postgres is False
        assert config.use_derby is True

    def test_default_database_type(self):
        """Test that PostgreSQL is the default database type."""
        config = DockerConfig(version="7.111.4")

        assert config.database_type == DatabaseType.POSTGRESQL
        assert config.use_postgres is True
        assert config.use_derby is False

    def test_postgres_defaults(self):
        """Test PostgreSQL default configuration values."""
        config = DockerConfig(version="7.111.4")

        assert config.postgres_user == "artifactory"
        assert config.postgres_db == "artifactory"


class TestDockerConfigPaths:
    """Test DockerConfig path handling."""

    def test_default_paths(self):
        """Test default path configuration."""
        config = DockerConfig(version="7.111.4")

        # Check that default paths are reasonable
        assert config.data_dir == Path.home() / ".jfrog" / "artifactory"
        assert config.output_dir == Path.home() / ".jfrog" / "artifactory" / "docker"
        assert config.port == 8082

    def test_custom_paths(self):
        """Test custom path configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir) / "custom_data"
            output_dir = Path(temp_dir) / "custom_output"

            config = DockerConfig(
                version="7.111.4", data_dir=data_dir, output_dir=output_dir, port=9999
            )

            assert config.data_dir == data_dir
            assert config.output_dir == output_dir
            assert config.port == 9999

    def test_path_absolute_conversion(self):
        """Test that paths are handled properly for absolute conversion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir) / "test_data"

            config = DockerConfig(version="7.111.4", data_dir=data_dir)

            # Should be able to get absolute path
            absolute_path = config.data_dir.absolute()
            assert absolute_path.is_absolute()


class TestDockerConfigValidation:
    """Test DockerConfig validation and error handling."""

    def test_version_required(self):
        """Test that version is required."""
        with pytest.raises(ValueError):
            DockerConfig()  # Missing required version

    def test_version_string_validation(self):
        """Test version string validation."""
        # Valid versions should work
        config1 = DockerConfig(version="7.111.4")
        config2 = DockerConfig(version="latest")
        config3 = DockerConfig(version="7.111.4-alpine")

        assert config1.version == "7.111.4"
        assert config2.version == "latest"
        assert config3.version == "7.111.4-alpine"

    def test_port_validation(self):
        """Test port number validation."""
        # Valid ports should work
        config1 = DockerConfig(version="7.111.4", port=8080)
        config2 = DockerConfig(version="7.111.4", port=8082)

        assert config1.port == 8080
        assert config2.port == 8082
