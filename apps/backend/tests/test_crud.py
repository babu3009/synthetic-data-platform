"""
Tests for CRUD operations.
"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.db.models import RequestType, RequestStatus


@pytest_asyncio.fixture
async def sample_project_data():
    """Sample project data for testing."""
    return schemas.ProjectCreate(
        name="Test CRUD Project",
        owner="crud@example.com",
        tags=["crud", "test"],
    )


class TestProjectCRUD:
    """Test Project CRUD operations."""
    
    @pytest_asyncio.fixture
    async def test_create_project(self, db_session: AsyncSession, sample_project_data):
        """Test creating a project via CRUD."""
        project = await crud.project.create(db=db_session, obj_in=sample_project_data)
        
        assert project.id is not None
        assert project.name == sample_project_data.name
        assert project.owner == sample_project_data.owner
        assert project.tags == sample_project_data.tags

    @pytest_asyncio.fixture
    async def test_get_project(self, db_session: AsyncSession, sample_project_data):
        """Test getting a project by ID."""
        # Create project
        created_project = await crud.project.create(db=db_session, obj_in=sample_project_data)
        
        # Get project
        fetched_project = await crud.project.get(db=db_session, id=created_project.id)
        
        assert fetched_project is not None
        assert fetched_project.id == created_project.id
        assert fetched_project.name == created_project.name

    @pytest_asyncio.fixture
    async def test_get_projects_by_owner(self, db_session: AsyncSession, sample_project_data):
        """Test getting projects by owner."""
        # Create multiple projects
        project1 = await crud.project.create(db=db_session, obj_in=sample_project_data)
        
        project2_data = schemas.ProjectCreate(
            name="Another Project",
            owner=sample_project_data.owner,
            tags=["other"],
        )
        project2 = await crud.project.create(db=db_session, obj_in=project2_data)
        
        # Get projects by owner
        projects = await crud.project.get_by_owner(
            db=db_session, owner=sample_project_data.owner
        )
        
        assert len(projects) == 2
        project_ids = {p.id for p in projects}
        assert project1.id in project_ids
        assert project2.id in project_ids

    @pytest_asyncio.fixture
    async def test_update_project(self, db_session: AsyncSession, sample_project_data):
        """Test updating a project."""
        # Create project
        project = await crud.project.create(db=db_session, obj_in=sample_project_data)
        
        # Update project
        update_data = schemas.ProjectUpdate(
            name="Updated Project Name",
            tags=["updated", "test"],
        )
        updated_project = await crud.project.update(
            db=db_session, db_obj=project, obj_in=update_data
        )
        
        assert updated_project.name == "Updated Project Name"
        assert updated_project.tags == ["updated", "test"]
        assert updated_project.owner == sample_project_data.owner  # Unchanged

    @pytest_asyncio.fixture
    async def test_delete_project(self, db_session: AsyncSession, sample_project_data):
        """Test deleting a project."""
        # Create project
        project = await crud.project.create(db=db_session, obj_in=sample_project_data)
        project_id = project.id
        
        # Delete project
        deleted_project = await crud.project.remove(db=db_session, id=project_id)
        
        assert deleted_project is not None
        assert deleted_project.id == project_id
        
        # Verify project is deleted
        fetched_project = await crud.project.get(db=db_session, id=project_id)
        assert fetched_project is None


class TestRequestCRUD:
    """Test Request CRUD operations."""
    
    @pytest_asyncio.fixture
    async def test_project(self, db_session: AsyncSession):
        """Create a test project."""
        project_data = schemas.ProjectCreate(
            name="Request Test Project",
            owner="request@example.com",
            tags=["request", "test"],
        )
        return await crud.project.create(db=db_session, obj_in=project_data)
    
    @pytest_asyncio.fixture
    async def test_create_request(self, db_session: AsyncSession, test_project):
        """Test creating a request via CRUD."""
        request_data = schemas.RequestCreate(
            type=RequestType.RELATIONAL,
            seed=42,
            params_json={"rows": 1000, "tables": ["users", "orders"]},
        )
        
        request = await crud.request.create_with_project(
            db=db_session, obj_in=request_data, project_id=test_project.id
        )
        
        assert request.id is not None
        assert request.project_id == test_project.id
        assert request.type == RequestType.RELATIONAL
        assert request.status == RequestStatus.PENDING
        assert request.seed == 42

    @pytest_asyncio.fixture
    async def test_get_requests_by_project(self, db_session: AsyncSession, test_project):
        """Test getting requests by project."""
        # Create multiple requests
        request_data1 = schemas.RequestCreate(type=RequestType.RELATIONAL, seed=1)
        request_data2 = schemas.RequestCreate(type=RequestType.FLAT, seed=2)
        
        request1 = await crud.request.create_with_project(
            db=db_session, obj_in=request_data1, project_id=test_project.id
        )
        request2 = await crud.request.create_with_project(
            db=db_session, obj_in=request_data2, project_id=test_project.id
        )
        
        # Get requests by project
        requests = await crud.request.get_by_project(
            db=db_session, project_id=test_project.id
        )
        
        assert len(requests) == 2
        request_ids = {r.id for r in requests}
        assert request1.id in request_ids
        assert request2.id in request_ids

    @pytest_asyncio.fixture
    async def test_get_requests_by_status(self, db_session: AsyncSession, test_project):
        """Test getting requests by status."""
        # Create requests with different statuses
        request_data = schemas.RequestCreate(type=RequestType.RELATIONAL)
        
        request1 = await crud.request.create_with_project(
            db=db_session, obj_in=request_data, project_id=test_project.id
        )
        request2 = await crud.request.create_with_project(
            db=db_session, obj_in=request_data, project_id=test_project.id
        )
        
        # Update one request to running status
        update_data = schemas.RequestUpdate(status=RequestStatus.RUNNING)
        await crud.request.update(db=db_session, db_obj=request2, obj_in=update_data)
        
        # Get pending requests
        pending_requests = await crud.request.get_by_status(
            db=db_session, status=RequestStatus.PENDING
        )
        assert len(pending_requests) == 1
        assert pending_requests[0].id == request1.id
        
        # Get running requests
        running_requests = await crud.request.get_by_status(
            db=db_session, status=RequestStatus.RUNNING
        )
        assert len(running_requests) == 1
        assert running_requests[0].id == request2.id


class TestArtifactCRUD:
    """Test Artifact CRUD operations."""
    
    @pytest_asyncio.fixture
    async def test_request(self, db_session: AsyncSession):
        """Create a test request."""
        # Create project first
        project_data = schemas.ProjectCreate(
            name="Artifact Test Project",
            owner="artifact@example.com",
            tags=["artifact", "test"],
        )
        project = await crud.project.create(db=db_session, obj_in=project_data)
        
        # Create request
        request_data = schemas.RequestCreate(
            type=RequestType.FLAT,
            status=RequestStatus.COMPLETED,
        )
        return await crud.request.create_with_project(
            db=db_session, obj_in=request_data, project_id=project.id
        )
    
    @pytest_asyncio.fixture
    async def test_create_artifact(self, db_session: AsyncSession, test_request):
        """Test creating an artifact via CRUD."""
        from app.db.models import ArtifactFormat
        
        artifact_data = schemas.ArtifactCreate(
            format=ArtifactFormat.CSV,
            storage_uri="s3://test/output/data.csv",
            size_bytes=2048000,
        )
        
        artifact = await crud.artifact.create_with_request(
            db=db_session, obj_in=artifact_data, request_id=test_request.id
        )
        
        assert artifact.id is not None
        assert artifact.request_id == test_request.id
        assert artifact.format == ArtifactFormat.CSV
        assert artifact.storage_uri == "s3://test/output/data.csv"
        assert artifact.size_bytes == 2048000

    @pytest_asyncio.fixture
    async def test_get_artifacts_by_request(self, db_session: AsyncSession, test_request):
        """Test getting artifacts by request."""
        from app.db.models import ArtifactFormat
        
        # Create multiple artifacts
        artifact_data1 = schemas.ArtifactCreate(
            format=ArtifactFormat.CSV,
            storage_uri="s3://test/data.csv",
            size_bytes=1000,
        )
        artifact_data2 = schemas.ArtifactCreate(
            format=ArtifactFormat.PARQUET,
            storage_uri="s3://test/data.parquet",
            size_bytes=800,
        )
        
        artifact1 = await crud.artifact.create_with_request(
            db=db_session, obj_in=artifact_data1, request_id=test_request.id
        )
        artifact2 = await crud.artifact.create_with_request(
            db=db_session, obj_in=artifact_data2, request_id=test_request.id
        )
        
        # Get artifacts by request
        artifacts = await crud.artifact.get_by_request(
            db=db_session, request_id=test_request.id
        )
        
        assert len(artifacts) == 2
        artifact_ids = {a.id for a in artifacts}
        assert artifact1.id in artifact_ids
        assert artifact2.id in artifact_ids