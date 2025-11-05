"""
Tests for API endpoints.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas


class TestProjectsAPI:
    """Test Projects API endpoints."""
    
    @pytest_asyncio.fixture
    async def test_create_project_endpoint(self, async_client: AsyncClient):
        """Test creating a project via API."""
        project_data = {
            "name": "API Test Project",
            "owner": "api@example.com",
            "tags": ["api", "test"],
        }
        
        response = await async_client.post("/api/v1/projects/", json=project_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == project_data["name"]
        assert data["owner"] == project_data["owner"]
        assert data["tags"] == project_data["tags"]
        assert "id" in data
        assert "created_at" in data

    @pytest_asyncio.fixture
    async def test_get_projects_endpoint(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test getting projects via API."""
        # Create a project first
        project_data = schemas.ProjectCreate(
            name="Get Test Project",
            owner="get@example.com",
            tags=["get", "test"],
        )
        project = await crud.project.create(db=db_session, obj_in=project_data)
        
        # Get projects via API
        response = await async_client.get("/api/v1/projects/")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # Find our project
        our_project = next((p for p in data if p["id"] == str(project.id)), None)
        assert our_project is not None
        assert our_project["name"] == project.name

    @pytest_asyncio.fixture
    async def test_get_project_by_id_endpoint(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test getting a specific project by ID via API."""
        # Create a project first
        project_data = schemas.ProjectCreate(
            name="Single Project Test",
            owner="single@example.com",
            tags=["single"],
        )
        project = await crud.project.create(db=db_session, obj_in=project_data)
        
        # Get project by ID via API
        response = await async_client.get(f"/api/v1/projects/{project.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(project.id)
        assert data["name"] == project.name
        assert data["owner"] == project.owner

    @pytest_asyncio.fixture
    async def test_get_nonexistent_project(self, async_client: AsyncClient):
        """Test getting a non-existent project."""
        fake_id = "550e8400-e29b-41d4-a716-446655440000"
        response = await async_client.get(f"/api/v1/projects/{fake_id}")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest_asyncio.fixture
    async def test_update_project_endpoint(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test updating a project via API."""
        # Create a project first
        project_data = schemas.ProjectCreate(
            name="Update Test Project",
            owner="update@example.com",
            tags=["update"],
        )
        project = await crud.project.create(db=db_session, obj_in=project_data)
        
        # Update project via API
        update_data = {
            "name": "Updated Project Name",
            "tags": ["updated", "test"],
        }
        response = await async_client.put(f"/api/v1/projects/{project.id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Project Name"
        assert data["tags"] == ["updated", "test"]
        assert data["owner"] == project.owner  # Should remain unchanged

    @pytest_asyncio.fixture
    async def test_delete_project_endpoint(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test deleting a project via API."""
        # Create a project first
        project_data = schemas.ProjectCreate(
            name="Delete Test Project",
            owner="delete@example.com",
            tags=["delete"],
        )
        project = await crud.project.create(db=db_session, obj_in=project_data)
        
        # Delete project via API
        response = await async_client.delete(f"/api/v1/projects/{project.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(project.id)
        
        # Verify project is deleted
        get_response = await async_client.get(f"/api/v1/projects/{project.id}")
        assert get_response.status_code == 404

    @pytest_asyncio.fixture
    async def test_create_duplicate_project_name(self, async_client: AsyncClient):
        """Test creating a project with duplicate name for same owner."""
        project_data = {
            "name": "Duplicate Test",
            "owner": "duplicate@example.com",
            "tags": ["duplicate"],
        }
        
        # Create first project
        response1 = await async_client.post("/api/v1/projects/", json=project_data)
        assert response1.status_code == 200
        
        # Try to create second project with same name and owner
        response2 = await async_client.post("/api/v1/projects/", json=project_data)
        assert response2.status_code == 400
        assert "already exists" in response2.json()["detail"].lower()


class TestRequestsAPI:
    """Test Requests API endpoints."""
    
    @pytest_asyncio.fixture
    async def test_project(self, db_session: AsyncSession):
        """Create a test project for request tests."""
        project_data = schemas.ProjectCreate(
            name="Request API Test Project",
            owner="requests@example.com",
            tags=["requests", "api"],
        )
        return await crud.project.create(db=db_session, obj_in=project_data)

    @pytest_asyncio.fixture
    async def test_create_request_endpoint(self, async_client: AsyncClient, test_project):
        """Test creating a request via API."""
        request_data = {
            "type": "relational",
            "seed": 42,
            "params_json": {"rows": 1000, "tables": ["users"]},
        }
        
        response = await async_client.post(
            f"/api/v1/projects/{test_project.id}/requests/",
            json=request_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "relational"
        assert data["seed"] == 42
        assert data["status"] == "pending"
        assert data["project_id"] == str(test_project.id)

    @pytest_asyncio.fixture
    async def test_get_requests_endpoint(self, async_client: AsyncClient, test_project, db_session: AsyncSession):
        """Test getting requests for a project via API."""
        # Create a request first
        request_data = schemas.RequestCreate(
            type="flat",
            seed=123,
        )
        request = await crud.request.create_with_project(
            db=db_session, obj_in=request_data, project_id=test_project.id
        )
        
        # Get requests via API
        response = await async_client.get(f"/api/v1/projects/{test_project.id}/requests/")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # Find our request
        our_request = next((r for r in data if r["id"] == str(request.id)), None)
        assert our_request is not None
        assert our_request["type"] == "flat"

    @pytest_asyncio.fixture
    async def test_get_request_by_id_endpoint(self, async_client: AsyncClient, test_project, db_session: AsyncSession):
        """Test getting a specific request by ID via API."""
        # Create a request first
        request_data = schemas.RequestCreate(
            type="timeseries",
            seed=456,
        )
        request = await crud.request.create_with_project(
            db=db_session, obj_in=request_data, project_id=test_project.id
        )
        
        # Get request by ID via API
        response = await async_client.get(
            f"/api/v1/projects/{test_project.id}/requests/{request.id}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(request.id)
        assert data["type"] == "timeseries"
        assert data["project_id"] == str(test_project.id)

    @pytest_asyncio.fixture
    async def test_create_request_for_nonexistent_project(self, async_client: AsyncClient):
        """Test creating a request for a non-existent project."""
        fake_project_id = "550e8400-e29b-41d4-a716-446655440000"
        request_data = {
            "type": "flat",
            "seed": 789,
        }
        
        response = await async_client.post(
            f"/api/v1/projects/{fake_project_id}/requests/",
            json=request_data
        )
        
        assert response.status_code == 404
        assert "project not found" in response.json()["detail"].lower()


class TestArtifactsAPI:
    """Test Artifacts API endpoints."""
    
    @pytest_asyncio.fixture
    async def test_request_with_artifacts(self, db_session: AsyncSession):
        """Create a test request with artifacts."""
        from app.db.models import RequestType, RequestStatus, ArtifactFormat
        
        # Create project
        project_data = schemas.ProjectCreate(
            name="Artifact API Test Project",
            owner="artifacts@example.com",
            tags=["artifacts", "api"],
        )
        project = await crud.project.create(db=db_session, obj_in=project_data)
        
        # Create request
        request_data = schemas.RequestCreate(
            type=RequestType.FLAT,
            status=RequestStatus.COMPLETED,
        )
        request = await crud.request.create_with_project(
            db=db_session, obj_in=request_data, project_id=project.id
        )
        
        # Create artifact
        artifact_data = schemas.ArtifactCreate(
            format=ArtifactFormat.CSV,
            storage_uri="s3://test/artifact.csv",
            size_bytes=1024,
        )
        artifact = await crud.artifact.create_with_request(
            db=db_session, obj_in=artifact_data, request_id=request.id
        )
        
        return {"project": project, "request": request, "artifact": artifact}

    @pytest_asyncio.fixture
    async def test_get_artifacts_endpoint(self, async_client: AsyncClient, test_request_with_artifacts):
        """Test getting artifacts for a request via API."""
        request = test_request_with_artifacts["request"]
        artifact = test_request_with_artifacts["artifact"]
        
        # Get artifacts via API
        response = await async_client.get(f"/api/v1/requests/{request.id}/artifacts")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # Find our artifact
        our_artifact = next((a for a in data if a["id"] == str(artifact.id)), None)
        assert our_artifact is not None
        assert our_artifact["format"] == "csv"
        assert our_artifact["storage_uri"] == "s3://test/artifact.csv"

    @pytest_asyncio.fixture
    async def test_get_artifact_by_id_endpoint(self, async_client: AsyncClient, test_request_with_artifacts):
        """Test getting a specific artifact by ID via API."""
        request = test_request_with_artifacts["request"]
        artifact = test_request_with_artifacts["artifact"]
        
        # Get artifact by ID via API
        response = await async_client.get(
            f"/api/v1/requests/{request.id}/artifacts/{artifact.id}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(artifact.id)
        assert data["request_id"] == str(request.id)
        assert data["format"] == "csv"

    @pytest_asyncio.fixture
    async def test_get_artifacts_for_nonexistent_request(self, async_client: AsyncClient):
        """Test getting artifacts for a non-existent request."""
        fake_request_id = "550e8400-e29b-41d4-a716-446655440000"
        
        response = await async_client.get(f"/api/v1/requests/{fake_request_id}/artifacts")
        
        assert response.status_code == 404
        assert "request not found" in response.json()["detail"].lower()