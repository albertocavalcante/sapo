# Sapo-CLI Improvements: Technical Specification

## Overview

This document outlines technical improvements to sapo-cli based on critical learnings from JFrog Artifactory OSS deployment issues. The primary goals are to:

1. Support OSS-specific configurations
2. Prevent service startup race conditions
3. Improve error handling and diagnostics
4. Enhance documentation and user experience

## 1. OSS-Specific Configuration Support

### 1.1 Problem Statement

Artifactory OSS has strict limitations on configuration keys compared to Pro version. Current sapo-cli generates configurations that cause validation failures in OSS, including:
- `artifactory.primary`, `artifactory.pool`, `artifactory.javaOpts`
- `artifactory.network`, `artifactory.cache`, `artifactory.security`
- `artifactory.access`, `shared.database.properties`

### 1.2 Solution Architecture

#### A. Validator Module Structure
```
sapo/cli/install_mode/validator/
├── __init__.py
├── base.py              # Base validator interface
├── oss_validator.py     # OSS-specific validation
├── pro_validator.py     # Pro-specific validation
└── errors.py           # Custom validation exceptions
```

#### B. OSS Validator Implementation
```python
# sapo/cli/install_mode/validator/oss_validator.py

class ArtifactoryOSSValidator(BaseValidator):
    """Validates system.yaml for OSS compatibility."""
    
    INVALID_OSS_KEYS = {
        'artifactory.primary',
        'artifactory.pool',
        'artifactory.javaOpts',
        'artifactory.network',
        'artifactory.cache',
        'artifactory.security',
        'artifactory.access',
        'shared.database.properties'
    }
    
    REQUIRED_KEYS = {
        'configVersion': int,
        'shared.security.joinKey': str,
        'shared.node.id': str,
        'shared.database.type': str
    }
    
    def validate(self, config: dict) -> ValidationResult:
        """Validate configuration for OSS edition."""
        errors = []
        warnings = []
        
        # Check for invalid keys
        invalid_keys = self._find_invalid_keys(config, self.INVALID_OSS_KEYS)
        if invalid_keys:
            errors.extend([
                f"Key '{key}' is not supported in OSS version"
                for key in invalid_keys
            ])
        
        # Check required keys
        missing_keys = self._check_required_keys(config, self.REQUIRED_KEYS)
        if missing_keys:
            errors.extend([
                f"Required key '{key}' is missing"
                for key in missing_keys
            ])
        
        return ValidationResult(errors=errors, warnings=warnings)
```

### 1.3 Template Separation

#### A. Directory Structure
```
sapo/cli/install_mode/templates/docker/
├── system.yaml.oss.j2      # Minimal OSS configuration
├── system.yaml.pro.j2      # Full Pro configuration
├── docker-compose.yml.j2   # Unified compose file
└── env.j2                  # Environment variables
```

#### B. OSS Template (system.yaml.oss.j2)
```yaml
configVersion: 1
shared:
    security:
        joinKey: "{{ joinkey }}"
    node:
        id: "art1"
        ip: "localhost"
        haEnabled: false
    database:
{% if use_postgres %}
        type: postgresql
        driver: org.postgresql.Driver
        url: jdbc:postgresql://postgres:5432/{{ postgres_db }}
        username: {{ postgres_user }}
        password: {{ postgres_password }}
{% else %}
        type: derby
        driver: org.apache.derby.jdbc.EmbeddedDriver
        url: jdbc:derby:data/derby/artifactory;create=true
        username: artifactory
        password: password
{% endif %}
```

### 1.4 Edition Detection

```python
# sapo/cli/install_mode/docker/config.py

class DockerConfig(BaseModel):
    """Docker deployment configuration."""
    
    edition: str = Field(default="oss", description="Artifactory edition (oss/pro)")
    
    def get_template_name(self, template_type: str) -> str:
        """Get template name based on edition."""
        if template_type == "system.yaml":
            return f"system.yaml.{self.edition}.j2"
        return f"{template_type}.j2"
```

## 2. Service Startup Orchestration

### 2.1 Problem Statement

Router and Access services have circular dependencies causing startup failures:
- Router (port 8082) needs Access service to be running
- Access (port 8040) tries to register with Router
- Current Docker setup starts all services simultaneously

### 2.2 Solution: Custom Startup Script

#### A. Orchestration Template (startup-orchestrator.sh.j2)
```bash
#!/bin/bash
# Custom startup orchestration for Artifactory OSS

set -e

echo "Starting Artifactory services in correct order..."

# Function to wait for service
wait_for_service() {
    local service=$1
    local url=$2
    local max_attempts=${3:-30}
    local attempt=1
    
    echo "Waiting for $service service..."
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            echo "$service service is ready"
            return 0
        fi
        echo "Attempt $attempt/$max_attempts: $service not ready yet..."
        sleep 2
        ((attempt++))
    done
    
    echo "ERROR: $service service failed to start after $max_attempts attempts"
    return 1
}

# 1. Start Access service first
echo "Starting Access service..."
$JF_PRODUCT_HOME/app/access/bin/access.sh start &

# Wait for Access to be fully ready
wait_for_service "Access" "http://localhost:8040/access/api/v1/system/ping" 40

# 2. Start Router service
echo "Starting Router service..."
$JF_PRODUCT_HOME/app/router/bin/router.sh start &

# Wait for Router to be fully ready
wait_for_service "Router" "http://localhost:8046/router/api/v1/system/health" 40

# 3. Start Artifactory service
echo "Starting Artifactory service..."
$JF_PRODUCT_HOME/app/bin/artifactory.sh start &

# Wait for Artifactory to be ready
wait_for_service "Artifactory" "http://localhost:8081/artifactory/api/system/ping" 60

# 4. Start Frontend service
echo "Starting Frontend service..."
$JF_PRODUCT_HOME/app/frontend/bin/frontend.sh start &

# Keep container running and monitor services
echo "All services started. Monitoring..."
tail -f $JF_PRODUCT_HOME/var/log/console.log
```

#### B. Docker Compose Integration

Update docker-compose.yml.j2 to use custom entrypoint:
```yaml
artifactory:
  image: releases-docker.jfrog.io/jfrog/artifactory-oss:{{ artifactory_version }}
  volumes:
    - ./startup-orchestrator.sh:/opt/startup-orchestrator.sh:ro
  entrypoint: ["/bin/bash", "/opt/startup-orchestrator.sh"]
  healthcheck:
    test: ["CMD-SHELL", "curl -f http://localhost:8081/artifactory/api/system/ping || exit 1"]
    interval: 30s
    timeout: 10s
    retries: 10
    start_period: 180s  # Extended startup period
```

## 3. Enhanced Diagnostics

### 3.1 Diagnostic Module

```python
# sapo/cli/install_mode/diagnostics.py

class ArtifactoryDiagnostics:
    """Diagnostic tools for troubleshooting Artifactory issues."""
    
    SERVICE_ENDPOINTS = {
        'access': {
            'url': 'http://localhost:8040/access/api/v1/system/ping',
            'port': 8040,
            'name': 'Access Service'
        },
        'router': {
            'url': 'http://localhost:8046/router/api/v1/system/health',
            'port': 8046,
            'name': 'Router Service'
        },
        'artifactory': {
            'url': 'http://localhost:8081/artifactory/api/system/ping',
            'port': 8081,
            'name': 'Artifactory Service'
        },
        'frontend': {
            'url': 'http://localhost:8070',
            'port': 8070,
            'name': 'Frontend Service'
        }
    }
    
    ERROR_PATTERNS = {
        'yaml_validation': {
            'pattern': r'yaml validation failed.*misplaced',
            'message': 'Configuration validation failed. This usually means incompatible keys for OSS version.',
            'action': 'Run with --validate-config to check configuration before starting.'
        },
        'router_crash': {
            'pattern': r'router not running|router exited',
            'message': 'Router service crashed. This is often due to Access service not being ready.',
            'action': 'Check if Access service is running on port 8040.'
        },
        'circular_dependency': {
            'pattern': r'Access Service ping failed after \d+ attempts',
            'message': 'Services have circular dependency preventing startup.',
            'action': 'Use --orchestrated-startup flag to start services in correct order.'
        }
    }
    
    async def diagnose(self, logs_path: Path) -> DiagnosticReport:
        """Run comprehensive diagnostics."""
        report = DiagnosticReport()
        
        # Check service status
        report.services = await self._check_all_services()
        
        # Analyze logs
        report.log_issues = self._analyze_logs(logs_path)
        
        # Check configuration
        report.config_issues = self._validate_configuration()
        
        return report
```

### 3.2 CLI Integration

```python
# Add to sapo/cli/cli.py

@app.command()
async def diagnose(
    path: Path = typer.Option(
        Path.home() / ".jfrog/artifactory",
        "--path", "-p",
        help="Artifactory installation path"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v")
):
    """Diagnose Artifactory installation issues."""
    diagnostics = ArtifactoryDiagnostics()
    report = await diagnostics.diagnose(path)
    
    console = Console()
    
    # Display service status
    console.print("\n[bold]Service Status:[/bold]")
    for service, status in report.services.items():
        icon = "✅" if status.healthy else "❌"
        console.print(f"{icon} {service}: {status.message}")
    
    # Display configuration issues
    if report.config_issues:
        console.print("\n[bold red]Configuration Issues:[/bold red]")
        for issue in report.config_issues:
            console.print(f"  • {issue}")
    
    # Display log analysis
    if report.log_issues:
        console.print("\n[bold yellow]Log Analysis:[/bold yellow]")
        for issue in report.log_issues:
            console.print(f"  • Issue: {issue.message}")
            console.print(f"    Action: {issue.action}")
```

## 4. Feature Flags

### 4.1 Implementation

```python
# sapo/cli/config/features.py

class FeatureFlags:
    """Feature flags for gradual rollout."""
    
    OSS_VALIDATION = "oss_validation"
    ORCHESTRATED_STARTUP = "orchestrated_startup"
    ENHANCED_DIAGNOSTICS = "enhanced_diagnostics"
    
    DEFAULT_FLAGS = {
        OSS_VALIDATION: True,
        ORCHESTRATED_STARTUP: False,  # Opt-in initially
        ENHANCED_DIAGNOSTICS: True
    }
```

### 4.2 Usage in CLI

```python
# Update install command
@install_app.command()
async def docker(
    edition: str = typer.Option(
        "oss",
        "--edition",
        help="Artifactory edition (oss/pro)"
    ),
    validate_config: bool = typer.Option(
        True,
        "--validate-config/--no-validate-config",
        help="Validate configuration before installation"
    ),
    orchestrated_startup: bool = typer.Option(
        False,
        "--orchestrated-startup",
        help="Use orchestrated startup sequence (recommended for OSS)"
    )
):
    """Install Artifactory using Docker."""
    # Implementation using feature flags
```

## 5. Testing Strategy

### 5.1 Unit Tests

```python
# tests/test_install_mode/test_oss_validator.py

def test_oss_validator_catches_invalid_keys():
    """Test that OSS validator catches Pro-only keys."""
    config = {
        'configVersion': 1,
        'shared': {...},
        'artifactory': {
            'primary': True,  # Invalid for OSS
            'pool': {...}     # Invalid for OSS
        }
    }
    
    validator = ArtifactoryOSSValidator()
    result = validator.validate(config)
    
    assert len(result.errors) == 2
    assert any('primary' in error for error in result.errors)
```

### 5.2 Integration Tests

```python
# tests/test_integration/test_oss_installation.py

@pytest.mark.integration
async def test_oss_installation_with_validation():
    """Test complete OSS installation with validation."""
    # Test installation flow with OSS-specific configuration
```

## 6. Migration Path

### 6.1 Backward Compatibility

- Keep existing templates as fallback
- Add deprecation warnings for old configurations
- Provide migration command: `sapo migrate-config`

### 6.2 User Communication

- Add prominent notice in README about OSS limitations
- Show warnings during installation for OSS users
- Provide clear error messages with actionable fixes

## Implementation Timeline

1. **Phase 1** (Week 1-2): Core validation and template separation
2. **Phase 2** (Week 3-4): Startup orchestration and diagnostics
3. **Phase 3** (Week 5): Documentation and testing
4. **Phase 4** (Week 6): Beta release with feature flags

## Success Metrics

- Zero validation errors for OSS installations
- 90% reduction in startup-related issues
- Clear diagnostic output for common problems
- Positive user feedback on OSS support