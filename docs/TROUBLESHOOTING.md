# TPS Production Troubleshooting Guide

## Quick Diagnostic Commands

### Service Status
```bash
# Check all service status
./deploy.sh status

# Check specific service logs
./deploy.sh logs web
./deploy.sh logs db
./deploy.sh logs redis
./deploy.sh logs nginx

# Follow logs in real-time
docker compose logs -f web
```

### Health Checks
```bash
# Application health check
curl -f https://yourdomain.com/health/

# Database health check
docker compose exec db pg_isready -U postgres

# Redis health check
docker compose exec redis redis-cli ping

# Nginx status
docker compose exec nginx nginx -t
```

## Common Issues and Solutions

### 1. Application Won't Start

**Symptoms:**
- Container exits immediately
- Health checks failing
- "Service Unavailable" errors

**Diagnostic Steps:**
```bash
# Check container logs
docker compose logs web

# Check Django configuration
docker compose exec web python manage.py check --deploy

# Verify environment variables
docker compose exec web env | grep -E "(SECRET_KEY|DATABASE_URL|REDIS_URL)"
```

**Common Causes:**
- Missing or invalid SECRET_KEY
- Database connection issues
- Missing environment variables
- Port conflicts

**Solutions:**
```bash
# Generate new secret key
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# Test database connection
docker compose exec web python manage.py dbshell

# Recreate containers with fresh environment
docker compose down && docker compose up -d
```

### 2. Database Connection Issues

**Symptoms:**
- "Connection refused" errors
- "FATAL: password authentication failed"
- Slow database queries

**Diagnostic Steps:**
```bash
# Check database container status
docker compose ps db

# Check database logs
docker compose logs db

# Test connection from web container
docker compose exec web pg_isready -h db -p 5432 -U postgres

# Check database disk usage
docker compose exec db df -h
```

**Solutions:**
```bash
# Restart database service
docker compose restart db

# Check database configuration
docker compose exec db cat /var/lib/postgresql/data/postgresql.conf

# Run database maintenance
docker compose exec db vacuumdb -U postgres -d tps_production --analyze --verbose
```

### 3. Static Files Not Loading

**Symptoms:**
- CSS/JS files return 404
- Images not displaying
- Admin interface unstyled

**Diagnostic Steps:**
```bash
# Check static files collection
docker compose exec web python manage.py collectstatic --dry-run

# Check nginx configuration
docker compose exec nginx nginx -t

# Check static files volume
docker compose exec web ls -la /app/staticfiles/
```

**Solutions:**
```bash
# Recollect static files
docker compose exec web python manage.py collectstatic --clear --noinput

# Restart nginx
docker compose restart nginx

# Check volume mounts
docker compose down && docker compose up -d
```

### 4. Memory/Performance Issues

**Symptoms:**
- Slow response times
- High memory usage
- Container restarts

**Diagnostic Steps:**
```bash
# Check resource usage
docker stats

# Check application metrics
curl https://yourdomain.com/metrics/

# Monitor database performance
docker compose exec db top
```

**Solutions:**
```bash
# Increase worker processes (in docker-compose.yml)
# environment:
#   - GUNICORN_WORKERS=8

# Add memory limits
# deploy:
#   resources:
#     limits:
#       memory: 1G

# Optimize database
docker compose exec db vacuumdb -U postgres -d tps_production --full --analyze
```

### 5. SSL/TLS Certificate Issues

**Symptoms:**
- "Not secure" warnings
- Certificate expired errors
- Mixed content warnings

**Diagnostic Steps:**
```bash
# Check certificate expiry
openssl x509 -in ssl/server.crt -text -noout | grep "Not After"

# Test SSL configuration
curl -I https://yourdomain.com

# Check nginx SSL configuration
docker compose exec nginx nginx -t
```

**Solutions:**
```bash
# Renew SSL certificate (Let's Encrypt example)
certbot renew --nginx

# Update certificate files and restart
docker compose restart nginx

# Check SSL configuration
testssl.sh yourdomain.com
```

## Log Analysis

### Important Log Locations
```bash
# Application logs
tail -f logs/tps.log

# Error logs
tail -f logs/error.log

# Security logs
tail -f logs/security.log

# Nginx access logs
docker compose logs nginx | grep "GET\|POST"

# Database logs
docker compose logs db | grep "ERROR\|FATAL"
```

### Log Patterns to Watch For
```bash
# High error rates
grep "ERROR" logs/tps.log | wc -l

# Security incidents
grep -i "blocked\|forbidden\|unauthorized" logs/security.log

# Performance issues
grep "slow query" logs/tps.log

# Memory issues
grep -i "memory\|oom" logs/tps.log
```

## Database Maintenance

### Regular Maintenance Tasks
```bash
# Database backup
./scripts/backup.sh

# Analyze database performance
docker compose exec db pg_stat_statements

# Vacuum and analyze
docker compose exec db vacuumdb -U postgres -d tps_production --analyze

# Check database size
docker compose exec db psql -U postgres -d tps_production -c "
SELECT schemaname,
       tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

### Database Recovery
```bash
# Point-in-time recovery (if enabled)
docker compose exec db pg_basebackup -U postgres -D /backup -Ft -z

# Restore from backup
gunzip < backup.sql.gz | docker compose exec -T db psql -U postgres -d tps_production
```

## Monitoring and Alerting

### Key Metrics to Monitor
- CPU usage > 80%
- Memory usage > 85%
- Disk usage > 90%
- Response time > 2 seconds
- Error rate > 1%
- Database connections > 80% of max

### Set Up Alerts
```bash
# Prometheus alerting rules
cat > monitoring/alerts.yml << EOF
groups:
  - name: tps_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(django_http_responses_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: High error rate detected
EOF
```

## Security Monitoring

### Security Checklist
```bash
# Check for failed login attempts
grep "authentication failed" logs/security.log

# Monitor for suspicious activity
grep -i "attack\|exploit\|injection" logs/security.log

# Check SSL certificate status
curl -I https://yourdomain.com 2>&1 | grep -i "ssl\|tls"

# Verify security headers
curl -I https://yourdomain.com | grep -i "x-frame-options\|x-content-type-options"
```

### Security Incident Response
1. **Identify** - What type of incident?
2. **Contain** - Block malicious IPs
3. **Investigate** - Check logs for scope
4. **Recover** - Restore from backup if needed
5. **Document** - Record incident details

## Backup and Recovery

### Backup Verification
```bash
# Test backup integrity
./scripts/backup.sh verify

# List available backups
ls -la backups/

# Test restore process (in staging)
./scripts/backup.sh restore backup_file.sql.gz
```

### Disaster Recovery Steps
1. **Assess damage** - What's affected?
2. **Communicate** - Notify stakeholders
3. **Restore services** - From backups
4. **Verify integrity** - Check data consistency
5. **Monitor** - Watch for issues
6. **Post-mortem** - Document lessons learned

## Performance Optimization

### Database Optimization
```bash
# Identify slow queries
docker compose exec db psql -U postgres -d tps_production -c "
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
"

# Index recommendations
docker compose exec db psql -U postgres -d tps_production -c "
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE n_distinct > 100
ORDER BY n_distinct DESC;
"
```

### Application Optimization
```bash
# Profile Django views
docker compose exec web python manage.py shell -c "
from django.test.utils import override_settings
with override_settings(DEBUG=True):
    # Your profiling code here
"

# Check for memory leaks
docker stats --no-stream web
```

## Contact Information
- **Emergency Hotline**: +31-xxx-xxx-xxxx
- **On-call Engineer**: oncall@yourdomain.com
- **Technical Lead**: tech-lead@yourdomain.com
- **DevOps Team**: devops@yourdomain.com

## External Resources
- [Django Deployment Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
- [PostgreSQL Monitoring](https://www.postgresql.org/docs/current/monitoring.html)
- [Nginx Troubleshooting](https://nginx.org/en/docs/debugging_log.html)
- [Docker Best Practices](https://docs.docker.com/develop/best-practices/)

---
**Last Updated**: $(date)
**Version**: 1.0
**Maintained By**: DevOps Team