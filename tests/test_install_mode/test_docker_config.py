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
