#!/bin/bash

# Script to run mypy consistently across the project structure
# Usage: ./scripts/run-mypy.sh [target]

set -e

# Default to checking both services if no target specified
TARGET="${1:-all}"

case "$TARGET" in
    "energy_data_service"|"eds")
        echo "Running mypy on energy_data_service..."
        cd energy_data_service && uv run mypy app/
        ;;
    "entsoe_client"|"client")
        echo "Running mypy on entsoe_client..."
        cd entsoe_client && uv run mypy src/
        ;;
    "all")
        echo "Running mypy on energy_data_service..."
        cd energy_data_service && uv run mypy app/
        echo -e "\nRunning mypy on entsoe_client..."
        cd ../entsoe_client && uv run mypy src/
        ;;
    *)
        echo "Usage: $0 [energy_data_service|entsoe_client|all]"
        exit 1
        ;;
esac
