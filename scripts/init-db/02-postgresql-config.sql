-- PostgreSQL configuration optimizations for production
-- This script configures PostgreSQL for optimal storage and performance

-- Optimize WAL settings for smaller storage footprint
-- Reduce WAL file retention for development/small datasets
ALTER SYSTEM SET max_wal_size = '128MB';
ALTER SYSTEM SET min_wal_size = '32MB';

-- Increase checkpoint frequency to clean up WAL files more often
ALTER SYSTEM SET checkpoint_timeout = '5min';

-- Optimize for time-series workload
ALTER SYSTEM SET checkpoint_completion_target = 0.9;

-- Apply settings
SELECT pg_reload_conf();
