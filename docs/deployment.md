# Deployment Guide

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

### 1. Clone and Configure

```bash
# Clone repository
git clone https://github.com/AldairPetronilia/trading-project.git
cd trading-project

# Copy production environment template
cp .env.example .env
```

### 2. Environment Configuration

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

### 3. Production Docker Compose

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

### 4. Deploy to Production

```bash
# Start production environment
docker-compose -f docker-compose.prod.yml up -d

# Check service status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f energy-data-service
```

## SSL/HTTPS Configuration

### 1. Obtain SSL Certificate

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

### 2. Nginx Configuration

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
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"

# Check TimescaleDB compression
docker exec timescaledb psql -U $DB_USER -d $DB_NAME -c "
SELECT
    hypertable_name,
    compression_enabled,
    compressed_chunks,
    uncompressed_chunks
FROM timescaledb_information.hypertables;
"
```

## Monitoring & Alerting

### Application Monitoring

```bash
# Health check endpoint
curl https://your-domain.com/health

# Prometheus metrics (if enabled)
curl https://your-domain.com/metrics
```

### Log Management

```bash
# Centralized logging with Docker
version: '3.8'
services:
  fluentd:
    image: fluent/fluentd:v1.14-debian-1
    volumes:
      - ./fluentd/fluent.conf:/fluentd/etc/fluent.conf
      - ./logs:/var/log
    ports:
      - "24224:24224"

  energy-data-service:
    logging:
      driver: fluentd
      options:
        fluentd-address: fluentd:24224
        tag: energy-service
```

## Performance Optimization

### Database Tuning

Update PostgreSQL configuration in `postgresql.conf`:

```ini
# Memory settings
shared_buffers = 1GB                    # 25% of RAM
effective_cache_size = 3GB              # 75% of RAM
work_mem = 64MB                         # For sorting operations

# TimescaleDB specific
timescaledb.max_background_workers = 8
max_worker_processes = 16

# Connection settings
max_connections = 100
```

### Application Scaling

For high-load scenarios:

```yaml
# Scale horizontally
version: '3.8'
services:
  energy-data-service:
    deploy:
      replicas: 3
    ports:
      - "8000-8002:8000"

  nginx:
    # Load balance between replicas
    upstream energy_api {
        server energy-data-service:8000;
        server energy-data-service:8001;
        server energy-data-service:8002;
    }
```

## Security Hardening

### System Security

```bash
# Firewall configuration
sudo ufw enable
sudo ufw allow 22      # SSH
sudo ufw allow 80      # HTTP
sudo ufw allow 443     # HTTPS

# Fail2ban for SSH protection
sudo apt install fail2ban
sudo systemctl enable fail2ban
```

### Application Security

```bash
# Environment variables security
chmod 600 .env

# Container security scanning
docker scan energy_data_service:latest

# Regular updates
docker-compose pull
docker-compose up -d
```

## Maintenance Procedures

### Regular Maintenance Tasks

```bash
#!/bin/bash
# maintenance.sh - Run weekly

# Update containers
docker-compose pull
docker-compose up -d

# Clean up old images
docker image prune -f

# Database maintenance
docker exec timescaledb psql -U $DB_USER -d $DB_NAME -c "VACUUM ANALYZE;"

# Log rotation
find ./logs -name "*.log" -mtime +30 -delete

# Backup verification
latest_backup=$(ls -t /backups/postgresql/*.sql.gz | head -1)
if [ -z "$latest_backup" ]; then
    echo "ERROR: No recent backup found"
    exit 1
fi
```

## Troubleshooting

### Common Issues

**Service won't start:**
```bash
# Check logs
docker-compose logs energy-data-service

# Check resource usage
docker stats

# Verify database connection
docker exec timescaledb pg_isready
```

**High memory usage:**
```bash
# Monitor container resources
docker stats --no-stream

# Check TimescaleDB memory
docker exec timescaledb psql -U $DB_USER -d $DB_NAME -c "
SELECT name, setting, unit
FROM pg_settings
WHERE name IN ('shared_buffers', 'work_mem', 'maintenance_work_mem');
"
```

**API response issues:**
```bash
# Test endpoints
curl -I https://your-domain.com/health
curl https://your-domain.com/api/v1/energy-data/latest?limit=1

# Check nginx logs
docker-compose logs nginx
```

## Recovery Procedures

### Database Recovery

```bash
# Restore from backup
gunzip < /backups/postgresql/energy_trading_20250106_120000.sql.gz | \
  docker exec -i timescaledb psql -U $DB_USER -d $DB_NAME
```

### Full System Recovery

```bash
# Complete system restoration
git pull origin main
docker-compose down
docker volume rm $(docker volume ls -q)
docker-compose up -d
# Restore database from backup
```

---

For development setup, see the [Getting Started Guide](getting-started.md). For system architecture details, check the [Architecture Overview](architecture.md).
