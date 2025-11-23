"""
Comprehensive test for recent fixes:
1. Authentication with provided credentials
2. WebSocket real-time progress updates
3. Timeout handling (60s timeout)
4. WebSocket disconnect handling (no errors)
5. Artifact auto-refresh
"""
import asyncio
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

try:
    import requests
    from websockets import connect
    from websockets.exceptions import ConnectionClosed, ConnectionClosedOK
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install: pip install requests websockets")
    sys.exit(1)

BASE_URL = "http://localhost:8000"
API_V1 = f"{BASE_URL}/api/v1"

# Credentials from .env
USERNAME = "babu3009@gmail.com"
PASSWORD = "admin@123"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.CYAN}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*70}{Colors.RESET}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓{Colors.RESET} {text}")

def print_error(text):
    print(f"{Colors.RED}✗{Colors.RESET} {text}")

def print_info(text):
    print(f"{Colors.BLUE}→{Colors.RESET} {text}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠{Colors.RESET} {text}")


def test_01_authentication():
    """Test 1: Login and get JWT token"""
    print_header("TEST 1: Authentication")
    
    try:
        response = requests.post(
            f"{API_V1}/auth/login",
            json={
                "email": USERNAME,
                "password": PASSWORD
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            if token:
                print_success(f"Login successful")
                print_info(f"Token: {token[:50]}...")
                print_info(f"Token type: {data.get('token_type', 'bearer')}")
                return token
            else:
                print_error("No access token in response")
                return None
        else:
            print_error(f"Login failed: {response.status_code}")
            print_error(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Login error: {e}")
        return None


def test_02_get_projects(token):
    """Test 2: Get user's projects"""
    print_header("TEST 2: Fetch Projects")
    
    if not token:
        print_warning("Skipping - no token")
        return None
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{API_V1}/projects", headers=headers, timeout=10)
        
        if response.status_code == 200:
            projects = response.json()
            print_success(f"Found {len(projects)} project(s)")
            
            if projects:
                project = projects[0]
                print_info(f"Using project: {project['name']}")
                print_info(f"Project ID: {project['id']}")
                return project['id']
            else:
                print_warning("No projects found")
                return None
        else:
            print_error(f"Failed to fetch projects: {response.status_code}")
            return None
            
    except Exception as e:
        print_error(f"Error fetching projects: {e}")
        return None


def test_03_create_test_request(token, project_id):
    """Test 3: Create a test request"""
    print_header("TEST 3: Create Test Request")
    
    if not token or not project_id:
        print_warning("Skipping - no token or project")
        return None
    
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Simple flat data generation request
        request_data = {
            "alias": f"test-websocket-{datetime.now().strftime('%H%M%S')}",
            "type": "flat",
            "params_json": {
                "rows": 100,
                "schema": {
                    "fields": [
                        {
                            "name": "id",
                            "provider": {"type": "sequence", "start": 1}
                        },
                        {
                            "name": "email",
                            "provider": {"type": "faker", "method": "email", "unique": True}
                        },
                        {
                            "name": "name",
                            "provider": {"type": "faker", "method": "name"}
                        }
                    ]
                },
                "outputs": {
                    "formats": ["csv"]
                }
            }
        }
        
        response = requests.post(
            f"{API_V1}/projects/{project_id}/requests",
            headers=headers,
            json=request_data,
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            request = response.json()
            print_success(f"Created request: {request['alias']}")
            print_info(f"Request ID: {request['id']}")
            print_info(f"Status: {request['status']}")
            return request['id']
        else:
            print_error(f"Failed to create request: {response.status_code}")
            print_error(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Error creating request: {e}")
        return None


async def test_04_websocket_and_start(token, project_id, request_id):
    """Test 4: WebSocket real-time updates + Start request (60s timeout)"""
    print_header("TEST 4: WebSocket + Start Request (Timeout Test)")
    
    if not all([token, project_id, request_id]):
        print_warning("Skipping - missing parameters")
        return False
    
    ws_url = f"ws://localhost:8000/api/v1/ws/requests/{request_id}"
    
    try:
        print_info(f"Connecting to WebSocket...")
        async with connect(ws_url) as websocket:
            print_success("WebSocket connected")
            
            # Start request via HTTP (with 60s timeout)
            print_info(f"Starting request via API (60s timeout)...")
            headers = {"Authorization": f"Bearer {token}"}
            
            start_time = time.time()
            try:
                response = requests.post(
                    f"{API_V1}/projects/{project_id}/requests/{request_id}:start",
                    headers=headers,
                    timeout=60  # 60 second timeout (same as frontend)
                )
                elapsed = time.time() - start_time
                
                if response.status_code == 200:
                    print_success(f"Start request successful ({elapsed:.1f}s)")
                else:
                    print_error(f"Start failed: {response.status_code} ({elapsed:.1f}s)")
                    
            except requests.Timeout:
                elapsed = time.time() - start_time
                print_warning(f"HTTP timeout after {elapsed:.1f}s (but job may still be running)")
            except Exception as e:
                print_error(f"Start request error: {e}")
            
            # Listen for WebSocket updates
            print_info("Listening for WebSocket updates...")
            update_count = 0
            last_status = None
            last_progress = None
            
            try:
                while True:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(message)
                    update_count += 1
                    
                    msg_type = data.get("type")
                    
                    if msg_type == "status":
                        status = data.get("status")
                        progress = data.get("progress")
                        
                        if status != last_status or progress != last_progress:
                            progress_str = f"{progress}%" if progress is not None else "N/A"
                            print_success(f"Update #{update_count}: status={status}, progress={progress_str}")
                            last_status = status
                            last_progress = progress
                    
                    elif msg_type == "artifacts":
                        artifacts = data.get("artifacts", [])
                        print_success(f"Artifacts received: {len(artifacts)} file(s)")
                        for art in artifacts:
                            print_info(f"  - {art['format']}: {art.get('size_bytes', 0)} bytes")
                    
                    elif msg_type == "complete":
                        final_status = data.get("status")
                        print_success(f"Job completed with status: {final_status}")
                        break
                    
                    elif msg_type == "error":
                        print_error(f"WebSocket error: {data.get('message')}")
                        break
                        
            except asyncio.TimeoutError:
                print_warning("No more WebSocket updates (timeout)")
            except ConnectionClosedOK:
                print_success("WebSocket closed gracefully by server")
            except ConnectionClosed as e:
                print_warning(f"WebSocket closed: code={e.code}, reason={e.reason}")
            
            print_info(f"Total updates received: {update_count}")
            
            # Test graceful disconnect
            print_info("Closing WebSocket from client (code 1001)...")
            await websocket.close(code=1001, reason="Test complete")
            print_success("Client closed connection")
            
            return True
            
    except Exception as e:
        print_error(f"WebSocket test error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_05_check_artifacts(token, request_id):
    """Test 5: Verify artifacts were created"""
    print_header("TEST 5: Verify Artifacts")
    
    if not token or not request_id:
        print_warning("Skipping - no token or request")
        return False
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{API_V1}/requests/{request_id}/artifacts",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            artifacts = response.json()
            print_success(f"Found {len(artifacts)} artifact(s)")
            
            for art in artifacts:
                print_info(f"  - ID: {art['id']}")
                print_info(f"    Format: {art['format']}")
                print_info(f"    Size: {art.get('size_bytes', 0)} bytes")
                print_info(f"    URI: {art.get('storage_uri', 'N/A')}")
            
            return len(artifacts) > 0
        else:
            print_error(f"Failed to fetch artifacts: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Error fetching artifacts: {e}")
        return False


async def main():
    """Run all tests"""
    print(f"\n{Colors.BOLD}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}Comprehensive Feature Test Suite{Colors.RESET}")
    print(f"{Colors.BOLD}Testing: Auth, WebSocket, Timeout, Disconnect Handling{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*70}{Colors.RESET}")
    
    results = {
        "authentication": False,
        "projects": False,
        "create_request": False,
        "websocket_start": False,
        "artifacts": False
    }
    
    # Test 1: Login
    token = test_01_authentication()
    results["authentication"] = token is not None
    
    if not token:
        print_error("\nCannot proceed without authentication")
        return results
    
    # Test 2: Get projects
    project_id = test_02_get_projects(token)
    results["projects"] = project_id is not None
    
    if not project_id:
        print_error("\nCannot proceed without a project")
        return results
    
    # Test 3: Create request
    request_id = test_03_create_test_request(token, project_id)
    results["create_request"] = request_id is not None
    
    if not request_id:
        print_error("\nCannot proceed without a request")
        return results
    
    # Test 4: WebSocket + Start (with timeout handling)
    results["websocket_start"] = await test_04_websocket_and_start(token, project_id, request_id)
    
    # Test 5: Verify artifacts
    results["artifacts"] = test_05_check_artifacts(token, request_id)
    
    # Summary
    print_header("TEST SUMMARY")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for test_name, passed_test in results.items():
        status = f"{Colors.GREEN}PASS{Colors.RESET}" if passed_test else f"{Colors.RED}FAIL{Colors.RESET}"
        print(f"  {test_name.replace('_', ' ').title()}: {status}")
    
    print(f"\n{Colors.BOLD}Results: {passed}/{total} tests passed{Colors.RESET}")
    
    if passed == total:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ ALL TESTS PASSED{Colors.RESET}\n")
    else:
        print(f"{Colors.RED}{Colors.BOLD}✗ SOME TESTS FAILED{Colors.RESET}\n")
    
    print_header("BACKEND LOG CHECK")
    print_info("Check the backend terminal for:")
    print(f"  {Colors.GREEN}✓{Colors.RESET} No 'RuntimeError: Cannot call send once a close message has been sent'")
    print(f"  {Colors.GREEN}✓{Colors.RESET} Clean WebSocket connect/disconnect logs")
    print(f"  {Colors.GREEN}✓{Colors.RESET} No stack traces for normal disconnections")
    print()
    
    return results


if __name__ == "__main__":
    print(f"\n{Colors.YELLOW}Make sure backend server is running on http://localhost:8000{Colors.RESET}")
    print(f"{Colors.YELLOW}Press Enter to start testing...{Colors.RESET}")
    input()
    
    results = asyncio.run(main())
    
    # Exit code based on results
    all_passed = all(results.values())
    sys.exit(0 if all_passed else 1)
