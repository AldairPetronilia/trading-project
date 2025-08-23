---
layout: default
title: Deployment Guide
nav_order: 5
has_children: false
---

# Deployment Guide
{: .no_toc }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

This guide covers deploying the Energy Trading Project in production environments.

## Production Requirements

### System Requirements
- **OS**: Linux (Ubuntu 20.04+ recommended)
- **CPU**: 2+ cores
- **RAM**: 4GB+ (8GB recommended)
- **Storage**: 50GB+ SSD for database
- **Network**: Stable internet for ENTSO-E API access

### Software Dependencies
- **Docker Engine**: 20.10+
- **Docker Compose**: 2.0+
- **Git**: For source code management

## Docker Deployment (Recommended)

### Clone and Configure

```bash
# Clone repository
git clone https://github.com/AldairPetronilia/trading-project.git
cd trading-project

# Copy production environment template
cp .env.example .env
```

### Environment Configuration

Edit `.env` for production:

```bash
# Production Environment
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# ENTSO-E API
ENTSOE_API_TOKEN=your_production_token_here

# Database (TimescaleDB)
DB_NAME=energy_trading_prod
DB_USER=trading_user
DB_PASSWORD=secure_random_password_here
DB_HOST=timescaledb
DB_PORT=5432

# Security
SECRET_KEY=generate_secure_secret_key_here
API_KEY=your_api_key_for_external_access

# Monitoring
GRAFANA_ADMIN_PASSWORD=secure_grafana_password
```

### Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  timescaledb:
    image: timescale/timescaledb-ha:pg15-latest
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - timescale_data:/home/postgres/pgdata/data
      - ./scripts/init-db:/docker-entrypoint-initdb.d
    ports:
      - "5432:5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      interval: 30s
      timeout: 10s
      retries: 3

  energy-data-service:
    build:
      context: ./energy_data_service
      dockerfile: Dockerfile
    environment:
      - ENVIRONMENT=production
      - DB_HOST=timescaledb
    depends_on:
      timescaledb:
        condition: service_healthy
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - energy-data-service
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD}
      GF_INSTALL_PLUGINS: grafana-clock-panel
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./grafana/datasources:/etc/grafana/provisioning/datasources
    ports:
      - "3000:3000"
    depends_on:
      - timescaledb
    restart: unless-stopped

volumes:
  timescale_data:
  grafana_data:
```

### Deploy to Production

```bash
# Start production environment
docker-compose -f docker-compose.prod.yml up -d

# Check service status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f energy-data-service
```

## SSL/HTTPS Configuration

### Obtain SSL Certificate

Using Let's Encrypt with Certbot:

```bash
# Install Certbot
sudo apt update
sudo apt install snapd
sudo snap install --classic certbot

# Obtain certificate
sudo certbot certonly --standalone -d your-domain.com

# Certificate files will be in /etc/letsencrypt/live/your-domain.com/
```

### Nginx Configuration

Create `nginx/nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream energy_api {
        server energy-data-service:8000;
    }

    # Redirect HTTP to HTTPS
    server {
        listen 80;
        server_name your-domain.com;
        return 301 https://$server_name$request_uri;
    }

    # HTTPS server
    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;

        # Security headers
        add_header X-Frame-Options SAMEORIGIN;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";

        # API proxy
        location /api/ {
            proxy_pass http://energy_api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Health check
        location /health {
            proxy_pass http://energy_api;
        }

        # Documentation
        location /docs {
            proxy_pass http://energy_api;
        }
    }
}
```

## Database Management

### Backup Strategy

```bash
# Daily backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/postgresql"

docker exec timescaledb pg_dump -U $DB_USER -d $DB_NAME \
  | gzip > $BACKUP_DIR/energy_trading_$DATE.sql.gz

# Keep only last 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
```

### Database Monitoring

```bash
# Check database size
docker exec timescaledb psql -U $DB_USER -d $DB_NAME -c "
SELECT pg_size_pretty(pg_database_size('$DB_NAME')) as size;
"

# Check hypertable status
docker exec timescaledb psql -U $DB_USER -d $DB_NAME -c "
SELECT * FROM timescaledb_information.hypertables;
"

# View compression stats
docker exec timescaledb psql -U $DB_USER -d $DB_NAME -c "
SELECT * FROM timescaledb_information.compression_settings;
"
```

### Performance Tuning

```bash
# Optimize PostgreSQL settings
docker exec timescaledb psql -U $DB_USER -d $DB_NAME -c "
-- Set chunk interval to 1 day
SELECT set_chunk_time_interval('load_data', INTERVAL '1 day');

-- Enable compression after 7 days
SELECT add_compression_policy('load_data', INTERVAL '7 days');

-- Add retention policy (optional)
SELECT add_retention_policy('load_data', INTERVAL '1 year');
"
```

## Monitoring & Alerting

### Grafana Dashboard Setup

```bash
# Access Grafana
open http://your-domain.com:3000

# Login with admin credentials
# Import dashboard from grafana/dashboards/energy-data.json
```

### System Monitoring

```bash
# Monitor container resources
docker stats

# Check service health
curl -f http://your-domain.com/health || echo "Service down!"

# Monitor disk usage
df -h

# Check database connections
docker exec timescaledb psql -U $DB_USER -d $DB_NAME -c "
SELECT count(*) as active_connections
FROM pg_stat_activity
WHERE state = 'active';
"
```

### Log Management

```bash
# Centralized logging with rotation
docker run -d \
  --name logrotate \
  --restart unless-stopped \
  -v /var/lib/docker/containers:/var/lib/docker/containers:ro \
  -v /var/log:/logs \
  blacklabelops/logrotate

# View application logs
docker-compose logs -f --tail=100 energy-data-service

# Search logs for errors
docker-compose logs energy-data-service 2>&1 | grep -i error
```

## Security Hardening

### Firewall Configuration

```bash
# UFW firewall setup
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
```

### Docker Security

```bash
# Run containers as non-root user
# Add to docker-compose.yml:
user: "1000:1000"

# Use secrets for sensitive data
secrets:
  db_password:
    file: ./secrets/db_password.txt
  api_token:
    file: ./secrets/api_token.txt
```

### Environment Security

```bash
# Set secure file permissions
chmod 600 .env
chmod 600 secrets/*

# Use environment-specific configs
# Separate .env files for dev/staging/prod
```

## Scaling & High Availability

### Database Replication

```yaml
# Add read replica for scaling
timescaledb-replica:
  image: timescale/timescaledb-ha:pg15-latest
  environment:
    POSTGRES_MASTER_SERVICE: timescaledb
    POSTGRES_REPLICA_SERVICE: timescaledb-replica
  depends_on:
    - timescaledb
```

### Load Balancing

```nginx
# Multiple application instances
upstream energy_api {
    server energy-data-service-1:8000;
    server energy-data-service-2:8000;
    server energy-data-service-3:8000;
}
```

### Container Orchestration

```bash
# For production scale, consider:
# - Docker Swarm
# - Kubernetes
# - AWS ECS/Fargate
# - Google Cloud Run
```

## Disaster Recovery

### Backup Automation

```bash
# Automated backup script
#!/bin/bash
set -e

# Database backup
docker exec timescaledb pg_dump -U $DB_USER $DB_NAME | \
  gzip > "/backups/db_$(date +%Y%m%d_%H%M%S).sql.gz"

# Configuration backup
tar -czf "/backups/config_$(date +%Y%m%d_%H%M%S).tar.gz" \
  .env docker-compose.prod.yml nginx/ grafana/

# Upload to cloud storage (AWS S3, GCS, etc.)
aws s3 sync /backups/ s3://your-backup-bucket/energy-trading/
```

### Recovery Procedures

```bash
# Restore database
gunzip < backup.sql.gz | \
  docker exec -i timescaledb psql -U $DB_USER -d $DB_NAME

# Restore configuration
tar -xzf config_backup.tar.gz

# Restart services
docker-compose -f docker-compose.prod.yml up -d
```

## Maintenance

### Regular Tasks

```bash
# Weekly maintenance script
#!/bin/bash

# Update containers
docker-compose pull
docker-compose up -d

# Clean unused images
docker image prune -f

# Vacuum database
docker exec timescaledb psql -U $DB_USER -d $DB_NAME -c "VACUUM ANALYZE;"

# Check disk space
df -h | grep -E '(8[0-9]|9[0-9])%' && echo "Disk space warning!"
```

### Health Checks

```bash
# Automated health monitoring
#!/bin/bash

# Check service health
if ! curl -sf http://localhost:8000/health > /dev/null; then
    echo "Service unhealthy - restarting"
    docker-compose restart energy-data-service
fi

# Check database connectivity
if ! docker exec timescaledb pg_isready -U $DB_USER; then
    echo "Database unhealthy - investigating"
    docker-compose logs timescaledb
fi
```

---

For development setup, see the [Getting Started Guide](getting-started.html). For technical details, check the [Architecture Overview](architecture.html).
