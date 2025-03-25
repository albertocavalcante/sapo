# Sapo 🐸

A CLI tool for downloading and installing JFrog Artifactory OSS.

## 📑 Table of Contents
- [Overview](#overview)
- [Installation](#installation)
  - [Using pipx (Recommended)](#using-pipx-recommended-)
  - [Alternative Installation Methods](#alternative-installation-methods-)
    - [Using Docker Compose](#using-docker-compose-)
    - [Using Helm (Kubernetes)](#using-helm-kubernetes-)
    - [Using Poetry (Development)](#using-poetry-development-)
- [Usage](#usage)
  - [Basic Commands](#basic-commands)
  - [Platform-Specific Behavior](#platform-specific-behavior)
  - [Examples](#examples)
- [Development](#development)
- [Notes](#notes)

## Overview

Sapo is a command-line tool that simplifies the process of downloading and installing JFrog Artifactory OSS. It provides a user-friendly interface to manage different versions and platforms of Artifactory.

For a complete list of available Artifactory OSS versions, visit the [official JFrog releases page](https://releases.jfrog.io/artifactory/bintray-artifactory/org/artifactory/oss/jfrog-artifactory-oss/).

For detailed information about single-node installation, including prerequisites and system requirements, refer to the [official JFrog single-node installation documentation](https://jfrog.com/help/r/jfrog-installation-setup-documentation/artifactory-single-node-installation).

## Installation

You can install Sapo in several ways:

### Using pipx (Recommended) 🚀

```bash
# Build the package using Poetry
poetry build

# Install the built package using pipx
pipx install dist/sapo-0.1.0.tar.gz
```

### Alternative Installation Methods 🔧

#### Using Docker Compose 🐳
If you prefer using Docker, you can install Artifactory using Docker Compose. This method is particularly useful for containerized environments or when you want to run Artifactory in isolation. For detailed instructions, see the [official JFrog documentation](https://jfrog.com/help/r/jfrog-installation-setup-documentation/install-artifactory-single-node-with-docker-compose).

#### Using Helm (Kubernetes) 🎮
For Kubernetes environments, you can install Artifactory using the official JFrog Helm chart. This method is ideal for container orchestration and provides additional features like automatic scaling and high availability. For detailed instructions, see the [official JFrog Helm chart documentation](https://github.com/jfrog/charts/tree/master/stable/artifactory-oss).

#### Using Poetry (Development) 🛠️

```bash
poetry install
```

After installation, you can use the CLI in one of these ways:

1. Activate the Poetry environment (if using Poetry):
```bash
# Using Poetry 2.0.0+
poetry env use python
poetry env activate

# Or if you prefer the shell plugin
poetry self add poetry-plugin-shell
poetry shell

# For fish shell users
source ~/.cache/pypoetry/virtualenvs/sapo-*/bin/activate.fish
```

2. Use Poetry run (if using Poetry):
```bash
poetry run sapo --help
```

3. Use the full path to the virtual environment (if using Poetry):
```bash
# On macOS/Linux
~/.cache/pypoetry/virtualenvs/sapo-*/bin/sapo --help

# On Windows
%APPDATA%\pypoetry\virtualenvs\sapo-*\Scripts\sapo --help
```

The recommended approach is to use pipx installation as it:
- Creates an isolated environment for the tool
- Prevents conflicts with other Python packages
- Makes the `sapo` command available system-wide
- Follows best practices for CLI tool installation

## Usage

### Basic Commands

#### Show Help 📚
```bash
# Show general help
sapo

# Show help for a specific command
sapo install --help
sapo versions --help
sapo info --help
```

#### List Available Versions 📋
```bash
# Show the 10 most recent versions (default)
sapo versions

# Show the last 5 versions
sapo versions --limit 5

# Show all available versions
sapo versions --limit 0
```

#### Install Artifactory ⚙️
```bash
# Install the latest version (7.98.17)
sapo install

# Install a specific version
sapo install --version 7.98.16

# Install for a different platform
sapo install --platform linux

# Install with custom destination
sapo install --dest /path/to/destination

# Keep the downloaded archive
sapo install --keep
```

#### Show Installation Information ℹ️
```bash
# Show info for the latest version
sapo info

# Show info for a specific version
sapo info --version 7.98.16
```

### Platform-Specific Behavior

#### Default Installation Paths 🗂️
- **Windows**: `%USERPROFILE%\AppData\Local\Programs\Artifactory`
- **macOS/Linux**: `~/dev/tools`

#### Package Formats 📦
- **Windows**: `.zip` archives
- **macOS/Linux**: `.tar.gz` archives

### Examples

#### Complete Installation Process 🚀
```bash
# 1. Check available versions
sapo versions

# 2. Get information about a specific version
sapo info --version 7.98.17

# 3. Install the version
sapo install --version 7.98.17 --keep
```

#### Development Setup 💻
```bash
# Install for development with custom path
sapo install --version 7.98.17 --dest ~/projects/artifactory-dev --keep
```

#### Cross-Platform Installation 🌐
```bash
# Install Linux version on macOS
sapo install --version 7.98.17 --platform linux

# Install Windows version on macOS
sapo install --version 7.98.17 --platform windows
```

## Development

### Prerequisites
- Python 3.13 or above
- Poetry >=2.0.0

### Setup
1. Clone the repository
2. Install dependencies:
```bash
poetry install
```

### Running Tests
```bash
poetry run pytest
```

## Notes

- The `versions` command shows the most recent versions by default (10) to avoid long loading times
- Use `--limit 0` with the `versions` command to see all available versions
- The `--keep` flag is useful when you want to inspect the downloaded archive
- Platform-specific paths are automatically selected based on your operating system

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
