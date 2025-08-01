# Multi-stage Dockerfile for TPS Django + FastAPI Application
# Production-ready with security and performance optimizations

# Build stage for frontend assets
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --only=production
COPY frontend/ ./
RUN npm run build

# Python build stage
FROM python:3.12-slim AS python-builder

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create and use a non-root user
RUN groupadd -r tps && useradd -r -g tps tps

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt requirements_fastapi.txt ./
RUN pip install --no-cache-dir --user -r requirements.txt -r requirements_fastapi.txt

# Production stage
FROM python:3.12-slim AS production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -r tps && useradd -r -g tps -d /app -s /bin/bash tps

# Set up application directory
WORKDIR /app
RUN chown tps:tps /app

# Copy Python packages from builder
COPY --from=python-builder /root/.local /home/tps/.local

# Copy application code
COPY --chown=tps:tps . .

# Copy built frontend assets
COPY --from=frontend-builder --chown=tps:tps /app/frontend/dist ./frontend/static/

# Create required directories and set permissions
RUN mkdir -p /app/logs /app/media /app/staticfiles && \
    chown -R tps:tps /app/logs /app/media /app/staticfiles && \
    chmod 755 /app/logs /app/media /app/staticfiles

# Switch to non-root user
USER tps

# Add user's local bin to PATH
ENV PATH="/home/tps/.local/bin:$PATH"

# Environment variables
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=tps_project.settings

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Expose ports
EXPOSE 8000 8001

# Create entrypoint script
COPY --chown=tps:tps docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["web"]