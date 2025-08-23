---
layout: default
title: API Documentation
nav_order: 4
has_children: false
---

# API Documentation
{: .no_toc }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

The Energy Trading Project provides RESTful APIs for accessing energy market data and system operations.

## Base URL

```
http://localhost:8000  # Development
https://your-domain.com  # Production
```

## Authentication

Currently, the API is designed for internal use. External authentication will be added in future versions.

## Endpoints

### Health & Status

#### `GET /health`
Check application health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-06T12:00:00Z",
  "database": "connected",
  "last_collection": "2025-01-06T11:55:00Z"
}
```

### Energy Data

#### `GET /api/v1/energy-data/latest`
Get the most recent energy data points.

**Parameters:**
- `area_code` (optional): Filter by geographic area
- `data_type` (optional): Filter by data type
- `limit` (optional): Number of records (default: 100)

**Response:**
```json
{
  "data": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "area_code": "DE",
      "time_interval": "2025-01-06T11:00:00Z",
      "value_mwh": 45678.5,
      "data_type": "LOAD",
      "created_at": "2025-01-06T11:15:00Z"
    }
  ],
  "count": 1,
  "area_codes": ["DE", "FR", "ES"],
  "time_range": {
    "start": "2025-01-06T10:00:00Z",
    "end": "2025-01-06T11:00:00Z"
  }
}
```

#### `GET /api/v1/energy-data/aggregated`
Get aggregated energy data over time periods.

**Parameters:**
- `area_code` (required): Geographic area
- `start_date` (required): Start date (ISO format)
- `end_date` (required): End date (ISO format)
- `interval` (optional): Aggregation interval ('hour', 'day', 'week')
- `data_type` (optional): Filter by data type

**Response:**
```json
{
  "data": [
    {
      "time_bucket": "2025-01-06T00:00:00Z",
      "area_code": "DE",
      "avg_value_mwh": 42500.0,
      "min_value_mwh": 38000.0,
      "max_value_mwh": 48000.0,
      "data_points": 24
    }
  ],
  "aggregation": {
    "interval": "day",
    "area_code": "DE",
    "data_type": "LOAD"
  },
  "period": {
    "start": "2025-01-06T00:00:00Z",
    "end": "2025-01-06T23:59:59Z"
  }
}
```

### System Operations

#### `POST /api/v1/collection/trigger`
Manually trigger data collection.

**Request Body:**
```json
{
  "area_codes": ["DE", "FR"],
  "start_date": "2025-01-06T00:00:00Z",
  "end_date": "2025-01-06T23:59:59Z",
  "force": false
}
```

**Response:**
```json
{
  "job_id": "job_123456",
  "status": "started",
  "estimated_completion": "2025-01-06T12:05:00Z"
}
```

#### `GET /api/v1/collection/status/{job_id}`
Check collection job status.

**Response:**
```json
{
  "job_id": "job_123456",
  "status": "completed",
  "progress": 100,
  "records_collected": 1440,
  "started_at": "2025-01-06T12:00:00Z",
  "completed_at": "2025-01-06T12:03:45Z"
}
```

### Backfill Operations

#### `GET /api/v1/backfill/gaps`
Identify data gaps that need backfilling.

**Parameters:**
- `area_code` (optional): Filter by area
- `days_back` (optional): How many days to check (default: 7)

**Response:**
```json
{
  "gaps": [
    {
      "area_code": "DE",
      "start_date": "2025-01-05T14:00:00Z",
      "end_date": "2025-01-05T16:00:00Z",
      "duration_hours": 2,
      "priority": "high"
    }
  ],
  "summary": {
    "total_gaps": 1,
    "total_missing_hours": 2,
    "areas_affected": ["DE"]
  }
}
```

#### `POST /api/v1/backfill/start`
Start backfill operation for identified gaps.

**Request Body:**
```json
{
  "area_codes": ["DE"],
  "start_date": "2025-01-05T00:00:00Z",
  "end_date": "2025-01-05T23:59:59Z",
  "priority": "normal"
}
```

**Response:**
```json
{
  "backfill_id": "bf_789012",
  "status": "queued",
  "estimated_duration": "15 minutes",
  "periods_to_fill": 5
}
```

## Data Types

### Energy Data Types
- `LOAD`: Energy consumption
- `GENERATION`: Energy production
- `CROSS_BORDER_FLOW`: Energy exchange between areas

### Area Codes
Standard ENTSO-E area codes:
- `DE`: Germany
- `FR`: France
- `ES`: Spain
- `IT`: Italy
- `NL`: Netherlands
- And more...

## Error Responses

### 400 Bad Request
```json
{
  "error": "validation_error",
  "message": "Invalid area_code parameter",
  "details": {
    "field": "area_code",
    "provided": "INVALID",
    "allowed": ["DE", "FR", "ES", "IT", "NL"]
  }
}
```

### 404 Not Found
```json
{
  "error": "not_found",
  "message": "No data found for the specified parameters",
  "suggestion": "Try expanding the date range or checking different area codes"
}
```

### 500 Internal Server Error
```json
{
  "error": "internal_error",
  "message": "Data collection service temporarily unavailable",
  "retry_after": 300
}
```

## Rate Limiting

- **Rate Limit**: 100 requests per minute per IP
- **Headers**:
  - `X-RateLimit-Limit`: Request limit
  - `X-RateLimit-Remaining`: Remaining requests
  - `X-RateLimit-Reset`: Reset timestamp

## SDKs and Libraries

### Python Client
```python
from trading_project_client import EnergyDataClient

client = EnergyDataClient(base_url="http://localhost:8000")
data = client.get_latest_data(area_code="DE", limit=50)
```

### JavaScript/Node.js
```javascript
import { EnergyDataAPI } from 'trading-project-js';

const api = new EnergyDataAPI('http://localhost:8000');
const data = await api.getLatestData({ areaCode: 'DE', limit: 50 });
```

## OpenAPI Documentation

Interactive API documentation is available at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

## Webhooks (Planned)

Future versions will support webhooks for real-time notifications:
- Data collection completion
- Gap detection alerts
- System health changes

---

For more technical details, see the [Architecture Overview](architecture.html) or [Getting Started Guide](getting-started.html).
