# Sapo User Guide

## Overview

Sapo is a CLI tool for downloading and installing JFrog Artifactory OSS. This guide covers installation, configuration, and usage.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Installation Modes](#installation-modes)
3. [Configuration](#configuration)
4. [Commands Reference](#commands-reference)
5. [Best Practices](#best-practices)

## Getting Started

### Prerequisites
- Python 3.13 or higher
- Docker (for Docker installation mode)
- Sufficient disk space (minimum 20GB recommended)

### Quick Install
```bash
# Using pipx (recommended)
pipx install sapo
```

## Installation Modes

### Docker Mode (Recommended)
The Docker mode provides a containerized installation.

```bash
# Basic installation with defaults
sapo install --mode docker

# Custom configuration
sapo install --mode docker --port 8082
```

### Local Mode
For installing the downloaded archive on the host system.

```bash
sapo install --mode local --version 7.111.9 --destination ~/tools/artifactory
```

## Configuration
Configuration files and templates are generated as needed by the selected mode.

## Commands Reference

### `sapo install`
Install Artifactory with specified options.

Options:
- `--mode` - Installation mode (docker/direct)
- `--edition` - Artifactory edition (oss/pro)
- `--version` - Specific version to install
- `--port` - HTTP port (default: 8082)
- `--data-dir` - Data directory location

### `sapo releases`
List available Artifactory releases.

```bash
sapo releases --limit 10
```

### `sapo release-notes`
Show release notes for a given version.

```bash
sapo release-notes --version 7.111.9
```

## Best Practices

1. **Always use Docker mode for production** - Provides better isolation and easier management
2. **Regular backups** - Back up the data directory regularly
3. **Monitor disk space** - Artifactory requires significant storage
4. **Use PostgreSQL** - Better performance than Derby for production
5. **Validate configuration** - Use `--validate-config` flag before installation