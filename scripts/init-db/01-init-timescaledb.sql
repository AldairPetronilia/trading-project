-- TimescaleDB initialization script
-- This script runs automatically when the container starts for the first time
-- Sets up TimescaleDB extension and database-level optimizations

-- Create TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Note: Hypertable creation and compression will be handled by the application
-- since they depend on the table structure defined by SQLAlchemy models.
-- This ensures proper coordination between schema creation and TimescaleDB features.
