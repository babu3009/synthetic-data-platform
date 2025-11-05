"""
Tests for database models.
"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.models import (
    Project,
    Request,
    Source,
    Config,
    Artifact,
    ApiKey,
    AuditEvent,
    SourceKind,
    RequestType,
    RequestStatus,
    ArtifactFormat,
)


@pytest_asyncio.fixture
async def sample_project(db_session: AsyncSession):
    """Create a sample project for testing."""
    project = Project(
        name="Test Project",
        owner="test@example.com",
        tags=["test", "sample"],
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


class TestProject:
    """Test Project model."""
    
    @pytest_asyncio.fixture
    async def test_create_project(self, db_session: AsyncSession):
        """Test creating a project."""
        project = Project(
            name="My Project",
            owner="user@example.com",
            tags=["analytics", "test"],
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)
        
        assert project.id is not None
        assert project.name == "My Project"
        assert project.owner == "user@example.com"
        assert project.tags == ["analytics", "test"]
        assert project.created_at is not None

    @pytest_asyncio.fixture
    async def test_project_relationships(self, sample_project: Project, db_session: AsyncSession):
        """Test project relationships."""
        # Create a source
        source = Source(
            project_id=sample_project.id,
            kind=SourceKind.DDL,
            storage_uri="s3://test/schema.sql",
            checksum="abc123",
        )
        db_session.add(source)
        
        # Create a request
        request = Request(
            project_id=sample_project.id,
            type=RequestType.RELATIONAL,
            seed=42,
        )
        db_session.add(request)
        
        await db_session.commit()
        
        # Refresh and check relationships
        await db_session.refresh(sample_project)
        assert len(sample_project.sources) == 1
        assert len(sample_project.requests) == 1
        assert sample_project.sources[0].kind == SourceKind.DDL
        assert sample_project.requests[0].type == RequestType.RELATIONAL


class TestSource:
    """Test Source model."""
    
    @pytest_asyncio.fixture
    async def test_create_source(self, sample_project: Project, db_session: AsyncSession):
        """Test creating a source."""
        source = Source(
            project_id=sample_project.id,
            kind=SourceKind.JSON,
            storage_uri="s3://test/config.json",
            checksum="def456",
        )
        db_session.add(source)
        await db_session.commit()
        await db_session.refresh(source)
        
        assert source.id is not None
        assert source.project_id == sample_project.id
        assert source.kind == SourceKind.JSON
        assert source.storage_uri == "s3://test/config.json"
        assert source.checksum == "def456"
        assert source.created_at is not None


class TestRequest:
    """Test Request model."""
    
    @pytest_asyncio.fixture
    async def test_create_request(self, sample_project: Project, db_session: AsyncSession):
        """Test creating a request."""
        request = Request(
            project_id=sample_project.id,
            type=RequestType.TIMESERIES,
            seed=123,
            params_json={"rows": 1000, "frequency": "daily"},
        )
        db_session.add(request)
        await db_session.commit()
        await db_session.refresh(request)
        
        assert request.id is not None
        assert request.project_id == sample_project.id
        assert request.type == RequestType.TIMESERIES
        assert request.status == RequestStatus.PENDING
        assert request.seed == 123
        assert request.params_json == {"rows": 1000, "frequency": "daily"}
        assert request.created_at is not None
        assert request.started_at is None
        assert request.finished_at is None

    @pytest_asyncio.fixture
    async def test_request_status_updates(self, sample_project: Project, db_session: AsyncSession):
        """Test request status updates."""
        request = Request(
            project_id=sample_project.id,
            type=RequestType.FLAT,
        )
        db_session.add(request)
        await db_session.commit()
        
        # Update status to running
        request.status = RequestStatus.RUNNING
        await db_session.commit()
        await db_session.refresh(request)
        
        assert request.status == RequestStatus.RUNNING
        
        # Update status to completed
        request.status = RequestStatus.COMPLETED
        await db_session.commit()
        await db_session.refresh(request)
        
        assert request.status == RequestStatus.COMPLETED


class TestConfig:
    """Test Config model."""
    
    @pytest_asyncio.fixture
    async def test_create_config(self, sample_project: Project, db_session: AsyncSession):
        """Test creating a configuration."""
        # Create request first
        request = Request(
            project_id=sample_project.id,
            type=RequestType.RELATIONAL,
        )
        db_session.add(request)
        await db_session.commit()
        await db_session.refresh(request)
        
        # Create config
        config_body = {
            "tables": {
                "users": {
                    "rows": 1000,
                    "columns": {
                        "id": {"type": "uuid"},
                        "name": {"type": "name"},
                        "email": {"type": "email"},
                    }
                }
            }
        }
        
        config = Config(
            request_id=request.id,
            version=1,
            body_json=config_body,
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)
        
        assert config.id is not None
        assert config.request_id == request.id
        assert config.version == 1
        assert config.body_json == config_body
        assert config.created_at is not None


class TestArtifact:
    """Test Artifact model."""
    
    @pytest_asyncio.fixture
    async def test_create_artifact(self, sample_project: Project, db_session: AsyncSession):
        """Test creating an artifact."""
        # Create request first
        request = Request(
            project_id=sample_project.id,
            type=RequestType.FLAT,
            status=RequestStatus.COMPLETED,
        )
        db_session.add(request)
        await db_session.commit()
        await db_session.refresh(request)
        
        # Create artifact
        artifact = Artifact(
            request_id=request.id,
            format=ArtifactFormat.CSV,
            storage_uri="s3://test/output/data.csv",
            size_bytes=1024000,
        )
        db_session.add(artifact)
        await db_session.commit()
        await db_session.refresh(artifact)
        
        assert artifact.id is not None
        assert artifact.request_id == request.id
        assert artifact.format == ArtifactFormat.CSV
        assert artifact.storage_uri == "s3://test/output/data.csv"
        assert artifact.size_bytes == 1024000
        assert artifact.created_at is not None


class TestApiKey:
    """Test ApiKey model."""
    
    @pytest_asyncio.fixture
    async def test_create_api_key(self, sample_project: Project, db_session: AsyncSession):
        """Test creating an API key."""
        api_key = ApiKey(
            project_id=sample_project.id,
            name="Production Key",
            hashed_key="hashed_key_value_12345",
            scopes=["read", "write"],
        )
        db_session.add(api_key)
        await db_session.commit()
        await db_session.refresh(api_key)
        
        assert api_key.id is not None
        assert api_key.project_id == sample_project.id
        assert api_key.name == "Production Key"
        assert api_key.hashed_key == "hashed_key_value_12345"
        assert api_key.scopes == ["read", "write"]
        assert api_key.created_at is not None


class TestAuditEvent:
    """Test AuditEvent model."""
    
    @pytest_asyncio.fixture
    async def test_create_audit_event(self, sample_project: Project, db_session: AsyncSession):
        """Test creating an audit event."""
        event = AuditEvent(
            actor="user@example.com",
            project_id=sample_project.id,
            action="create_request",
            payload_json={"request_type": "relational", "rows": 1000},
        )
        db_session.add(event)
        await db_session.commit()
        await db_session.refresh(event)
        
        assert event.id is not None
        assert event.actor == "user@example.com"
        assert event.project_id == sample_project.id
        assert event.action == "create_request"
        assert event.payload_json == {"request_type": "relational", "rows": 1000}
        assert event.created_at is not None

    @pytest_asyncio.fixture
    async def test_create_global_audit_event(self, db_session: AsyncSession):
        """Test creating a global audit event (no project)."""
        event = AuditEvent(
            actor="admin@example.com",
            action="system_maintenance",
            payload_json={"action": "backup_database"},
        )
        db_session.add(event)
        await db_session.commit()
        await db_session.refresh(event)
        
        assert event.id is not None
        assert event.actor == "admin@example.com"
        assert event.project_id is None
        assert event.action == "system_maintenance"
        assert event.created_at is not None