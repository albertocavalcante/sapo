# JFrog Artifactory OSS Docker Deployment: Critical Learnings and Improvements for sapo-cli

## Date: July 30, 2025
## Context: Troubleshooting session with JFrog Artifactory OSS 7.111.9

## Executive Summary

During an extensive troubleshooting session, we discovered critical differences between JFrog Artifactory OSS and Pro versions that affect Docker deployments. The main issues centered around:

1. **Configuration Validation**: The OSS version has strict limitations on which configuration keys are accepted in `system.yaml`
2. **Service Startup Race Conditions**: Router and Access services have circular dependencies causing startup failures
3. **Port Mapping Confusion**: The relationship between internal services (8081) and router service (8082) is not well documented

## Key Learnings

### 1. Configuration Differences: OSS vs Pro

#### Invalid Keys in OSS Version
The following keys cause validation failures in Artifactory OSS:
```yaml
.artifactory.primary
.artifactory.pool
.artifactory.javaOpts
.artifactory.network
.artifactory.cache
.artifactory.security
.artifactory.access
.shared.database.properties
```

#### Working Minimal Configuration for OSS
```yaml
configVersion: 1
shared:
    security:
        joinKey: "<generated-join-key>"
    node:
        id: "art1"
        ip: "localhost"
        haEnabled: false
    database:
        type: postgresql
        driver: org.postgresql.Driver
        url: jdbc:postgresql://postgres:5432/artifactory
        username: artifactory
        password: <encrypted-password>
```

### 2. Service Architecture and Race Conditions

#### The Problem
- **Router Service** (port 8082 external, 8046 internal) needs Access service to be running
- **Access Service** (port 8040) tries to register with Router service
- **Result**: Circular dependency causing both services to fail

#### Current Docker Behavior
1. All services start simultaneously via `/entrypoint-artifactory.sh`
2. Router crashes when it can't connect to Access after 80 retries
3. Access keeps trying to register with the non-existent Router
4. System remains in "Starting Up..." state indefinitely

#### Root Cause
The Docker image expects a specific startup sequence that isn't enforced:
1. Access service must start first and be ready
2. Router service starts and connects to Access
3. Other services (Artifactory, Frontend) register with Router

### 3. Port Architecture Clarification

```
External Request → Port 8082 (Router) → Port 8046 (Router Internal)
                                      ↓
                                   Routes to:
                                   - Port 8081 (Artifactory)
                                   - Port 8040 (Access)
                                   - Port 8070 (Frontend)
```

When Router fails, port 8082 shows "connection reset" because nothing is listening.

## Proposed Improvements for sapo-cli

### 1. Add OSS-Specific Validation

```python
class ArtifactoryOSSValidator:
    """Validates system.yaml for OSS compatibility"""
    
    INVALID_OSS_KEYS = [
        'artifactory.primary',
        'artifactory.pool',
        'artifactory.javaOpts',
        'artifactory.network',
        'artifactory.cache',
        'artifactory.security',
        'artifactory.access',
        'shared.database.properties'
    ]
    
    REQUIRED_KEYS = [
        'configVersion',
        'shared.security.joinKey',
        'shared.node.id',
        'shared.database.type'
    ]
    
    def validate(self, config: dict, is_oss: bool = True) -> ValidationResult:
        """Validate configuration based on edition"""
        errors = []
        warnings = []
        
        if is_oss:
            # Check for invalid keys
            for key in self.INVALID_OSS_KEYS:
                if self._key_exists(config, key):
                    errors.append(f"Key '{key}' is not supported in OSS version")
            
        # Check required keys
        for key in self.REQUIRED_KEYS:
            if not self._key_exists(config, key):
                errors.append(f"Required key '{key}' is missing")
                
        return ValidationResult(errors=errors, warnings=warnings)
```

### 2. Implement Startup Orchestration

```python
class DockerStartupOrchestrator:
    """Ensures proper service startup order"""
    
    def generate_custom_entrypoint(self) -> str:
        """Generate entrypoint script that enforces startup order"""
        return '''#!/bin/bash
# Custom startup orchestration for Artifactory OSS

echo "Starting services in correct order..."

# 1. Start Access service first
$JF_PRODUCT_HOME/app/access/bin/access.sh start
echo "Waiting for Access service..."
until curl -s http://localhost:8040/access/api/v1/system/ping; do
    sleep 2
done

# 2. Start Router service
$JF_PRODUCT_HOME/app/router/bin/router.sh start
echo "Waiting for Router service..."
until curl -s http://localhost:8046/router/api/v1/system/health; do
    sleep 2
done

# 3. Continue with standard entrypoint
exec /entrypoint-artifactory.sh
'''
```

### 3. Add Healthcheck Improvements

```yaml
# docker-compose.yml.j2 improvements
healthcheck:
  test: ["CMD-SHELL", "curl -f http://localhost:8081/artifactory/api/system/ping || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 10
  start_period: 120s  # Give services time to start in order
```

### 4. Template Separation

Create separate templates:
- `system.yaml.oss.j2` - Minimal configuration for OSS
- `system.yaml.pro.j2` - Full configuration for Pro
- `docker-compose.oss.yml.j2` - OSS-specific compose file
- `docker-compose.pro.yml.j2` - Pro-specific compose file

### 5. Add Diagnostic Commands

```python
class ArtifactoryDiagnostics:
    """Diagnostic tools for troubleshooting"""
    
    def check_service_status(self):
        """Check individual service status"""
        services = {
            'access': 'http://localhost:8040/access/api/v1/system/ping',
            'router': 'http://localhost:8046/router/api/v1/system/health',
            'artifactory': 'http://localhost:8081/artifactory/api/system/ping',
            'frontend': 'http://localhost:8070/readiness'
        }
        
        for service, url in services.items():
            # Check each service independently
            
    def analyze_startup_logs(self):
        """Parse logs for common issues"""
        patterns = {
            'yaml_validation': r'yaml validation failed',
            'router_crash': r'router not running',
            'access_timeout': r'Access Service ping failed',
            'circular_dependency': r'Service registry ping failed'
        }
```

## Implementation Priority

1. **High Priority**: 
   - OSS validation to prevent invalid configurations
   - Separate templates for OSS vs Pro
   
2. **Medium Priority**:
   - Startup orchestration script
   - Enhanced healthchecks
   
3. **Low Priority**:
   - Diagnostic commands
   - Automated troubleshooting

## Testing Requirements

1. Test with clean installation (no existing data)
2. Test with existing data migration
3. Test container restart scenarios
4. Test with both PostgreSQL and Derby databases
5. Validate on different Docker versions

## Documentation Updates Needed

1. Clear explanation of OSS limitations
2. Service architecture diagram
3. Troubleshooting guide for common issues
4. Migration guide from Pro to OSS

## Future Considerations

1. **Version Detection**: Auto-detect Artifactory version and adjust configuration
2. **Progressive Enhancement**: Start with minimal config, add features as validated
3. **Rollback Capability**: Save working configurations before changes
4. **Community Templates**: Allow users to share working configurations

## Conclusion

The main issue is that sapo-cli generates configurations optimized for Artifactory Pro, which causes validation failures in OSS. By implementing edition-aware validation and configuration generation, we can prevent these issues and provide a smoother experience for OSS users.

The secondary issue of service startup race conditions requires either custom entrypoint scripts or documentation to help users understand and resolve startup failures.