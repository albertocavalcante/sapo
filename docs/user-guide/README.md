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
- Python 3.8 or higher
- Docker (for Docker installation mode)
- Sufficient disk space (minimum 20GB recommended)

### Quick Install
```bash
# Using pipx (recommended)
pipx install sapo

# Or using pip
pip install sapo
```

## Installation Modes

### Docker Mode (Recommended)
The Docker mode provides a containerized installation with PostgreSQL database.

```bash
# Basic installation with defaults
sapo install --mode docker

# Specify edition (OSS or Pro)
sapo install --mode docker --edition oss

# Custom configuration
sapo install --mode docker --port 8082 --data-dir ~/.artifactory
```

### Direct Mode
For direct installation on the host system (advanced users).

```bash
sapo install --mode direct --version 7.111.9
```

## Configuration

### Environment Variables
- `SAPO_DATA_DIR` - Default data directory
- `SAPO_LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)

### Configuration Files
- `system.yaml` - Main Artifactory configuration
- `docker-compose.yml` - Docker deployment configuration
- `.env` - Environment variables for Docker

## Commands Reference

### `sapo install`
Install Artifactory with specified options.

Options:
- `--mode` - Installation mode (docker/direct)
- `--edition` - Artifactory edition (oss/pro)
- `--version` - Specific version to install
- `--port` - HTTP port (default: 8082)
- `--data-dir` - Data directory location

### `sapo diagnose`
Diagnose installation issues.

```bash
sapo diagnose --path ~/.jfrog/artifactory
```

### `sapo list`
List available Artifactory versions.

```bash
sapo list --edition oss
```

## Best Practices

1. **Always use Docker mode for production** - Provides better isolation and easier management
2. **Regular backups** - Back up the data directory regularly
3. **Monitor disk space** - Artifactory requires significant storage
4. **Use PostgreSQL** - Better performance than Derby for production
5. **Validate configuration** - Use `--validate-config` flag before installation