-- Initialize the database with any required extensions or initial setup

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create initial schemas if needed
-- CREATE SCHEMA IF NOT EXISTS synthetic_data;

-- Initial setup completed
SELECT 'Database initialized successfully' as message;