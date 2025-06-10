"""Tests for Docker installation functionality."""

from pathlib import Path

from sapo.cli.install_mode.docker import DockerConfig
from sapo.cli.install_mode.docker.config import DatabaseType

# NOTE: These private functions are tested indirectly through integration tests
# Direct unit tests are disabled due to import conflicts between docker.py and docker/ package


class TestDockerInstall:
    """Tests for Docker installation functions."""

    def test_docker_config_init(self):
        """Test DockerConfig initialization with defaults."""
        config = DockerConfig(version="7.111.4")
        assert config.version == "7.111.4"
        assert config.port == 8082
        assert str(config.data_dir).endswith("artifactory")
        assert config.database_type == DatabaseType.POSTGRESQL
        assert config.use_derby is False
        assert config.postgres_user == "artifactory"
        assert config.postgres_db == "artifactory"

    def test_docker_config_init_custom(self):
        """Test DockerConfig initialization with custom values."""
        custom_dir = Path.home() / "custom" / "artifactory"
        config = DockerConfig(
            version="7.111.4",
            port=8090,
            data_dir=custom_dir,
            database_type=DatabaseType.DERBY,
            postgres_user="custom_user",
            postgres_db="custom_db",
            joinkey="my_custom_joinkey",
        )

        assert config.version == "7.111.4"
        assert config.port == 8090
        assert config.data_dir == custom_dir
        assert config.database_type == DatabaseType.DERBY
        assert config.use_derby is True
        assert config.postgres_user == "custom_user"
        assert config.postgres_db == "custom_db"
        assert config.joinkey == "my_custom_joinkey"
