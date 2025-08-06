# Getting Started

This guide will help you set up and run the Energy Trading Project locally.

## Prerequisites

- **Python 3.13+**
- **Docker** and **Docker Compose**
- **Git**
- **uv** (Python package manager)

### Install uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Quick Setup

### 1. Clone the Repository

```bash
git clone https://github.com/AldairPetronilia/trading-project.git
cd trading-project
```

### 2. Environment Setup

```bash
# Install dependencies
uv sync

# Copy environment template
cp .env.example .env
```

### 3. Configure Environment Variables

Edit `.env` file with your settings:

```bash
# ENTSO-E API Configuration
ENTSOE_API_TOKEN=your_entsoe_api_token_here

# Database Configuration
DB_NAME=energy_trading
DB_USER=postgres
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5432

# Application Settings
LOG_LEVEL=INFO
ENVIRONMENT=development
```

### 4. Start Database

```bash
# Start TimescaleDB with Docker
docker-compose up -d timescaledb

# Wait for database to be ready (30 seconds)
sleep 30
```

### 5. Run the Application

```bash
# Run the energy data service
uv run python energy_data_service/main.py

# Or run with FastAPI server (if implemented)
uv run uvicorn energy_data_service.app.api.app:app --reload
```

## Getting an ENTSO-E API Token

1. Visit [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/)
2. Register for an account
3. Request an API token from your account settings
4. Add the token to your `.env` file

## Testing the Setup

### Run Tests

```bash
# Run all tests
uv run pytest

# Run only unit tests
uv run pytest tests/app/

# Run integration tests (requires database)
uv run pytest tests/integration/
```

### Check Data Collection

```bash
# Check application logs
tail -f logs/app.log

# Verify database connection
docker-compose exec timescaledb psql -U postgres -d energy_trading -c "SELECT NOW();"
```

## Development Workflow

### Code Quality Checks

```bash
# Run pre-commit hooks
pre-commit run --all-files

# Manual quality checks
uv run ruff check .
uv run mypy .
```

### Database Management

```bash
# Connect to database
docker-compose exec timescaledb psql -U postgres -d energy_trading

# View collected data
SELECT area_code, time_interval, value_mwh
FROM load_data
ORDER BY time_interval DESC
LIMIT 10;
```

### Monitoring with Grafana

```bash
# Start Grafana dashboard
docker-compose up -d grafana

# Access dashboard at http://localhost:3000
# Default login: admin/admin
```

## Common Commands

```bash
# Full development environment
docker-compose up -d

# Restart specific service
docker-compose restart energy-data-service

# View service logs
docker-compose logs -f energy-data-service

# Clean everything
docker-compose down -v
```

## Troubleshooting

### Database Connection Issues
```bash
# Check database status
docker-compose ps timescaledb

# View database logs
docker-compose logs timescaledb
```

### Missing Dependencies
```bash
# Reinstall dependencies
uv sync --refresh
```

### API Token Issues
- Verify token in `.env` file
- Check ENTSO-E API rate limits
- Ensure token has proper permissions

## Next Steps

- [Architecture Overview](architecture.md) - Understand the system design
- [API Documentation](api.md) - Explore available endpoints
- [Deployment Guide](deployment.md) - Deploy to production

---

Need help? Check the [main documentation](index.md) or open an issue on GitHub.
