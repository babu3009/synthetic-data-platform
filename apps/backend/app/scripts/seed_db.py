"""
Database seeding script for development and testing.
"""
import asyncio
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.db.models import (
    Project,
    Request,
    Source,
    Config,
    Artifact,
    SourceKind,
    RequestType,
    RequestStatus,
    ArtifactFormat,
)


async def create_sample_projects(db: AsyncSession) -> List[Project]:
    """Create sample projects."""
    projects_data = [
        {
            "name": "Customer Analytics",
            "owner": "admin@company.com",
            "tags": ["analytics", "customer", "production"],
        },
        {
            "name": "Financial Modeling",
            "owner": "admin@company.com", 
            "tags": ["finance", "risk", "modeling"],
        },
        {
            "name": "ML Training Data",
            "owner": "datascientist@company.com",
            "tags": ["machine-learning", "training", "development"],
        },
    ]

    projects = []
    for project_data in projects_data:
        project = Project(**project_data)
        db.add(project)
        projects.append(project)

    await db.commit()
    
    # Refresh to get IDs
    for project in projects:
        await db.refresh(project)
    
    return projects


async def create_sample_sources(db: AsyncSession, projects: List[Project]) -> List[Source]:
    """Create sample sources for projects."""
    sources_data = [
        {
            "project_id": projects[0].id,
            "kind": SourceKind.DDL,
            "storage_uri": "s3://synthetic-data/schemas/customer_schema.sql",
            "checksum": "a1b2c3d4e5f6",
        },
        {
            "project_id": projects[0].id,
            "kind": SourceKind.JSON,
            "storage_uri": "s3://synthetic-data/configs/customer_config.json",
            "checksum": "f6e5d4c3b2a1",
        },
        {
            "project_id": projects[1].id,
            "kind": SourceKind.INTROSPECTION,
            "storage_uri": "postgresql://prod-db/financial_tables",
            "checksum": "1a2b3c4d5e6f",
        },
        {
            "project_id": projects[2].id,
            "kind": SourceKind.DDL,
            "storage_uri": "s3://synthetic-data/schemas/ml_features.sql",
            "checksum": "6f5e4d3c2b1a",
        },
    ]

    sources = []
    for source_data in sources_data:
        source = Source(**source_data)
        db.add(source)
        sources.append(source)

    await db.commit()
    
    # Refresh to get IDs
    for source in sources:
        await db.refresh(source)
    
    return sources


async def create_sample_requests(db: AsyncSession, projects: List[Project]) -> List[Request]:
    """Create sample requests for projects."""
    requests_data = [
        {
            "project_id": projects[0].id,
            "type": RequestType.RELATIONAL,
            "status": RequestStatus.COMPLETED,
            "seed": 42,
            "params_json": {
                "rows": 10000,
                "relationships": True,
                "data_quality": "high",
            },
        },
        {
            "project_id": projects[0].id,
            "type": RequestType.FLAT,
            "status": RequestStatus.PENDING,
            "seed": 123,
            "params_json": {
                "rows": 5000,
                "format": "csv",
            },
        },
        {
            "project_id": projects[1].id,
            "type": RequestType.TIMESERIES,
            "status": RequestStatus.RUNNING,
            "seed": 789,
            "params_json": {
                "rows": 50000,
                "time_range": "2020-2024",
                "frequency": "daily",
            },
        },
        {
            "project_id": projects[2].id,
            "type": RequestType.RELATIONAL,
            "status": RequestStatus.FAILED,
            "seed": 456,
            "params_json": {
                "rows": 100000,
                "features": 50,
                "target_balance": 0.3,
            },
        },
    ]

    requests = []
    for request_data in requests_data:
        request = Request(**request_data)
        db.add(request)
        requests.append(request)

    await db.commit()
    
    # Refresh to get IDs
    for request in requests:
        await db.refresh(request)
    
    return requests


async def create_sample_configs(db: AsyncSession, requests: List[Request]) -> List[Config]:
    """Create sample configurations for requests."""
    configs_data = [
        {
            "request_id": requests[0].id,
            "version": 1,
            "body_json": {
                "tables": {
                    "customers": {
                        "rows": 1000,
                        "columns": {
                            "id": {"type": "uuid", "primary_key": True},
                            "name": {"type": "name", "locale": "en_US"},
                            "email": {"type": "email"},
                            "age": {"type": "integer", "min": 18, "max": 85},
                        }
                    }
                }
            },
        },
        {
            "request_id": requests[1].id,
            "version": 1,
            "body_json": {
                "columns": {
                    "transaction_id": {"type": "uuid"},
                    "amount": {"type": "decimal", "min": 1.0, "max": 10000.0},
                    "currency": {"type": "choice", "options": ["USD", "EUR", "GBP"]},
                }
            },
        },
        {
            "request_id": requests[2].id,
            "version": 1,
            "body_json": {
                "time_series": {
                    "start_date": "2020-01-01",
                    "end_date": "2024-12-31",
                    "frequency": "D",
                    "metrics": ["price", "volume", "volatility"]
                }
            },
        },
    ]

    configs = []
    for config_data in configs_data:
        config = Config(**config_data)
        db.add(config)
        configs.append(config)

    await db.commit()
    
    # Refresh to get IDs
    for config in configs:
        await db.refresh(config)
    
    return configs


async def create_sample_artifacts(db: AsyncSession, requests: List[Request]) -> List[Artifact]:
    """Create sample artifacts for completed requests."""
    artifacts_data = [
        {
            "request_id": requests[0].id,
            "format": ArtifactFormat.CSV,
            "storage_uri": "s3://synthetic-data/outputs/customers_2024_11_05.csv",
            "size_bytes": 1024000,
        },
        {
            "request_id": requests[0].id,
            "format": ArtifactFormat.PARQUET,
            "storage_uri": "s3://synthetic-data/outputs/customers_2024_11_05.parquet",
            "size_bytes": 512000,
        },
        {
            "request_id": requests[0].id,
            "format": ArtifactFormat.JSONL,
            "storage_uri": "s3://synthetic-data/outputs/customers_2024_11_05.jsonl",
            "size_bytes": 2048000,
        },
    ]

    artifacts = []
    for artifact_data in artifacts_data:
        artifact = Artifact(**artifact_data)
        db.add(artifact)
        artifacts.append(artifact)

    await db.commit()
    
    # Refresh to get IDs
    for artifact in artifacts:
        await db.refresh(artifact)
    
    return artifacts


async def seed_database():
    """Main seeding function."""
    print("🌱 Starting database seeding...")
    
    async with AsyncSessionLocal() as db:
        try:
            # Create sample data
            print("Creating sample projects...")
            projects = await create_sample_projects(db)
            print(f"✅ Created {len(projects)} projects")

            print("Creating sample sources...")
            sources = await create_sample_sources(db, projects)
            print(f"✅ Created {len(sources)} sources")

            print("Creating sample requests...")
            requests = await create_sample_requests(db, projects)
            print(f"✅ Created {len(requests)} requests")

            print("Creating sample configurations...")
            configs = await create_sample_configs(db, requests)
            print(f"✅ Created {len(configs)} configurations")

            print("Creating sample artifacts...")
            artifacts = await create_sample_artifacts(db, requests)
            print(f"✅ Created {len(artifacts)} artifacts")

            print("🎉 Database seeding completed successfully!")
            
        except Exception as e:
            print(f"❌ Error seeding database: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(seed_database())