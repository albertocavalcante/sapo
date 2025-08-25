# Artifactory Installation Feature Specification

## Overview
This specification outlines the implementation of multi-mode installation support for JFrog Artifactory OSS in the Sapo CLI.

## Immediate Goal (v1)
Implement Docker-based installation with basic configuration options.

### Command Structure
```bash
# Basic Docker installation 
sapo install --mode docker --version 7.104.15

# With basic customization
sapo install --mode docker --version 7.104.15 --port 8082 --data-dir ~/artifactory-data
```

### Features for v1
- Docker mode installation using docker-compose
- Basic system.yaml configuration
- Port customization
- Data directory specification
- Version selection (leveraging existing functionality)

### Implementation Details
- Add InstallMode enum with initial DOCKER support
- Create Docker compose template generation
- Extend ArtifactoryConfig to support Docker mode
- Generate minimal system.yaml for Docker deployment

## Future Roadmap

### Additional Installation Modes (v2)
- Local binary installation
- Helm chart installation

### Enhanced Configuration Options (v3)
- Database configuration (type, connection details)
- JVM options
- Authentication settings
- Custom networking configurations
- Proxy settings
- Repository configurations

### Advanced Features (v4)
- Configuration validation
- Health checks after installation
- Upgrade support
- Backup/restore functionality
- Migration between installation modes
- Multi-node setup for HA
- Integration with external databases

## Full Command Vision
Once fully implemented, the CLI would support commands like:

```bash
# Docker mode
sapo install --mode docker --version 7.104.15 --port 8082 --data-dir ~/artifactory-data --db-type postgresql --db-url jdbc:postgresql://localhost:5432/artifactory

# Local mode
sapo install --mode local --version 7.104.15 --dest ~/tools/artifactory --java-opts "-Xms512m -Xmx2g"

# Helm mode
sapo install --mode helm --version 7.104.15 --namespace artifactory --set artifactory.javaOpts="-Xms512m -Xmx2g"

# Configuration generation only
sapo config --mode docker --version 7.104.15 --output system.yaml
```

## Implementation Architecture
- `install_mode/` package with mode-specific implementations
- Template-based configuration generation
- Modular, extensible design for adding new modes
- Consistent error handling and user feedback

This specification will be updated as implementation progresses and requirements evolve.