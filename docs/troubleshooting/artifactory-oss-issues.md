# Troubleshooting JFrog Artifactory OSS Issues

This guide helps resolve common issues when deploying JFrog Artifactory OSS using sapo-cli.

## Table of Contents
1. [Configuration Validation Errors](#configuration-validation-errors)
2. [Service Startup Failures](#service-startup-failures)
3. [Port Connection Issues](#port-connection-issues)
4. [Database Connection Problems](#database-connection-problems)
5. [Docker-Specific Issues](#docker-specific-issues)
6. [Performance Issues](#performance-issues)

## Configuration Validation Errors

### Issue: "Key is misplaced or doesn't apply at this location"

**Symptoms:**
```
yaml validation failed
The key <artifactory> is misplaced or doesnt apply at this location
```

**Cause:** Using Pro/Enterprise configuration keys in OSS version.

**Solution:**
1. Use OSS-specific configuration:
   ```bash
   sapo install --mode docker --edition oss
   ```

2. Remove invalid keys from `system.yaml`:
   - `artifactory.primary`
   - `artifactory.pool`
   - `artifactory.javaOpts`
   - `artifactory.network`
   - `artifactory.cache`
   - `artifactory.security`
   - `artifactory.access`
   - `shared.database.properties`

3. Use minimal OSS configuration:
   ```yaml
   configVersion: 1
   shared:
     security:
       joinKey: "<your-join-key>"
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

### Issue: Invalid YAML formatting

**Symptoms:**
```
yaml: line X: found character that cannot start any token
```

**Solution:**
- Ensure consistent indentation (2 spaces recommended)
- Check for special characters in values
- Quote string values containing special characters

## Service Startup Failures

### Issue: "Router not running after 80 attempts"

**Symptoms:**
```
router not running after 80 attempts
Access Service ping failed after 80 attempts
```

**Cause:** Circular dependency between Router and Access services.

**Solution:**
1. Use orchestrated startup:
   ```bash
   sapo install --mode docker --orchestrated-startup
   ```

2. Or manually start services in order:
   ```bash
   # Inside container
   /opt/jfrog/artifactory/app/access/bin/access.sh start
   # Wait for Access to be ready
   /opt/jfrog/artifactory/app/router/bin/router.sh start
   # Then start other services
   ```

3. Check service logs:
   ```bash
   docker logs artifactory 2>&1 | grep -E "(router|access)"
   ```

### Issue: Services crash on startup

**Symptoms:**
- Container restarts repeatedly
- "Artifactory failed to initialize" errors

**Solution:**
1. Check available resources:
   ```bash
   # Check memory
   docker stats
   # Ensure at least 4GB RAM available
   ```

2. Increase startup timeout in docker-compose.yml:
   ```yaml
   healthcheck:
     start_period: 180s
   ```

## Port Connection Issues

### Issue: "Connection reset by peer" on port 8082

**Symptoms:**
```
curl: (56) Recv failure: Connection reset by peer
```

**Cause:** Router service not running on port 8082.

**Solution:**
1. Check if Router is listening:
   ```bash
   docker exec artifactory netstat -tlnp | grep 8082
   ```

2. Temporary workaround - access Artifactory directly:
   ```bash
   # Change port mapping in docker-compose.yml
   ports:
     - "8082:8081"  # Map to Artifactory service directly
   ```

3. Check Router health:
   ```bash
   docker exec artifactory curl http://localhost:8046/router/api/v1/system/health
   ```

### Issue: "Session filter is not initialized"

**Symptoms:**
```json
{
  "errors": [{
    "status": 500,
    "message": "Session filter is not initialized! Thread: ..."
  }]
}
```

**Cause:** Accessing Artifactory service directly without proper initialization.

**Solution:**
- Wait for all services to fully initialize (2-3 minutes)
- Access via Router port (8082) not Artifactory port (8081)

## Database Connection Problems

### Issue: PostgreSQL connection refused

**Symptoms:**
```
Connection to postgres:5432 refused
```

**Solution:**
1. Ensure PostgreSQL container is running:
   ```bash
   docker ps | grep postgres
   ```

2. Check PostgreSQL logs:
   ```bash
   docker logs postgres
   ```

3. Verify network connectivity:
   ```bash
   docker exec artifactory ping postgres
   ```

4. Check credentials in system.yaml match docker-compose.yml

### Issue: Derby database corruption

**Symptoms:**
- "Database 'artifactory' not found" errors
- Startup failures after unexpected shutdown

**Solution:**
1. Switch to PostgreSQL (recommended):
   ```bash
   sapo install --mode docker --use-postgres
   ```

2. Or clean Derby database:
   ```bash
   rm -rf ~/.jfrog/artifactory/var/data/derby
   # Reinstall
   ```

## Docker-Specific Issues

### Issue: "Cannot connect to Docker daemon"

**Solution:**
1. Ensure Docker is running:
   ```bash
   docker info
   ```

2. Check Docker permissions:
   ```bash
   # Add user to docker group
   sudo usermod -aG docker $USER
   # Log out and back in
   ```

### Issue: "No space left on device"

**Solution:**
1. Clean Docker resources:
   ```bash
   docker system prune -a
   ```

2. Check available space:
   ```bash
   df -h /var/lib/docker
   ```

3. Use different data directory:
   ```bash
   sapo install --mode docker --data-dir /path/with/space
   ```

## Performance Issues

### Issue: Slow startup times

**Solution:**
1. Allocate more resources:
   ```yaml
   # docker-compose.yml
   services:
     artifactory:
       deploy:
         resources:
           limits:
             memory: 4G
           reservations:
             memory: 2G
   ```

2. Use SSD storage for data directory

3. Disable unnecessary services in OSS

### Issue: High memory usage

**Solution:**
1. Adjust JVM settings (Pro only)
2. Monitor with:
   ```bash
   docker stats artifactory
   ```

3. Set memory limits in Docker

## Diagnostic Commands

Run comprehensive diagnostics:
```bash
# Using sapo
sapo diagnose --path ~/.jfrog/artifactory

# Manual checks
docker exec artifactory /opt/jfrog/artifactory/app/bin/artifactoryctl status
docker exec artifactory cat /opt/jfrog/artifactory/var/log/console.log | tail -100
```

## Getting Help

If issues persist:

1. Collect diagnostic information:
   ```bash
   # System info
   uname -a
   docker version
   
   # Artifactory logs
   docker logs artifactory > artifactory.log 2>&1
   
   # Configuration
   cat ~/.jfrog/artifactory/etc/system.yaml
   ```

2. Check official documentation:
   - [JFrog Documentation](https://www.jfrog.com/confluence/display/JFROG/JFrog+Artifactory)
   - [Sapo Issues](https://github.com/yourusername/sapo/issues)

3. Common log locations inside container:
   - `/opt/jfrog/artifactory/var/log/console.log` - Main console log
   - `/opt/jfrog/artifactory/var/log/artifactory-service.log` - Service log
   - `/opt/jfrog/artifactory/var/log/router-service.log` - Router log
   - `/opt/jfrog/artifactory/var/log/access-service.log` - Access log