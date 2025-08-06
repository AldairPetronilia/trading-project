# Energy Trading Project

Welcome to the Energy Trading Project documentation! This system provides production-quality energy market data collection, processing, and storage for trading signals and analytics.

## Overview

The Energy Trading Project is a Python-based system designed to collect, process, and store energy market data from the ENTSO-E (European Network of Transmission System Operators for Electricity) API. Built with Clean Architecture principles, it provides reliable data infrastructure for energy trading operations.

### Key Features

- 🔄 **Automated Data Collection**: Continuous data fetching from ENTSO-E API
- 📊 **Gap Detection & Backfill**: Intelligent handling of missing data periods
- ⚡ **TimescaleDB Integration**: Optimized time-series storage with compression
- 🔍 **Comprehensive Monitoring**: Structured logging and health monitoring
- 🐳 **Docker Deployment**: Production-ready containerized deployment
- 📈 **Grafana Integration**: Real-time data visualization dashboards

## Architecture

The project follows Clean Architecture principles with clearly separated concerns:

- **Collectors**: Fetch raw data from external sources
- **Processors**: Transform raw data into domain models
- **Services**: Business logic orchestration and workflows
- **Repositories**: Database abstraction and queries
- **Models**: SQLAlchemy database schema definitions

## Tech Stack

- **Python 3.13+** - Latest Python version
- **FastAPI** - Modern async web framework
- **SQLAlchemy 2.0** - Async ORM with type safety
- **TimescaleDB** - PostgreSQL extension for time-series data
- **Docker** - Containerized deployment
- **uv** - Fast Python package manager

## Quick Links

- [Getting Started Guide](getting-started.md)
- [Architecture Overview](architecture.md)
- [API Documentation](api.md)
- [Deployment Guide](deployment.md)

## Project Structure

```
trading-project/
├── energy_data_service/     # Core data service
├── entsoe_client/          # ENTSO-E API client library
├── scripts/                # Database initialization scripts
└── docs/                   # Documentation (you are here!)
```

## Support

For questions, issues, or contributions:

- Check the [GitHub Issues](https://github.com/AldairPetronilia/trading-project/issues)
- Review the [API Documentation](api.md)
- Read the [Architecture Guide](architecture.md)

---

**Last Updated**: January 2025
