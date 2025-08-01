#!/bin/bash
set -e

# Docker entrypoint script for TPS application
# Handles Django and FastAPI startup with proper initialization

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Wait for database to be ready
wait_for_db() {
    log_info "Waiting for database connection..."
    
    # Check if we're using PostgreSQL
    if [[ "${DATABASE_URL:-}" == postgresql* ]] || [[ "${DB_HOST:-}" != "" ]]; then
        local host="${DB_HOST:-localhost}"
        local port="${DB_PORT:-5432}"
        
        while ! nc -z "$host" "$port"; do
            log_warn "Database not ready on $host:$port, waiting..."
            sleep 2
        done
        log_info "Database connection established"
    else
        log_info "Using SQLite database"
    fi
}

# Initialize Django application
init_django() {
    log_info "Initializing Django application..."
    
    # Run database migrations
    python manage.py migrate --noinput
    
    # Collect static files in production
    if [[ "${ENVIRONMENT:-}" == "production" ]]; then
        log_info "Collecting static files..."
        python manage.py collectstatic --noinput --clear
    fi
    
    # Create superuser if specified
    if [[ -n "${ADMIN_USERNAME:-}" ]] && [[ -n "${ADMIN_PASSWORD:-}" ]]; then
        python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='${ADMIN_USERNAME}').exists():
    User.objects.create_superuser(
        username='${ADMIN_USERNAME}',
        email='${ADMIN_EMAIL:-admin@localhost}',
        password='${ADMIN_PASSWORD}'
    )
    print("Superuser created successfully")
else:
    print("Superuser already exists")
EOF
    fi
    
    log_info "Django initialization complete"
}

# Initialize FastAPI scheduler
init_scheduler() {
    log_info "Initializing scheduler database..."
    
    # Initialize scheduler database if needed
    if [[ ! -f scheduler.db ]] || [[ "${RESET_SCHEDULER_DB:-}" == "true" ]]; then
        log_info "Creating scheduler database..."
        sqlite3 scheduler.db < database_schema.sql
        log_info "Scheduler database initialized"
    fi
}

# Health check endpoint setup
setup_health_check() {
    log_info "Setting up health check endpoints..."
    # Health check will be handled by Django views
}

# Signal handlers for graceful shutdown
trap 'log_info "Received SIGTERM, shutting down gracefully..."; kill -TERM $PID; wait $PID' TERM
trap 'log_info "Received SIGINT, shutting down gracefully..."; kill -INT $PID; wait $PID' INT

# Main execution based on command
case "$1" in
    web)
        log_info "Starting TPS web application..."
        wait_for_db
        init_django
        setup_health_check
        
        if [[ "${ENVIRONMENT:-}" == "production" ]]; then
            log_info "Starting Gunicorn server in production mode..."
            exec gunicorn tps_project.wsgi:application \
                --bind 0.0.0.0:8000 \
                --workers 4 \
                --worker-class gevent \
                --worker-connections 1000 \
                --max-requests 1000 \
                --max-requests-jitter 100 \
                --preload \
                --access-logfile - \
                --error-logfile - \
                --log-level info &
        else
            log_info "Starting Django development server..."
            exec python manage.py runserver 0.0.0.0:8000 &
        fi
        PID=$!
        wait $PID
        ;;
        
    scheduler)
        log_info "Starting TPS scheduler API..."
        init_scheduler
        
        exec python scheduler_api.py &
        PID=$!
        wait $PID
        ;;
        
    worker)
        log_info "Starting Celery worker..."
        wait_for_db
        
        exec celery -A tps_project worker \
            --loglevel=info \
            --concurrency=2 \
            --max-tasks-per-child=1000 &
        PID=$!
        wait $PID
        ;;
        
    beat)
        log_info "Starting Celery beat scheduler..."
        wait_for_db
        
        exec celery -A tps_project beat \
            --loglevel=info \
            --scheduler django_celery_beat.schedulers:DatabaseScheduler &
        PID=$!
        wait $PID
        ;;
        
    migrate)
        log_info "Running database migrations..."
        wait_for_db
        exec python manage.py migrate --noinput
        ;;
        
    collectstatic)
        log_info "Collecting static files..."
        exec python manage.py collectstatic --noinput --clear
        ;;
        
    test)
        log_info "Running test suite..."
        wait_for_db
        init_django
        exec python -m pytest
        ;;
        
    shell)
        log_info "Starting Django shell..."
        wait_for_db
        exec python manage.py shell
        ;;
        
    *)
        log_info "Executing custom command: $*"
        exec "$@"
        ;;
esac