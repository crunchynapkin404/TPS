"""
Health check views for TPS application
Production-ready health monitoring endpoints
"""
from django.http import JsonResponse
from django.db import connections
from django.core.cache import cache
from django.conf import settings
import redis
import logging

logger = logging.getLogger(__name__)

def health_check(request):
    """
    Comprehensive health check endpoint for load balancers and monitoring
    Returns JSON with service status and dependencies
    """
    status = {
        'status': 'healthy',
        'services': {
            'web': 'healthy',
            'database': 'unknown',
            'redis': 'unknown',
            'scheduler': 'unknown'
        },
        'version': getattr(settings, 'VERSION', '1.0.0'),
        'environment': getattr(settings, 'ENVIRONMENT', 'unknown')
    }
    
    overall_healthy = True
    
    # Check database connectivity
    try:
        db_conn = connections['default']
        with db_conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        status['services']['database'] = 'healthy'
        logger.debug("Database health check: OK")
    except Exception as e:
        status['services']['database'] = 'unhealthy'
        overall_healthy = False
        logger.error(f"Database health check failed: {e}")
    
    # Check Redis connectivity (if configured)
    try:
        redis_host = getattr(settings, 'REDIS_HOST', 'localhost')
        redis_port = getattr(settings, 'REDIS_PORT', 6379)
        r = redis.Redis(host=redis_host, port=redis_port, socket_timeout=5)
        r.ping()
        status['services']['redis'] = 'healthy'
        logger.debug("Redis health check: OK")
    except Exception as e:
        status['services']['redis'] = 'unhealthy'
        # Redis is not critical for basic functionality
        logger.warning(f"Redis health check failed: {e}")
    
    # Check scheduler database (if exists)
    try:
        import sqlite3
        import os
        scheduler_db_path = os.path.join(settings.BASE_DIR, 'scheduler.db')
        if os.path.exists(scheduler_db_path):
            conn = sqlite3.connect(scheduler_db_path, timeout=5)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            cursor.fetchone()
            conn.close()
            status['services']['scheduler'] = 'healthy'
            logger.debug("Scheduler database health check: OK")
        else:
            status['services']['scheduler'] = 'not_found'
    except Exception as e:
        status['services']['scheduler'] = 'unhealthy'
        logger.warning(f"Scheduler database health check failed: {e}")
    
    # Set overall status
    if not overall_healthy:
        status['status'] = 'unhealthy'
        return JsonResponse(status, status=503)
    
    return JsonResponse(status)

def readiness_check(request):
    """
    Readiness check for Kubernetes/container orchestration
    Returns 200 if service is ready to serve traffic
    """
    try:
        # Basic database connectivity check
        db_conn = connections['default']
        with db_conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        return JsonResponse({'status': 'ready'})
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JsonResponse({'status': 'not_ready', 'error': str(e)}, status=503)

def liveness_check(request):
    """
    Liveness check for Kubernetes/container orchestration
    Returns 200 if service is alive (basic functionality)
    """
    return JsonResponse({
        'status': 'alive',
        'timestamp': __import__('time').time()
    })

def metrics_endpoint(request):
    """
    Basic metrics endpoint for monitoring integration
    Returns application metrics in JSON format
    """
    try:
        import psutil
        import os
        
        # Get basic system metrics
        metrics = {
            'process': {
                'pid': os.getpid(),
                'memory_usage': psutil.Process().memory_info().rss / 1024 / 1024,  # MB
                'cpu_percent': psutil.Process().cpu_percent(),
            },
            'system': {
                'memory_usage_percent': psutil.virtual_memory().percent,
                'disk_usage_percent': psutil.disk_usage('/').percent,
                'cpu_usage_percent': psutil.cpu_percent(),
            }
        }
        
        # Add database metrics if available
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM django_session")
                metrics['database'] = {
                    'active_sessions': cursor.fetchone()[0]
                }
        except Exception:
            pass
            
        return JsonResponse(metrics)
        
    except ImportError:
        # psutil not available, return basic metrics
        return JsonResponse({
            'process': {'pid': os.getpid()},
            'message': 'Install psutil for detailed metrics'
        })
    except Exception as e:
        logger.error(f"Metrics endpoint error: {e}")
        return JsonResponse({'error': 'Metrics unavailable'}, status=500)