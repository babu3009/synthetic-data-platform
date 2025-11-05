"""
Apply migration directly to database.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.db.session import engine
from app.db.base import SCHEMA_NAME

async def apply_migration():
    """Apply the initial migration."""
    print("=" * 60)
    print("Applying Database Migration")
    print("=" * 60)
    print(f"\nSchema: {SCHEMA_NAME}")
    
    try:
        async with engine.begin() as conn:
            # Create schema
            print("\n1. Creating schema...")
            await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA_NAME}"))
            print(f"✓ Schema '{SCHEMA_NAME}' created")
            
            # Create projects table
            print("\n2. Creating tables...")
            await conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.projects (
                    id UUID PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    owner VARCHAR(255) NOT NULL,
                    tags JSONB,
                    settings JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
                )
            """))
            print("  ✓ projects")

            # Ensure new columns exist on projects
            await conn.execute(text(f"""
                ALTER TABLE {SCHEMA_NAME}.projects
                ADD COLUMN IF NOT EXISTS webhook_run_status_url VARCHAR(2048)
            """))
            await conn.execute(text(f"""
                ALTER TABLE {SCHEMA_NAME}.projects
                ADD COLUMN IF NOT EXISTS artifact_ttl_days INTEGER
            """))
            
            await conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS ix_{SCHEMA_NAME}_projects_name 
                ON {SCHEMA_NAME}.projects(name)
            """))
            await conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS ix_{SCHEMA_NAME}_projects_owner 
                ON {SCHEMA_NAME}.projects(owner)
            """))
            
            # Create sources table
            await conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.sources (
                    id UUID PRIMARY KEY,
                    project_id UUID NOT NULL REFERENCES {SCHEMA_NAME}.projects(id) ON DELETE CASCADE,
                    kind VARCHAR(50) NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    connection_details JSONB NOT NULL,
                    schema_info JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
                )
            """))
            print("  ✓ sources")
            
            await conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS ix_{SCHEMA_NAME}_sources_kind 
                ON {SCHEMA_NAME}.sources(kind)
            """))
            await conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS ix_{SCHEMA_NAME}_sources_project_id 
                ON {SCHEMA_NAME}.sources(project_id)
            """))
            
            # Create requests table
            await conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.requests (
                    id UUID PRIMARY KEY,
                    project_id UUID NOT NULL REFERENCES {SCHEMA_NAME}.projects(id) ON DELETE CASCADE,
                    type VARCHAR(50) NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    row_count INTEGER,
                    submitted_by VARCHAR(255) NOT NULL,
                    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    started_at TIMESTAMP WITH TIME ZONE,
                    completed_at TIMESTAMP WITH TIME ZONE,
                    error_message TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
                )
            """))
            print("  ✓ requests")
            
            await conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS ix_{SCHEMA_NAME}_requests_project_id 
                ON {SCHEMA_NAME}.requests(project_id)
            """))
            await conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS ix_{SCHEMA_NAME}_requests_status 
                ON {SCHEMA_NAME}.requests(status)
            """))
            await conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS ix_{SCHEMA_NAME}_requests_type 
                ON {SCHEMA_NAME}.requests(type)
            """))
            
            # Create configs table
            await conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.configs (
                    id UUID PRIMARY KEY,
                    request_id UUID NOT NULL REFERENCES {SCHEMA_NAME}.requests(id) ON DELETE CASCADE,
                    llm_provider VARCHAR(100) NOT NULL,
                    llm_model VARCHAR(100) NOT NULL,
                    llm_params JSONB,
                    generation_strategy JSONB NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
                )
            """))
            print("  ✓ configs")
            
            await conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS ix_{SCHEMA_NAME}_configs_request_id 
                ON {SCHEMA_NAME}.configs(request_id)
            """))
            
            # Create artifacts table
            await conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.artifacts (
                    id UUID PRIMARY KEY,
                    request_id UUID NOT NULL REFERENCES {SCHEMA_NAME}.requests(id) ON DELETE CASCADE,
                    format VARCHAR(50) NOT NULL,
                    storage_path TEXT NOT NULL,
                    size_bytes BIGINT,
                    checksum VARCHAR(64),
                    metadata JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
                )
            """))
            print("  ✓ artifacts")
            
            await conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS ix_{SCHEMA_NAME}_artifacts_format 
                ON {SCHEMA_NAME}.artifacts(format)
            """))
            await conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS ix_{SCHEMA_NAME}_artifacts_request_id 
                ON {SCHEMA_NAME}.artifacts(request_id)
            """))
            
            # Create api_keys table
            await conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.api_keys (
                    id UUID PRIMARY KEY,
                    project_id UUID NOT NULL REFERENCES {SCHEMA_NAME}.projects(id) ON DELETE CASCADE,
                    name VARCHAR(255) NOT NULL,
                    hashed_key VARCHAR(255) NOT NULL,
                    prefix VARCHAR(10) NOT NULL,
                    expires_at TIMESTAMP WITH TIME ZONE,
                    last_used_at TIMESTAMP WITH TIME ZONE,
                    is_active BOOLEAN DEFAULT TRUE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
                )
            """))
            print("  ✓ api_keys")
            
            await conn.execute(text(f"""
                CREATE UNIQUE INDEX IF NOT EXISTS ix_{SCHEMA_NAME}_api_keys_hashed_key 
                ON {SCHEMA_NAME}.api_keys(hashed_key)
            """))
            await conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS ix_{SCHEMA_NAME}_api_keys_project_id 
                ON {SCHEMA_NAME}.api_keys(project_id)
            """))
            
            # Create audit_events table
            await conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.audit_events (
                    id UUID PRIMARY KEY,
                    project_id UUID REFERENCES {SCHEMA_NAME}.projects(id) ON DELETE SET NULL,
                    action VARCHAR(100) NOT NULL,
                    actor VARCHAR(255) NOT NULL,
                    details JSONB,
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
                )
            """))
            print("  ✓ audit_events")
            
            await conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS ix_{SCHEMA_NAME}_audit_events_action 
                ON {SCHEMA_NAME}.audit_events(action)
            """))
            await conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS ix_{SCHEMA_NAME}_audit_events_actor 
                ON {SCHEMA_NAME}.audit_events(actor)
            """))
            await conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS ix_{SCHEMA_NAME}_audit_events_project_id 
                ON {SCHEMA_NAME}.audit_events(project_id)
            """))
            
            # Create alembic version table
            print("\n3. Creating Alembic version table...")
            await conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.alembic_version (
                    version_num VARCHAR(32) NOT NULL,
                    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                )
            """))
            
            # Insert version
            await conn.execute(text(f"""
                INSERT INTO {SCHEMA_NAME}.alembic_version (version_num)
                VALUES ('001_initial')
                ON CONFLICT (version_num) DO NOTHING
            """))
            print(f"✓ Alembic version table created in {SCHEMA_NAME} schema")
            
        print("\n" + "=" * 60)
        print("✅ MIGRATION SUCCESSFUL")
        print("=" * 60)
        print(f"\n All 7 tables created in '{SCHEMA_NAME}' schema:")
        print("  • projects")
        print("  • sources")
        print("  • requests")
        print("  • configs")
        print("  • artifacts")
        print("  • api_keys")
        print("  • audit_events")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        return False
    finally:
        await engine.dispose()

if __name__ == "__main__":
    success = asyncio.run(apply_migration())
    sys.exit(0 if success else 1)
