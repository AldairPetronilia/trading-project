---
layout: default
title: Architecture
nav_order: 3
has_children: false
---

# System Architecture
{: .no_toc }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

The Energy Trading Project follows Clean Architecture principles, ensuring separation of concerns, testability, and maintainability.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    External Systems                         │
├─────────────────────────────────────────────────────────────┤
│  ENTSO-E API  │  TimescaleDB  │  Grafana  │  Monitoring    │
└─────────────────┬───────────────┬──────────┬────────────────┘
                  │               │          │
┌─────────────────┼───────────────┼──────────┼────────────────┐
│                 │               │          │                │
│  ┌─────────────▼──┐  ┌─────────▼─────────┐ │                │
│  │   Collectors    │  │   Repositories   │ │                │
│  │  (Data Input)   │  │  (Data Output)   │ │                │
│  └─────────────────┘  └───────────────────┘ │                │
│           │                     ▲           │                │
│           │     ┌──────────────┐│           │                │
│           │     │              ││           │                │
│           ▼     │  ┌───────────▼┼───┐       │                │
│  ┌──────────────▼─┐│  │            │       │                │
│  │   Processors   ││  │  Services  │       │                │
│  │ (Transformation)││  │ (Business  │       │                │
│  └────────────────┘│  │   Logic)   │       │                │
│                    │  └────────────┘       │                │
│                    └───────────────────────┘                │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                    Models                               │ │
│  │              (Domain Entities)                         │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### Collectors Layer
**Purpose**: Interface with external data sources

- **`EntsoeCollector`**: Fetches energy market data from ENTSO-E API
- **Responsibilities**:
  - API authentication and rate limiting
  - Error handling and retries
  - Raw data extraction

### Processors Layer
**Purpose**: Transform raw data into domain models

- **`GlMarketDocumentProcessor`**: Converts ENTSO-E XML to typed Python objects
- **`BaseProcessor`**: Common processing patterns and validation
- **Responsibilities**:
  - Data validation and cleaning
  - Format transformation (XML → Domain Models)
  - Business rule application

### Services Layer
**Purpose**: Business logic orchestration

- **`EntsoeDataService`**: Core data collection workflows
- **`BackfillService`**: Gap detection and historical data recovery
- **`SchedulerService`**: Automated job management
- **`MonitoringService`**: Health checks and metrics collection
- **Responsibilities**:
  - Workflow coordination
  - Business rule enforcement
  - Cross-cutting concerns (logging, monitoring)

### Repositories Layer
**Purpose**: Data persistence abstraction

- **`EnergyDataRepository`**: Energy market data storage/retrieval
- **`BackfillProgressRepository`**: Backfill operation tracking
- **`CollectionMetricsRepository`**: System metrics persistence
- **`BaseRepository`**: Common database patterns
- **Responsibilities**:
  - Database abstraction
  - Query optimization
  - Transaction management

### Models Layer
**Purpose**: Domain entity definitions

- **`LoadData`**: Energy consumption/generation data points
- **`BackfillProgress`**: Historical data collection status
- **`CollectionMetrics`**: System performance metrics
- **Responsibilities**:
  - Data schema definition
  - Business invariants
  - Database mapping

## Data Flow

### Normal Collection Flow
```
1. Scheduler triggers collection
2. EntsoeDataService orchestrates workflow
3. EntsoeCollector fetches raw data from API
4. GlMarketDocumentProcessor transforms XML
5. EnergyDataRepository persists to TimescaleDB
6. MonitoringService records metrics
```

### Backfill Flow
```
1. BackfillService detects data gaps
2. Calculates missing time periods
3. EntsoeCollector fetches historical data
4. Same processing pipeline as normal flow
5. BackfillProgressRepository tracks completion
```

## Design Patterns

### Dependency Injection
- **Container**: `dependency-injector` manages all components
- **Benefits**: Loose coupling, testability, configuration management
- **Implementation**: Constructor injection throughout

### Repository Pattern
- **Abstraction**: `BaseRepository[T]` generic interface
- **Benefits**: Database agnostic, consistent API, easy testing
- **Implementation**: SQLAlchemy-based with async support

### Strategy Pattern
- **Processing**: Different processors for different data types
- **Collection**: Multiple collector implementations
- **Benefits**: Extensibility, maintainability

## Technology Stack

### Core Framework
- **Python 3.13+**: Latest language features and performance
- **SQLAlchemy 2.0**: Async ORM with type safety
- **Pydantic**: Data validation and settings management
- **dependency-injector**: Dependency management

### Data Storage
- **TimescaleDB**: PostgreSQL extension optimized for time-series
- **Features**: Compression, continuous aggregates, retention policies
- **Schema**: Hypertables partitioned by time

### Monitoring & Observability
- **structlog**: Structured logging with context
- **Grafana**: Data visualization and alerting
- **Custom Metrics**: Application performance tracking

### Development & Testing
- **uv**: Fast Python package management
- **pytest**: Testing framework with fixtures
- **testcontainers**: Integration testing with real databases
- **pre-commit**: Code quality automation

## Database Schema

### Primary Tables

**`load_data`** (Hypertable)
- `id`: Primary key
- `area_code`: Geographic region identifier
- `time_interval`: Timestamp (partition key)
- `value_mwh`: Energy value in MWh
- `data_type`: Load/generation type
- `created_at`: Record creation time

**`backfill_progress`**
- `id`: Primary key
- `area_code`: Target region
- `start_date`/`end_date`: Period boundaries
- `status`: Progress state
- `created_at`/`completed_at`: Timestamps

**`collection_metrics`**
- Performance and health metrics
- Success/failure rates
- Processing times

## Security Considerations

### API Security
- ENTSO-E token management via environment variables
- Rate limiting and exponential backoff
- Request timeout handling

### Database Security
- Connection pooling with secure credentials
- Prepared statements (SQLAlchemy ORM)
- Network isolation via Docker

### Application Security
- Input validation via Pydantic models
- Error handling without information leakage
- Structured logging without sensitive data

## Scalability & Performance

### Database Optimization
- TimescaleDB hypertables for time-series data
- Automatic compression for historical data
- Continuous aggregates for real-time analytics
- Proper indexing on time and area dimensions

### Application Performance
- Async/await throughout the pipeline
- Connection pooling for database operations
- Batch processing for bulk operations
- Configurable collection intervals

### Resource Management
- Docker containerization for isolation
- Resource limits and health checks
- Graceful shutdown handling
- Memory-efficient data processing

## Deployment Architecture

### Container Strategy
- Multi-stage Docker builds for optimization
- Service separation (app, database, monitoring)
- Health checks and restart policies

### Environment Management
- Configuration via environment variables
- Secrets management via Docker secrets
- Multiple environment support (dev/staging/prod)

---

For implementation details, see the [Getting Started Guide](getting-started.html) or explore the [API Documentation](api.html).
