"""Test creating and running a request."""
import asyncio
import httpx
import json

API_BASE = "http://localhost:8000/api/v1"

async def main():
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        # Get first project
        resp = await client.get(f"{API_BASE}/projects")
        resp.raise_for_status()
        projects = resp.json()
        if not projects:
            print("No projects found")
            return
        
        project_id = projects[0]["id"]
        print(f"Using project: {project_id}")
        
        # Create a simple relational request
        request_data = {
            "type": "relational",
            "alias": "test-debug",
            "params_json": {
                "entity": {
                    "tables": [
                        {
                            "name": "users",
                            "columns": [
                                {"name": "id", "type": "INTEGER", "primary_key": True},
                                {"name": "name", "type": "VARCHAR(100)"}
                            ]
                        }
                    ]
                },
                "rows": 10,
                "outputs": [
                    {
                        "type": "csv",
                        "path": "test_users.csv"
                    }
                ]
            },
            "seed": 42
        }
        
        resp = await client.post(
            f"{API_BASE}/projects/{project_id}/requests",
            json=request_data
        )
        resp.raise_for_status()
        request = resp.json()
        request_id = request["id"]
        print(f"Created request: {request_id}")
        
        # Start the request
        resp = await client.post(
            f"{API_BASE}/projects/{project_id}/requests/{request_id}:start"
        )
        resp.raise_for_status()
        print(f"Started request: {request_id}")
        print("Check logs for status updates")

if __name__ == "__main__":
    asyncio.run(main())
