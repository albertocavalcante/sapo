"""Tests for Docker file generation."""

import tempfile
from pathlib import Path
from unittest import mock
import platform

import pytest
from rich.console import Console

from sapo.cli.install_mode.docker.config import DockerConfig
from sapo.cli.install_mode.docker.files import DockerFileManager, FileType
from sapo.cli.install_mode.common import OperationStatus


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def docker_config(temp_data_dir):
    """Create a DockerConfig instance for testing."""
    return DockerConfig(
        version="7.111.4",
        port=8090,
        data_dir=temp_data_dir / "jfrog" / "artifactory",
        joinkey="123456789abcdef0123456789abcdef0",
    )


@pytest.fixture
def mock_console():
    """Create a mock console for testing."""
    console = mock.MagicMock(spec=Console)
    console.print = mock.MagicMock()
    return console


class TestDockerFileManager:
    """Tests for DockerFileManager."""

    def test_initialization(self, docker_config, mock_console):
        """Test DockerFileManager initialization."""
        manager = DockerFileManager(docker_config, mock_console)

        assert manager.config == docker_config
        assert manager.console == mock_console
        assert manager.use_named_volumes is False
        assert manager.volume_names == {}

        # Test with named volumes
        volume_names = {"data": "vol1", "logs": "vol2"}
        manager2 = DockerFileManager(
            docker_config,
            mock_console,
            use_named_volumes=True,
            volume_names=volume_names,
        )
        assert manager2.use_named_volumes is True
        assert manager2.volume_names == volume_names

    @mock.patch("sapo.cli.install_mode.docker.files.render_template_from_file")
    @mock.patch("sapo.cli.install_mode.docker.files.safe_write_file")
    def test_generate_env_file(
        self, mock_write, mock_render, docker_config, mock_console
    ):
        """Test environment file generation."""
        # Setup mocks
        mock_render.return_value = "MOCK_ENV_CONTENT"
        mock_write.return_value.success = True

        # Create the manager
        manager = DockerFileManager(docker_config, mock_console)

        # Generate the file
        result = manager._generate_env_file()

        # Verify the result
        assert result.success is True

        # Check that the template was rendered
        mock_render.assert_called_once()
        args, kwargs = mock_render.call_args
        assert args[0] == "docker"
        assert args[1] == "env.j2"
        context = args[2]

        # Verify context values
        assert context["artifactory_version"] == docker_config.version
        assert context["external_port"] == docker_config.port
        assert context["postgres_user"] == docker_config.postgres_user
        assert context["use_postgres"] is True
        assert context["joinkey"] == docker_config.joinkey

        # Verify the file was written
        mock_write.assert_called_once_with(
            docker_config.output_dir / ".env", "MOCK_ENV_CONTENT", False
        )

    @mock.patch("sapo.cli.install_mode.docker.files.render_template_from_file")
    @mock.patch("sapo.cli.install_mode.docker.files.safe_write_file")
    def test_generate_docker_compose(
        self, mock_write, mock_render, docker_config, mock_console
    ):
        """Test docker-compose.yml generation."""
        # Setup mocks
        mock_render.return_value = "MOCK_COMPOSE_CONTENT"
        mock_write.return_value.success = True

        # Create the manager
        manager = DockerFileManager(docker_config, mock_console)

        # Generate the file
        result = manager._generate_docker_compose()

        # Verify the result
        assert result.success is True

        # Check that the template was rendered
        mock_render.assert_called_once()
        args, kwargs = mock_render.call_args
        assert args[0] == "docker"
        assert args[1] == "docker-compose.yml.j2"
        context = args[2]

        # Verify context values
        assert context["docker_registry"] == "releases-docker.jfrog.io"
        assert context["artifactory_version"] == docker_config.version
        assert context["external_port"] == docker_config.port
        assert context["db_type"] == "postgresql"
        assert context["use_postgres"] is True
        assert context["use_named_volumes"] is False

        # Verify the file was written
        mock_write.assert_called_once_with(
            docker_config.output_dir / "docker-compose.yml",
            "MOCK_COMPOSE_CONTENT",
            False,
        )

    @mock.patch("sapo.cli.install_mode.docker.files.render_template_from_file")
    @mock.patch("sapo.cli.install_mode.docker.files.safe_write_file")
    def test_generate_system_yaml(
        self, mock_write, mock_render, docker_config, mock_console
    ):
        """Test system.yaml generation."""
        # Setup mocks
        mock_render.return_value = "MOCK_SYSTEM_YAML_CONTENT"
        mock_write.return_value.success = True

        # Create the manager
        manager = DockerFileManager(docker_config, mock_console)

        # Generate the file
        result = manager._generate_system_yaml()

        # Verify the result
        assert result.success is True

        # Check that the template was rendered
        mock_render.assert_called_once()
        args, kwargs = mock_render.call_args
        assert args[0] == "docker"
        assert args[1] == "system.yaml.j2"
        context = args[2]

        # Verify context values
        assert context["use_postgres"] is True
        assert context["postgres_user"] == docker_config.postgres_user
        assert context["joinkey"] == docker_config.joinkey
        assert context["platform"] == platform.system()

        # Verify both files were written (etc dir and output dir)
        assert mock_write.call_count == 2
        mock_write.assert_any_call(
            docker_config.data_dir / "etc" / "system.yaml",
            "MOCK_SYSTEM_YAML_CONTENT",
            False,
        )
        mock_write.assert_any_call(
            docker_config.output_dir / "system.yaml", "MOCK_SYSTEM_YAML_CONTENT", False
        )

    @mock.patch("sapo.cli.install_mode.docker.files.shutil.rmtree")
    @mock.patch("sapo.cli.install_mode.docker.files.render_template_from_file")
    @mock.patch("sapo.cli.install_mode.docker.files.safe_write_file")
    def test_system_yaml_handles_directory_conflict(
        self,
        mock_write,
        mock_render,
        mock_rmtree,
        docker_config,
        mock_console,
        temp_data_dir,
    ):
        """Test system.yaml handles the case where it's a directory."""
        # Setup mocks
        mock_render.return_value = "MOCK_SYSTEM_YAML_CONTENT"
        mock_write.return_value.success = True

        # Create the manager
        manager = DockerFileManager(docker_config, mock_console)

        # Create a system.yaml directory to simulate the problem
        system_yaml_dir = docker_config.data_dir / "etc" / "system.yaml"
        system_yaml_dir.parent.mkdir(parents=True, exist_ok=True)
        system_yaml_dir.mkdir(parents=True, exist_ok=True)

        # Generate the file
        manager._generate_system_yaml()

        # Verify rmtree was called to remove the directory
        mock_rmtree.assert_called_once_with(system_yaml_dir)

        # Check that the template was rendered
        mock_render.assert_called_once()

        # Verify both files were written (etc dir and output dir)
        assert mock_write.call_count == 2

    @mock.patch(
        "sapo.cli.install_mode.docker.files.DockerFileManager._generate_env_file"
    )
    @mock.patch(
        "sapo.cli.install_mode.docker.files.DockerFileManager._generate_docker_compose"
    )
    @mock.patch(
        "sapo.cli.install_mode.docker.files.DockerFileManager._generate_system_yaml"
    )
    @mock.patch("sapo.cli.install_mode.docker.files.DockerFileManager._set_permissions")
    def test_generate_all_files(
        self,
        mock_permissions,
        mock_system,
        mock_compose,
        mock_env,
        docker_config,
        mock_console,
    ):
        """Test generating all required files."""
        # Setup mocks
        mock_env.return_value.success = True
        mock_compose.return_value.success = True
        mock_system.return_value.success = True

        # Create the manager
        manager = DockerFileManager(docker_config, mock_console)

        # Create a mock for create_directories
        manager.create_directories = mock.MagicMock()

        # Generate all files
        results = manager.generate_all_files()

        # Verify directories were created
        manager.create_directories.assert_called_once()

        # Verify all files were generated
        assert mock_env.call_count == 1
        assert mock_compose.call_count == 1
        assert mock_system.call_count == 1

        # Check that permissions were set
        mock_permissions.assert_called_once_with(False)

        # Verify results contain all expected file types
        assert FileType.ENV in results
        assert FileType.DOCKER_COMPOSE in results
        assert FileType.SYSTEM_YAML in results
        assert all(result.success for result in results.values())

    @mock.patch("sapo.cli.install_mode.docker.files.create_artifactory_structure")
    def test_create_directories(
        self, mock_create_structure, docker_config, mock_console
    ):
        """Test directory creation for bind mounts."""
        # Setup mock
        mock_create_structure.return_value = {
            "var": docker_config.data_dir,
            "etc": docker_config.data_dir / "etc",
            "data": docker_config.data_dir / "data",
            "logs": docker_config.data_dir / "logs",
            "backup": docker_config.data_dir / "backup",
        }

        # Create the manager
        manager = DockerFileManager(docker_config, mock_console)

        # Create directories
        directories = manager.create_directories()

        # Verify structure was created
        mock_create_structure.assert_called_once_with(docker_config.data_dir)

        # Verify PostgreSQL directory was created
        assert "postgresql" in directories
        assert directories["postgresql"] == docker_config.data_dir / "postgresql"

        # Verify PostgreSQL data directory was created
        assert "postgresql_data" in directories
        assert (
            directories["postgresql_data"]
            == docker_config.data_dir / "postgresql" / "data"
        )

    def test_create_directories_with_named_volumes(self, docker_config, mock_console):
        """Test directory creation with named volumes."""
        # Create the manager with named volumes
        manager = DockerFileManager(docker_config, mock_console, use_named_volumes=True)

        # Create directories
        directories = manager.create_directories()

        # With named volumes, only etc should be created
        assert len(directories) == 1
        assert "etc" in directories
        assert directories["etc"] == docker_config.data_dir / "etc"

        # Verify etc directory was actually created
        assert (docker_config.data_dir / "etc").exists()

    @mock.patch("sapo.cli.install_mode.docker.files.set_directory_permissions")
    def test_set_permissions(self, mock_set_permissions, docker_config, mock_console):
        """Test directory permission setting."""
        # Setup mock
        mock_set_permissions.return_value = (OperationStatus.SUCCESS, None)

        # Create the manager
        manager = DockerFileManager(docker_config, mock_console)

        # Set permissions
        manager._set_permissions()

        # Verify permissions were set
        mock_set_permissions.assert_called_once_with(
            docker_config.data_dir,
            "1030:1030",  # Artifactory user in container
            False,
        )
