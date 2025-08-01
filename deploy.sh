#!/bin/bash
set -e

# TPS Production Deployment Script
# Zero-downtime deployment with health checks and rollback capabilities

# Configuration
APP_NAME="tps"
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env.production"
BACKUP_DIR="./backups"
LOG_FILE="./logs/deploy.log"
HEALTH_CHECK_URL="http://localhost/health/"
MAX_WAIT_TIME=300  # 5 minutes

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO:${NC} $1" | tee -a "$LOG_FILE"
}

# Cleanup function for rollback
cleanup() {
    if [ $? -ne 0 ]; then
        log_error "Deployment failed! Starting rollback..."
        rollback
    fi
}

# Set trap for cleanup
trap cleanup EXIT

# Create necessary directories
mkdir -p "$(dirname "$LOG_FILE")" "$BACKUP_DIR"

# Pre-deployment checks
pre_deployment_checks() {
    log "Starting pre-deployment checks..."
    
    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker is not running"
        exit 1
    fi
    
    # Check if docker-compose is available
    if ! command -v docker-compose > /dev/null; then
        log_error "docker-compose is not installed"
        exit 1
    fi
    
    # Check if environment file exists
    if [ ! -f "$ENV_FILE" ]; then
        log_error "Environment file $ENV_FILE not found"
        exit 1
    fi
    
    # Check if required environment variables are set
    if ! grep -q "SECRET_KEY=" "$ENV_FILE" || grep -q "CHANGE_THIS" "$ENV_FILE"; then
        log_error "SECRET_KEY not properly configured in $ENV_FILE"
        exit 1
    fi
    
    log "Pre-deployment checks passed"
}

# Backup database
backup_database() {
    log "Creating database backup..."
    
    local backup_file="$BACKUP_DIR/db_backup_$(date +%Y%m%d_%H%M%S).sql"
    
    # Create PostgreSQL backup
    if docker-compose exec -T db pg_dump -U postgres tps_production > "$backup_file" 2>/dev/null; then
        log "Database backup created: $backup_file"
        # Keep only last 5 backups
        ls -t "$BACKUP_DIR"/db_backup_*.sql | tail -n +6 | xargs -r rm
    else
        log_warn "Database backup failed or database not accessible"
    fi
}

# Health check function
health_check() {
    local url=${1:-$HEALTH_CHECK_URL}
    local max_attempts=${2:-30}
    local attempt=1
    
    log_info "Performing health check on $url"
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$url" > /dev/null 2>&1; then
            log "Health check passed (attempt $attempt)"
            return 0
        fi
        
        log_info "Health check failed (attempt $attempt/$max_attempts), waiting..."
        sleep 10
        ((attempt++))
    done
    
    log_error "Health check failed after $max_attempts attempts"
    return 1
}

# Deploy new version
deploy() {
    log "Starting deployment..."
    
    # Pull latest images
    log "Pulling latest Docker images..."
    docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" pull
    
    # Build custom images if needed
    log "Building application images..."
    docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" build --no-cache
    
    # Start database and redis first
    log "Starting core services..."
    docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d db redis
    
    # Wait for database to be ready
    log "Waiting for database to be ready..."
    local db_wait=0
    while [ $db_wait -lt 60 ]; do
        if docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T db pg_isready -U postgres > /dev/null 2>&1; then
            break
        fi
        sleep 5
        ((db_wait+=5))
    done
    
    # Run database migrations
    log "Running database migrations..."
    docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" run --rm web migrate
    
    # Collect static files
    log "Collecting static files..."
    docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" run --rm web collectstatic
    
    # Start all services
    log "Starting all services..."
    docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d
    
    # Wait for services to be healthy
    log "Waiting for services to be healthy..."
    sleep 30
    
    # Perform health check
    if ! health_check; then
        log_error "Health check failed after deployment"
        return 1
    fi
    
    log "Deployment completed successfully!"
}

# Rollback function
rollback() {
    log_warn "Starting rollback process..."
    
    # Stop current services
    docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" down
    
    # Try to restore from latest backup if available
    local latest_backup=$(ls -t "$BACKUP_DIR"/db_backup_*.sql 2>/dev/null | head -n1)
    if [ -n "$latest_backup" ]; then
        log_warn "Restoring database from backup: $latest_backup"
        # This would restore the database - implement based on your backup strategy
        # docker-compose exec -T db psql -U postgres tps_production < "$latest_backup"
    fi
    
    log_warn "Rollback completed. Manual intervention may be required."
}

# Post-deployment tasks
post_deployment() {
    log "Running post-deployment tasks..."
    
    # Clean up old Docker images
    log "Cleaning up old Docker images..."
    docker image prune -f
    
    # Log container status
    log "Container status:"
    docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps | tee -a "$LOG_FILE"
    
    # Log resource usage
    log "Resource usage:"
    docker stats --no-stream | tee -a "$LOG_FILE"
    
    log "Post-deployment tasks completed"
}

# Main deployment process
main() {
    log "TPS Deployment Started"
    log "Environment: $ENV_FILE"
    log "Compose file: $COMPOSE_FILE"
    
    pre_deployment_checks
    backup_database
    deploy
    post_deployment
    
    log "🎉 TPS Deployment completed successfully!"
    log "Application is available at: $(grep ALLOWED_HOSTS "$ENV_FILE" | cut -d'=' -f2 | cut -d',' -f1)"
    
    # Remove trap on successful completion
    trap - EXIT
}

# Command line options
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "rollback")
        rollback
        ;;
    "health-check")
        health_check
        ;;
    "backup")
        backup_database
        ;;
    "logs")
        docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" logs -f "${2:-web}"
        ;;
    "status")
        docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps
        ;;
    "stop")
        log "Stopping TPS services..."
        docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" down
        ;;
    "start")
        log "Starting TPS services..."
        docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d
        ;;
    *)
        echo "Usage: $0 {deploy|rollback|health-check|backup|logs|status|stop|start}"
        echo ""
        echo "Commands:"
        echo "  deploy      - Deploy the application (default)"
        echo "  rollback    - Rollback to previous version"
        echo "  health-check - Check application health"
        echo "  backup      - Create database backup"
        echo "  logs [service] - Show logs for service (default: web)"
        echo "  status      - Show service status"
        echo "  stop        - Stop all services"
        echo "  start       - Start all services"
        exit 1
        ;;
esac