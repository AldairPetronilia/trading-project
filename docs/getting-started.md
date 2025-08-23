---
layout: default
title: Getting Started
nav_order: 2
has_children: false
---

# Getting Started
{: .no_toc }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

This guide helps you set up and run the Energy Trading Project locally for development or testing.

## Prerequisites

### System Requirements
- **Python 3.13+**: Latest Python version with modern features
- **Docker Desktop**: For running TimescaleDB and other services
- **Git**: For version control
- **uv**: Modern Python package manager (faster than pip/poetry)

### Hardware Requirements
- **CPU**: 2+ cores recommended
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 10GB free space for data and containers

## Installation

### Install uv Package Manager

uv is a fast Python package manager that replaces pip, poetry, and virtualenv:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex

# Verify installation
uv --version
```

### Clone the Repository

```bash
git clone https://github.com/AldairPetronilia/trading-project.git
cd trading-project
```

### Environment Setup

```bash
# Create environment file from template
cp .env.example .env

# Install dependencies and create virtual environment
uv sync
```

This command:
- Creates a virtual environment in `.venv/`
- Installs all dependencies from `uv.lock`
- Sets up both production and development dependencies

## Configuration

### Environment Variables

Edit `.env` with your configuration:

```bash
# Development Environment
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# ENTSO-E API Configuration
ENTSOE_API_TOKEN=your_entso_e_token_here

# Database Configuration (TimescaleDB)
DB_NAME=energy_trading_dev
DB_USER=postgres
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5432

# Application Settings
COLLECTION_INTERVAL_MINUTES=15
MAX_RETRY_ATTEMPTS=3
BATCH_SIZE=1000

# Monitoring
GRAFANA_ADMIN_PASSWORD=admin123
```

### Get ENTSO-E API Token

1. Visit [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/)
2. Register for an account
3. Generate an API token
4. Add token to your `.env` file

## Running the Application

### Start Database Services

```bash
# Start TimescaleDB with Docker
docker-compose up -d timescaledb

# Wait for database to initialize (first time only)
sleep 30

# Verify database is running
docker-compose logs timescaledb
```

### Initialize Database Schema

```bash
# Run database migrations
uv run python energy_data_service/scripts/init_db.py

# Verify tables were created
uv run python energy_data_service/scripts/check_db.py
```

### Start the Application

#### Option 1: Direct Python Execution
```bash
# Run the main application
uv run python energy_data_service/main.py
```

#### Option 2: FastAPI Development Server (Recommended)
```bash
# Run with auto-reload for development
uv run uvicorn energy_data_service.app.api.app:app --reload --host 0.0.0.0 --port 8000
```

#### Option 3: Full Docker Stack
```bash
# Run everything in Docker
docker-compose up -d

# View logs
docker-compose logs -f energy-data-service
```

### Verify Installation

Check that services are running:

```bash
# Application health check
curl http://localhost:8000/health

# Database connection test
uv run python -c "from energy_data_service.app.database import engine; print('DB connected!' if engine else 'DB failed')"

# View collected data (after a few minutes)
uv run python energy_data_service/scripts/query_latest_data.py
```

## Development Workflow

### Code Quality Tools

```bash
# Run all quality checks
pre-commit run --all-files

# Individual commands
uv run ruff check .           # Linting
uv run ruff format .          # Formatting
uv run mypy .                 # Type checking
```

### Testing

```bash
# Run all tests
uv run pytest

# Run only unit tests (fast)
uv run pytest tests/app/

# Run only integration tests
uv run pytest tests/integration/

# Run with coverage report
uv run pytest --cov=energy_data_service
```

### Database Operations

```bash
# View database status
docker exec -it trading-project-timescaledb-1 psql -U postgres -d energy_trading_dev

# Common SQL queries
\dt                          # List tables
\d+ load_data               # Describe table structure
SELECT COUNT(*) FROM load_data;  # Count records

# Backup database
docker exec trading-project-timescaledb-1 pg_dump -U postgres energy_trading_dev > backup.sql

# Restore database
docker exec -i trading-project-timescaledb-1 psql -U postgres energy_trading_dev < backup.sql
```

## Core Commands Reference

### Project Management
```bash
uv sync                      # Install/update dependencies
uv add <package>             # Add new dependency
uv remove <package>          # Remove dependency
uv run <command>             # Run command in project environment
```

### Service Management
```bash
docker-compose up -d         # Start all services
docker-compose down          # Stop all services
docker-compose logs <service> # View service logs
docker-compose ps            # List running services
```

### Data Collection
```bash
# Manual data collection
uv run python energy_data_service/scripts/collect_now.py

# Backfill missing data
uv run python energy_data_service/scripts/backfill.py --days 7

# Check for data gaps
uv run python energy_data_service/scripts/find_gaps.py
```

## Monitoring and Visualization

### Grafana Dashboard

1. Open http://localhost:3000
2. Login with admin/admin (change on first login)
3. Import dashboard from `grafana/dashboards/energy-data.json`
4. View real-time energy data metrics

### Application Logs

```bash
# Follow application logs
docker-compose logs -f energy-data-service

# View structured logs
tail -f logs/energy_data_service.json | jq '.'

# Filter logs by level
tail -f logs/energy_data_service.json | jq 'select(.level == "ERROR")'
```

## Troubleshooting

### Common Issues

#### Database Connection Failed
```bash
# Check if TimescaleDB is running
docker-compose ps timescaledb

# Restart database service
docker-compose restart timescaledb

# Check database logs
docker-compose logs timescaledb
```

#### ENTSO-E API Errors
```bash
# Verify API token
curl "https://web-api.tp.entsoe.eu/api?documentType=A65&processType=A16&outBiddingZone_Domain=10Y1001A1001A83F&periodStart=202501011000&periodEnd=202501011100&securityToken=YOUR_TOKEN"

# Check rate limiting in logs
docker-compose logs energy-data-service | grep "rate limit"
```

#### Permission Errors
```bash
# Fix Docker permissions (Linux/macOS)
sudo chown -R $USER:$USER .

# Reset uv environment
rm -rf .venv
uv sync
```

### Performance Optimization

```bash
# Optimize TimescaleDB (run once)
docker exec trading-project-timescaledb-1 psql -U postgres -d energy_trading_dev -c "
SELECT set_chunk_time_interval('load_data', INTERVAL '1 day');
SELECT add_compression_policy('load_data', INTERVAL '7 days');
"

# Monitor database performance
docker exec trading-project-timescaledb-1 psql -U postgres -d energy_trading_dev -c "
SELECT * FROM timescaledb_information.chunks WHERE hypertable_name = 'load_data';
"
```

## Next Steps

Once you have the system running:

1. **Explore the Data**: Use Grafana dashboards to visualize collected energy data
2. **Understand Architecture**: Read the [Architecture Guide](architecture.html) for system design
3. **API Integration**: Check [API Documentation](api.html) for programmatic access
4. **Production Deployment**: Follow [Deployment Guide](deployment.html) for production setup

---

Need help? Check the [troubleshooting section](#troubleshooting) or open an issue on [GitHub](https://github.com/AldairPetronilia/trading-project/issues).
