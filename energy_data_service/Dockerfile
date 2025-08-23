FROM python:3.13-slim-bookworm

# Install system dependencies for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install UV
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy workspace configuration files (build context is project root)
COPY pyproject.toml ./
COPY uv.lock ./

# Copy workspace packages
COPY entsoe_client/ ./entsoe_client/
COPY energy_data_service/ ./energy_data_service/

# Change to energy_data_service directory and install dependencies
WORKDIR /app/energy_data_service
RUN uv sync

# Run the application
CMD ["uv", "run", "python", "main.py"]
