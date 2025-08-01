#!/bin/bash
set -e

# TPS Database Backup Script
# Automated backup with retention and encryption

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY:-}"
S3_BUCKET="${BACKUP_S3_BUCKET:-}"
S3_REGION="${BACKUP_S3_REGION:-eu-west-1}"
LOG_FILE="${LOG_FILE:-./logs/backup.log}"

# Database configuration
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-tps}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-postgres}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

# Create backup directory
mkdir -p "$BACKUP_DIR" "$(dirname "$LOG_FILE")"

# Generate backup filename
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/tps_backup_${TIMESTAMP}.sql"
COMPRESSED_FILE="${BACKUP_FILE}.gz"
ENCRYPTED_FILE="${COMPRESSED_FILE}.enc"

# Cleanup function
cleanup() {
    if [ -f "$BACKUP_FILE" ]; then
        rm -f "$BACKUP_FILE"
    fi
    if [ -f "$COMPRESSED_FILE" ] && [ -f "$ENCRYPTED_FILE" ]; then
        rm -f "$COMPRESSED_FILE"
    fi
}

trap cleanup EXIT

# Check dependencies
check_dependencies() {
    local deps=("pg_dump" "gzip")
    
    if [ -n "$ENCRYPTION_KEY" ]; then
        deps+=("openssl")
    fi
    
    if [ -n "$S3_BUCKET" ]; then
        deps+=("aws")
    fi
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" > /dev/null; then
            log_error "Required dependency '$dep' not found"
            exit 1
        fi
    done
}

# Test database connection
test_connection() {
    log "Testing database connection..."
    
    export PGPASSWORD="$DB_PASSWORD"
    if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" > /dev/null 2>&1; then
        log "Database connection successful"
    else
        log_error "Cannot connect to database"
        exit 1
    fi
}

# Create database backup
create_backup() {
    log "Creating database backup..."
    
    export PGPASSWORD="$DB_PASSWORD"
    
    # Create backup with custom format for faster restoration
    if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        --verbose --clean --if-exists --create \
        --format=custom --compress=9 \
        --file="$BACKUP_FILE" > /dev/null 2>&1; then
        
        local size=$(du -h "$BACKUP_FILE" | cut -f1)
        log "Database backup created: $BACKUP_FILE ($size)"
    else
        log_error "Database backup failed"
        exit 1
    fi
}

# Compress backup
compress_backup() {
    if [ ! -f "$BACKUP_FILE" ]; then
        log_error "Backup file not found: $BACKUP_FILE"
        exit 1
    fi
    
    log "Compressing backup..."
    
    if gzip -9 "$BACKUP_FILE"; then
        local size=$(du -h "$COMPRESSED_FILE" | cut -f1)
        log "Backup compressed: $COMPRESSED_FILE ($size)"
    else
        log_error "Backup compression failed"
        exit 1
    fi
}

# Encrypt backup
encrypt_backup() {
    if [ -z "$ENCRYPTION_KEY" ]; then
        log "Encryption key not provided, skipping encryption"
        return 0
    fi
    
    if [ ! -f "$COMPRESSED_FILE" ]; then
        log_error "Compressed backup file not found: $COMPRESSED_FILE"
        exit 1
    fi
    
    log "Encrypting backup..."
    
    if openssl enc -aes-256-cbc -salt -in "$COMPRESSED_FILE" -out "$ENCRYPTED_FILE" -k "$ENCRYPTION_KEY"; then
        local size=$(du -h "$ENCRYPTED_FILE" | cut -f1)
        log "Backup encrypted: $ENCRYPTED_FILE ($size)"
        rm -f "$COMPRESSED_FILE"  # Remove unencrypted version
    else
        log_error "Backup encryption failed"
        exit 1
    fi
}

# Upload to S3
upload_to_s3() {
    if [ -z "$S3_BUCKET" ]; then
        log "S3 bucket not configured, skipping upload"
        return 0
    fi
    
    local file_to_upload
    if [ -f "$ENCRYPTED_FILE" ]; then
        file_to_upload="$ENCRYPTED_FILE"
    elif [ -f "$COMPRESSED_FILE" ]; then
        file_to_upload="$COMPRESSED_FILE"
    else
        log_error "No backup file found for upload"
        exit 1
    fi
    
    log "Uploading backup to S3..."
    
    local s3_key="tps/backups/$(basename "$file_to_upload")"
    
    if aws s3 cp "$file_to_upload" "s3://$S3_BUCKET/$s3_key" --region "$S3_REGION" --storage-class STANDARD_IA; then
        log "Backup uploaded to S3: s3://$S3_BUCKET/$s3_key"
    else
        log_error "S3 upload failed"
        exit 1
    fi
}

# Clean old backups
cleanup_old_backups() {
    log "Cleaning up backups older than $RETENTION_DAYS days..."
    
    # Local cleanup
    local deleted_count=0
    find "$BACKUP_DIR" -name "tps_backup_*.sql*" -mtime +$RETENTION_DAYS -type f | while read -r file; do
        log "Deleting old backup: $(basename "$file")"
        rm -f "$file"
        ((deleted_count++))
    done
    
    if [ $deleted_count -gt 0 ]; then
        log "Deleted $deleted_count old local backups"
    fi
    
    # S3 cleanup (if configured)
    if [ -n "$S3_BUCKET" ]; then
        log "Cleaning up old S3 backups..."
        aws s3 ls "s3://$S3_BUCKET/tps/backups/" --region "$S3_REGION" | \
        awk '{print $4}' | \
        while read -r key; do
            if [ -n "$key" ]; then
                local file_date=$(echo "$key" | grep -o '[0-9]\{8\}_[0-9]\{6\}' | head -n1)
                if [ -n "$file_date" ]; then
                    local backup_date=$(date -d "${file_date:0:8} ${file_date:9:2}:${file_date:11:2}:${file_date:13:2}" +%s 2>/dev/null || echo "0")
                    local cutoff_date=$(date -d "$RETENTION_DAYS days ago" +%s)
                    
                    if [ "$backup_date" -lt "$cutoff_date" ] && [ "$backup_date" -gt "0" ]; then
                        log "Deleting old S3 backup: $key"
                        aws s3 rm "s3://$S3_BUCKET/tps/backups/$key" --region "$S3_REGION"
                    fi
                fi
            fi
        done
    fi
}

# Verify backup integrity
verify_backup() {
    local file_to_verify
    if [ -f "$ENCRYPTED_FILE" ]; then
        file_to_verify="$ENCRYPTED_FILE"
    elif [ -f "$COMPRESSED_FILE" ]; then
        file_to_verify="$COMPRESSED_FILE"
    else
        log_error "No backup file found for verification"
        exit 1
    fi
    
    log "Verifying backup integrity..."
    
    # Check file size
    local size=$(stat -c%s "$file_to_verify")
    if [ "$size" -lt 1024 ]; then  # Less than 1KB is suspicious
        log_error "Backup file seems too small: $size bytes"
        exit 1
    fi
    
    # If encrypted, try to decrypt first few bytes
    if [ -f "$ENCRYPTED_FILE" ] && [ -n "$ENCRYPTION_KEY" ]; then
        if openssl enc -aes-256-cbc -d -in "$ENCRYPTED_FILE" -k "$ENCRYPTION_KEY" | head -c 100 > /dev/null 2>&1; then
            log "Backup encryption verification successful"
        else
            log_error "Backup encryption verification failed"
            exit 1
        fi
    fi
    
    # Test gzip integrity if compressed
    if [ -f "$COMPRESSED_FILE" ]; then
        if gzip -t "$COMPRESSED_FILE" 2>/dev/null; then
            log "Backup compression verification successful"
        else
            log_error "Backup compression verification failed"
            exit 1
        fi
    fi
    
    log "Backup integrity verification completed successfully"
}

# Generate backup report
generate_report() {
    local final_file
    if [ -f "$ENCRYPTED_FILE" ]; then
        final_file="$ENCRYPTED_FILE"
    elif [ -f "$COMPRESSED_FILE" ]; then
        final_file="$COMPRESSED_FILE"
    else
        final_file="$BACKUP_FILE"
    fi
    
    local size=$(du -h "$final_file" | cut -f1)
    local checksum=$(sha256sum "$final_file" | cut -d' ' -f1)
    
    cat << EOF >> "$LOG_FILE"

=== BACKUP REPORT ===
Date: $(date)
Database: $DB_NAME
Host: $DB_HOST:$DB_PORT
Backup File: $(basename "$final_file")
Size: $size
SHA256: $checksum
Encrypted: $([ -f "$ENCRYPTED_FILE" ] && echo "Yes" || echo "No")
S3 Upload: $([ -n "$S3_BUCKET" ] && echo "Yes" || echo "No")
Status: SUCCESS
=====================

EOF

    log "Backup completed successfully!"
    log "File: $(basename "$final_file") ($size)"
    log "Checksum: $checksum"
}

# Main execution
main() {
    log "Starting TPS database backup..."
    
    check_dependencies
    test_connection
    create_backup
    compress_backup
    encrypt_backup
    upload_to_s3
    verify_backup
    cleanup_old_backups
    generate_report
    
    log "Backup process completed successfully!"
}

# Command line options
case "${1:-backup}" in
    "backup")
        main
        ;;
    "restore")
        echo "Restore functionality not implemented yet"
        echo "To restore manually:"
        echo "1. Decrypt: openssl enc -aes-256-cbc -d -in backup.sql.gz.enc -out backup.sql.gz -k \$ENCRYPTION_KEY"
        echo "2. Decompress: gunzip backup.sql.gz"
        echo "3. Restore: pg_restore -h \$DB_HOST -U \$DB_USER -d \$DB_NAME backup.sql"
        ;;
    "verify")
        verify_backup
        ;;
    "cleanup")
        cleanup_old_backups
        ;;
    *)
        echo "Usage: $0 {backup|restore|verify|cleanup}"
        exit 1
        ;;
esac