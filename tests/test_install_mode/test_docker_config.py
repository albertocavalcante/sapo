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
