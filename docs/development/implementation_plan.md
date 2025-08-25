# Docker Installation Mode Implementation Plan

## Files to Create/Modify

1. Create `sapo/cli/install_mode/__init__.py`
   - Define `InstallMode` enum with DOCKER (initially)

2. Create `sapo/cli/install_mode/docker.py`
   - Docker compose file generation
   - System.yaml template
   - Docker-specific configuration

3. Modify `sapo/cli/cli.py`
   - Update `install` command to support `--mode` option
   - Add mode-specific parameters

4. Modify `sapo/cli/artifactory.py`
   - Extend `ArtifactoryConfig` to handle installation modes
   - Add mode-specific configuration options

## Implementation Steps

1. Set up the basic structure with the InstallMode enum
2. Create templates for docker-compose.yml and system.yaml
3. Implement the docker installation mode functionality
4. Update the CLI interface to support the new options
5. Implement basic validation and error handling
6. Add tests for the new functionality

## Testing Checklist

- Verify Docker installation with default parameters
- Test custom port configuration
- Test custom data directory
- Verify proper system.yaml generation
- Test with different Artifactory versions