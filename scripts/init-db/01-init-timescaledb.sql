-- Minimal initialization script for TimescaleDB
-- This script runs automatically when the container starts for the first time
-- Only creates the TimescaleDB extension - everything else will be done programmatically

-- Create TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- That's it! Everything else (schemas, tables, permissions) will be handled
-- by SQLAlchemy models and Alembic migrations in the application code
