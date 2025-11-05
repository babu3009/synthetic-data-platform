"""
Integration tests for DDL ingestion API endpoints (async client).
"""
import json
from io import BytesIO
from uuid import uuid4

import pytest
import pytest_asyncio


# Sample DDL for testing
SAMPLE_DDL = """
CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    first_name VARCHAR(100),
    last_name VARCHAR(100)
);

CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total DECIMAL(10, 2) CHECK (total >= 0),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);
"""

# Use anyio to run async tests
pytestmark = pytest.mark.anyio


@pytest_asyncio.fixture
async def test_project(async_client):
    """Create a test project using the async client."""
    import uuid
    unique_name = f"Test Project {uuid.uuid4().hex[:8]}"
    response = await async_client.post(
        "/api/v1/projects/",
        json={
            "name": unique_name,
            "owner": "test@example.com",
            "tags": ["test"],
        },
    )
    if response.status_code != 200:
        print(f"Project creation failed: {response.status_code}, {response.text}")
    assert response.status_code == 200, f"Failed to create project: {response.text}"
    return response.json()


async def test_upload_ddl_file(async_client, test_project):
    """Test uploading a DDL file."""
    project_id = test_project["id"]

    # Create DDL file
    ddl_file = BytesIO(SAMPLE_DDL.encode("utf-8"))

    response = await async_client.post(
        f"/api/v1/projects/{project_id}/sources/",
        files={"file": ("test.sql", ddl_file, "text/plain")},
        data={"project_id": project_id, "dialect": "postgres"},
    )

    assert response.status_code == 200
    data = response.json()

    # Check response structure
    assert "source_id" in data
    assert "schema_id" in data
    assert data["kind"] == "ddl"
    assert data["tables_count"] == 2
    assert isinstance(data["warnings"], list)


async def test_upload_json_schema(async_client, test_project):
    """Test uploading a JSON schema file."""
    project_id = test_project["id"]

    # Create schema JSON
    schema = {
        "tables": [
            {
                "name": "users",
                "columns": [
                    {"name": "id", "dtype": "INTEGER", "nullable": False},
                    {"name": "name", "dtype": "VARCHAR(100)", "nullable": True},
                ],
                "pk": ["id"],
                "uniques": [],
                "checks": [],
                "fks": [],
            }
        ],
        "dag": {"nodes": ["users"], "edges": []},
        "warnings": [],
    }

    schema_file = BytesIO(json.dumps(schema).encode("utf-8"))

    response = await async_client.post(
        f"/api/v1/projects/{project_id}/sources/",
        files={"file": ("schema.json", schema_file, "application/json")},
        data={"project_id": project_id},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["kind"] == "json"
    assert data["tables_count"] == 1


async def test_get_source_schema(async_client, test_project):
    """Test retrieving parsed schema."""
    project_id = test_project["id"]

    # First upload a DDL file
    ddl_file = BytesIO(SAMPLE_DDL.encode("utf-8"))
    upload_response = await async_client.post(
        f"/api/v1/projects/{project_id}/sources/",
        files={"file": ("test.sql", ddl_file, "text/plain")},
        data={"project_id": project_id, "dialect": "postgres"},
    )
    source_id = upload_response.json()["source_id"]

    # Retrieve schema
    response = await async_client.get(
        f"/api/v1/projects/{project_id}/sources/{source_id}"
    )

    assert response.status_code == 200
    data = response.json()

    # Check schema structure
    assert "id" in data
    assert "source_id" in data
    assert "schema" in data
    assert "dag" in data
    assert "warnings" in data
    assert "created_at" in data

    # Check schema content
    schema = data["schema"]
    assert len(schema["tables"]) == 2
    assert "customers" in [t["name"] for t in schema["tables"]]
    assert "orders" in [t["name"] for t in schema["tables"]]


async def test_get_source_dag(async_client, test_project):
    """Test retrieving DAG."""
    project_id = test_project["id"]

    # Upload DDL
    ddl_file = BytesIO(SAMPLE_DDL.encode("utf-8"))
    upload_response = await async_client.post(
        f"/api/v1/projects/{project_id}/sources/",
        files={"file": ("test.sql", ddl_file, "text/plain")},
        data={"project_id": project_id, "dialect": "postgres"},
    )
    source_id = upload_response.json()["source_id"]

    # Get DAG
    response = await async_client.get(
        f"/api/v1/projects/{project_id}/sources/{source_id}/dag"
    )

    assert response.status_code == 200
    dag = response.json()

    assert "nodes" in dag
    assert "edges" in dag
    assert len(dag["nodes"]) == 2
    # Should have edge from orders to customers
    assert ["orders", "customers"] in dag["edges"]


async def test_get_source_tables(async_client, test_project):
    """Test retrieving table list."""
    project_id = test_project["id"]

    # Upload DDL
    ddl_file = BytesIO(SAMPLE_DDL.encode("utf-8"))
    upload_response = await async_client.post(
        f"/api/v1/projects/{project_id}/sources/",
        files={"file": ("test.sql", ddl_file, "text/plain")},
        data={"project_id": project_id, "dialect": "postgres"},
    )
    source_id = upload_response.json()["source_id"]

    # Get tables
    response = await async_client.get(
        f"/api/v1/projects/{project_id}/sources/{source_id}/tables"
    )

    assert response.status_code == 200
    tables = response.json()

    assert len(tables) == 2
    table_names = {t["name"] for t in tables}
    assert "customers" in table_names
    assert "orders" in table_names

    # Check table structure
    customers = next(t for t in tables if t["name"] == "customers")
    assert len(customers["columns"]) == 4
    assert customers["pk"] == ["customer_id"]


async def test_upload_invalid_ddl(async_client, test_project):
    """Test uploading invalid DDL."""
    project_id = test_project["id"]

    invalid_ddl = "THIS IS NOT VALID SQL;"
    ddl_file = BytesIO(invalid_ddl.encode("utf-8"))

    response = await async_client.post(
        f"/api/v1/projects/{project_id}/sources/",
        files={"file": ("invalid.sql", ddl_file, "text/plain")},
        data={"project_id": project_id, "dialect": "postgres"},
    )

    # Should return error or schema with warnings
    assert response.status_code in [200, 400]
    if response.status_code == 200:
        data = response.json()
        assert len(data["warnings"]) > 0


async def test_upload_unsupported_file_type(async_client, test_project):
    """Test uploading unsupported file type."""
    project_id = test_project["id"]

    file_content = BytesIO(b"some content")

    response = await async_client.post(
        f"/api/v1/projects/{project_id}/sources/",
        files={"file": ("test.txt", file_content, "text/plain")},
        data={"project_id": project_id},
    )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


async def test_get_nonexistent_source(async_client, test_project):
    """Test retrieving non-existent source."""
    project_id = test_project["id"]
    fake_source_id = str(uuid4())

    response = await async_client.get(
        f"/api/v1/projects/{project_id}/sources/{fake_source_id}"
    )

    assert response.status_code == 404


async def test_upload_to_nonexistent_project(async_client):
    """Test uploading to non-existent project."""
    fake_project_id = str(uuid4())
    ddl_file = BytesIO(SAMPLE_DDL.encode("utf-8"))

    response = await async_client.post(
        f"/api/v1/projects/{fake_project_id}/sources/",
        files={"file": ("test.sql", ddl_file, "text/plain")},
        data={"project_id": fake_project_id, "dialect": "postgres"},
    )

    assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
