-- ==============================================================================
-- Multilingual AI Meeting Platform - Initial Database Extensions & Schema Setup
-- ==============================================================================

-- Enable required PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Set timezone to UTC
SET timezone = 'UTC';

-- Log confirmation
DO $$
BEGIN
    RAISE NOTICE 'Database meeting_platform initialized with extensions: uuid-ossp, pgcrypto, vector, pg_trgm, pg_stat_statements';
END $$;
