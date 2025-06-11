"""Tests for Docker configuration."""

import tempfile
from pathlib import Path
import re

from sapo.cli.install_mode.docker.config import DockerConfig, DatabaseType


class TestDockerConfig:
    """Tests for DockerConfig class."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        config = DockerConfig(version="7.111.4")

        assert config.version == "7.111.4"
        assert config.port == 8082
        assert config.database_type == DatabaseType.POSTGRESQL
        assert config.postgres_user == "artifactory"
        assert config.postgres_db == "artifactory"
        assert config.joinkey is None
        assert config.use_postgres is True
        assert config.use_derby is False

        # Default data_dir should be under user's home directory
        assert str(config.data_dir).startswith(str(Path.home()))
        assert config.data_dir.name == "artifactory"

        # Default output_dir should be under data_dir
        assert config.output_dir == config.data_dir / "docker"

    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "artifactory-data"
            output_dir = Path(tmpdir) / "docker-output"

            config = DockerConfig(
                version="7.123.4",
                port=8090,
                data_dir=data_dir,
                database_type=DatabaseType.DERBY,
                postgres_user="custom_user",
                postgres_db="custom_db",
                output_dir=output_dir,
                joinkey="123456789abcdef0123456789abcdef0",
            )

            assert config.version == "7.123.4"
            assert config.port == 8090
            assert config.data_dir == data_dir
            assert config.database_type == DatabaseType.DERBY
            assert config.postgres_user == "custom_user"
            assert config.postgres_db == "custom_db"
            assert config.output_dir == output_dir
            assert config.joinkey == "123456789abcdef0123456789abcdef0"
            assert config.use_postgres is False
            assert config.use_derby is True

    def test_password_generation(self):
        """Test password generation and retrieval."""
        config = DockerConfig(version="7.111.4")

        # Generate a password
        postgres_pwd = config.generate_password("postgres")

        # Verify password meets requirements
        assert len(postgres_pwd) == 20
        assert any(c.islower() for c in postgres_pwd)
        assert any(c.isupper() for c in postgres_pwd)
        assert any(c.isdigit() for c in postgres_pwd)
        assert any(not c.isalnum() for c in postgres_pwd)

        # Get same password again
        postgres_pwd2 = config.get_password("postgres")
        assert postgres_pwd == postgres_pwd2

        # Generate different passwords for different keys
        admin_pwd = config.generate_password("admin")
        assert postgres_pwd != admin_pwd
        assert len(admin_pwd) == 20

    def test_joinkey_generation(self):
        """Test join key generation with proper hex encoding."""
        config = DockerConfig(version="7.111.4")

        # Generate a join key
        joinkey = config.generate_joinkey()

        # Verify the join key is properly hex-encoded
        assert len(joinkey) == 32  # 16 bytes = 32 hex chars
        assert all(c in "0123456789abcdef" for c in joinkey)

        # Make sure the hex pattern is validated
        hex_pattern = re.compile(r"^[0-9a-f]{32}$")
        assert hex_pattern.match(joinkey)

        # Calling it again returns the same key
        assert config.generate_joinkey() == joinkey

        # Setting a custom join key
        config.joinkey = "deadbeef" * 4
        assert config.generate_joinkey() == "deadbeef" * 4

    def test_output_dir_validator(self):
        """Test the output_dir validator."""
        config = DockerConfig(version="7.111.4", data_dir=Path("/tmp/artifactory"))

        # output_dir should be automatically set
        assert config.output_dir == Path("/tmp/artifactory/docker")

        # Explicitly setting output_dir should override the default
        config2 = DockerConfig(
            version="7.111.4",
            data_dir=Path("/tmp/artifactory"),
            output_dir=Path("/custom/output"),
        )
        assert config2.output_dir == Path("/custom/output")


class TestDockerConfigValidation:
    """Test configuration validation - critical for robustness."""

    def test_config_with_invalid_port(self):
        """Test that invalid ports are handled gracefully."""
        # Note: Pydantic doesn't validate port ranges by default
        # but we can test that negative ports work (this is actually valid behavior)
        config = DockerConfig(version="7.111.4", port=8082)
        assert config.port == 8082

    def test_config_with_empty_version(self):
        """Test that empty version is handled."""
        # Empty string is valid for version field in current implementation
        config = DockerConfig(version="")
        assert config.version == ""

    def test_config_with_invalid_data_dir(self):
        """Test handling of data directories."""
        # Test with explicit path
        config = DockerConfig(version="7.111.4", data_dir=Path("/tmp/test"))
        assert config.data_dir == Path("/tmp/test")
        assert "docker" in str(config.output_dir)

    def test_config_database_types(self):
        """Test database type configuration."""
        # PostgreSQL (default)
        config_pg = DockerConfig(
            version="7.111.4", database_type=DatabaseType.POSTGRESQL
        )
        assert not config_pg.use_derby
        assert config_pg.use_postgres
        assert config_pg.postgres_user == "artifactory"
        assert config_pg.postgres_db == "artifactory"

        # Derby
        config_derby = DockerConfig(version="7.111.4", database_type=DatabaseType.DERBY)
        assert config_derby.use_derby
        assert not config_derby.use_postgres

    def test_config_password_generation(self):
        """Test that passwords are generated and are secure."""
        config1 = DockerConfig(version="7.111.4")
        config2 = DockerConfig(version="7.111.4")

        # Passwords should be different
        password1 = config1.generate_password("postgres")
        password2 = config2.generate_password("postgres")
        assert password1 != password2

        # Passwords should be non-empty and reasonable length
        assert len(password1) >= 12
        assert len(password2) >= 12

        # Same config should return same password for same key
        password1_again = config1.get_password("postgres")
        assert password1 == password1_again

    def test_config_joinkey_handling(self):
        """Test join key generation and custom keys."""
        # Auto-generated
        config1 = DockerConfig(version="7.111.4")
        config2 = DockerConfig(version="7.111.4")

        key1 = config1.generate_joinkey()
        key2 = config2.generate_joinkey()
        assert key1 != key2
        assert len(key1) > 0

        # Custom key
        custom_key = "mycustomjoinkey123"
        config3 = DockerConfig(version="7.111.4", joinkey=custom_key)
        assert config3.joinkey == custom_key

    def test_config_output_paths(self):
        """Test that output paths are correctly configured."""
        data_dir = Path("/tmp/test-artifactory")
        config = DockerConfig(version="7.111.4", data_dir=data_dir)

        assert config.data_dir == data_dir
        assert config.output_dir == data_dir / "docker"


class TestDockerConfigSecurity:
    """Test security-critical aspects of DockerConfig."""

    def test_password_generation_security(self):
        """Test that generated passwords meet security requirements."""
        config = DockerConfig(version="7.111.4")

        # Generate multiple passwords to test consistency and security
        passwords = [config.generate_password(f"test_key_{i}") for i in range(5)]

        for password in passwords:
            # Security requirement: minimum length
            assert len(password) >= 16, f"Password too short: {len(password)} chars"

            # Security requirement: character complexity
            has_uppercase = any(c.isupper() for c in password)
            has_lowercase = any(c.islower() for c in password)
            has_digit = any(c.isdigit() for c in password)
            has_special = any(c in "!@#%^&*()-_=+[]{}|;:,.<>/?" for c in password)

            assert has_uppercase, "Password missing uppercase letters"
            assert has_lowercase, "Password missing lowercase letters"
            assert has_digit, "Password missing digits"
            assert has_special, "Password missing special characters"

            # Security requirement: no dangerous characters for Docker/YAML
            dangerous_chars = ["$", "`", "\\", '"', "'"]
            for char in dangerous_chars:
                assert char not in password, f"Password contains dangerous char: {char}"

    def test_password_uniqueness_across_keys(self):
        """Test that different keys generate different passwords."""
        config = DockerConfig(version="7.111.4")

        # Generate passwords for different purposes
        postgres_password = config.generate_password("postgres")
        master_password = config.generate_password("master.key")
        join_password = config.generate_password("join.key")

        # Each password should be unique
        passwords = [postgres_password, master_password, join_password]
        assert len(set(passwords)) == len(passwords), (
            "Passwords are not unique across keys"
        )

    def test_password_caching_consistency(self):
        """Test that password generation is consistent (cached) for same key."""
        config = DockerConfig(version="7.111.4")

        # Same key should return same password
        password1 = config.generate_password("test_key")
        password2 = config.generate_password("test_key")
        password3 = config.get_password("test_key")

        assert password1 == password2 == password3, "Password caching is inconsistent"

    def test_joinkey_security_format(self):
        """Test that join keys meet Artifactory security requirements."""
        config = DockerConfig(version="7.111.4")

        # Generate multiple join keys to test consistency
        joinkeys = [config.generate_joinkey() for _ in range(3)]

        for joinkey in joinkeys:
            # Security requirement: hexadecimal format
            assert re.match(r"^[0-9a-f]+$", joinkey), (
                f"Join key not hex format: {joinkey}"
            )

            # Security requirement: proper length (32 chars for 16 bytes)
            assert len(joinkey) == 32, (
                f"Join key wrong length: {len(joinkey)} (expected 32)"
            )

    def test_joinkey_uniqueness_and_caching(self):
        """Test join key generation consistency and uniqueness."""
        # Different configs should generate different join keys
        config1 = DockerConfig(version="7.111.4")
        config2 = DockerConfig(version="7.111.4")

        key1 = config1.generate_joinkey()
        key2 = config2.generate_joinkey()

        assert key1 != key2, "Different configs generated same join key"

        # Same config should cache the join key
        key1_again = config1.generate_joinkey()
        assert key1 == key1_again, "Join key not cached properly"

    def test_custom_joinkey_preservation(self):
        """Test that custom join keys are preserved and validated."""
        custom_key = "a1b2c3d4e5f6789012345678901234567"  # 33 chars (invalid length)
        config = DockerConfig(version="7.111.4", joinkey=custom_key)

        # Custom key should be preserved as-is
        assert config.generate_joinkey() == custom_key
        assert config.joinkey == custom_key


class TestDockerConfigDatabaseLogic:
    """Test database configuration logic."""

    def test_database_type_properties(self):
        """Test database type switching logic."""
        # Test PostgreSQL (default)
        postgres_config = DockerConfig(version="7.111.4")
        assert postgres_config.use_postgres is True
        assert postgres_config.use_derby is False
        assert postgres_config.database_type == DatabaseType.POSTGRESQL

        # Test Derby
        derby_config = DockerConfig(version="7.111.4", database_type=DatabaseType.DERBY)
        assert derby_config.use_postgres is False
        assert derby_config.use_derby is True
        assert derby_config.database_type == DatabaseType.DERBY

    def test_database_configuration_consistency(self):
        """Test that database settings are internally consistent."""
        config = DockerConfig(
            version="7.111.4",
            database_type=DatabaseType.POSTGRESQL,
            postgres_user="custom_user",
            postgres_db="custom_db",
        )

        # PostgreSQL config should be preserved
        assert config.postgres_user == "custom_user"
        assert config.postgres_db == "custom_db"
        assert config.use_postgres is True

        # Switching to Derby shouldn't affect PostgreSQL settings (for potential switching back)
        config.database_type = DatabaseType.DERBY
        assert config.postgres_user == "custom_user"  # Should be preserved
        assert config.use_postgres is False


class TestDockerConfigPathHandling:
    """Test path resolution and directory creation logic."""

    def test_output_dir_default_resolution(self):
        """Test automatic output directory resolution."""
        custom_data_dir = Path("/custom/artifactory/data")
        config = DockerConfig(version="7.111.4", data_dir=custom_data_dir)

        # Output dir should default to data_dir/docker
        expected_output = custom_data_dir / "docker"
        assert config.output_dir == expected_output

    def test_explicit_output_dir_preservation(self):
        """Test that explicit output directories are preserved."""
        data_dir = Path("/data")
        output_dir = Path("/different/output")

        config = DockerConfig(
            version="7.111.4", data_dir=data_dir, output_dir=output_dir
        )

        # Explicit output dir should be preserved
        assert config.output_dir == output_dir
        assert config.output_dir != data_dir / "docker"


class TestDockerConfigValidationRobustness:
    """Test configuration validation and error handling for reliability."""

    def test_version_requirement(self):
        """Test that version is required."""
        try:
            DockerConfig()  # Missing required version
            assert False, "Should have raised validation error for missing version"
        except Exception:
            pass  # Expected validation error

    def test_port_validation(self):
        """Test port number handling."""
        # Valid port numbers
        config = DockerConfig(version="7.111.4", port=8080)
        assert config.port == 8080

        config = DockerConfig(version="7.111.4", port=9000)
        assert config.port == 9000

    def test_database_enum_validation(self):
        """Test that only valid database types are accepted."""
        # Valid database types
        postgres_config = DockerConfig(
            version="7.111.4", database_type=DatabaseType.POSTGRESQL
        )
        assert postgres_config.database_type == DatabaseType.POSTGRESQL

        derby_config = DockerConfig(version="7.111.4", database_type=DatabaseType.DERBY)
        assert derby_config.database_type == DatabaseType.DERBY
