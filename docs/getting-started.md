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

This guide helps you set up and run the project locally in minutes.

### Prerequisites
- Python 3.13+
- Docker
- Git
- uv (Python package manager)

### Install uv
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex
```

### 1) Clone & setup
```bash
git clone https://github.com/AldairPetronilia/trading-project.git
cd trading-project
cp .env.example .env
uv sync
```

### 2) Configure environment
Edit `.env` with your settings (ENTSO-E token, DB credentials, etc.).

### 3) Start services
```bash
docker-compose up -d timescaledb
sleep 30
```

### 4) Run the app
```bash
uv run python energy_data_service/main.py
# or
uv run uvicorn energy_data_service.app.api.app:app --reload
```

> ✅ Data collection starts automatically every 15 minutes when the app is running.

See also: [Architecture](architecture.html), [API](api.html), and [Deployment](deployment.html).
