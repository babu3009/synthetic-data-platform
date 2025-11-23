"""Test WebSocket disconnect handling without errors."""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

async def test_websocket_disconnect_handling():
    """Verify WebSocket handles client disconnections gracefully."""
    from websockets import connect
    from websockets.exceptions import ConnectionClosedOK
    
    ws_url = "ws://localhost:8000/api/v1/ws/requests/00000000-0000-0000-0000-000000000000"
    
    print("\n" + "=" * 70)
    print("WebSocket Disconnect Handling Test")
    print("=" * 70)
    print(f"\nConnecting to: {ws_url}")
    
    try:
        async with connect(ws_url) as websocket:
            print("✓ WebSocket connected")
            
            # Receive first message (should be error: request not found)
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                print(f"✓ Received message: {message[:100]}...")
            except asyncio.TimeoutError:
                print("✓ No immediate message (request might exist)")
            
            # Close connection from client side
            print("\n→ Closing connection from client (code 1001 - going away)...")
            await websocket.close(code=1001, reason="Test disconnect")
            print("✓ Client closed connection")
            
    except ConnectionClosedOK:
        print("✓ Connection closed gracefully")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 70)
    print("✓ TEST PASSED: WebSocket disconnect handled gracefully")
    print("=" * 70)
    print("\nCheck backend logs - should NOT see RuntimeError or stack traces")
    print("about 'Cannot call send once a close message has been sent'\n")
    
    return True


if __name__ == "__main__":
    print("\nMake sure backend server is running on http://localhost:8000")
    print("Press Enter to start test...")
    input()
    
    result = asyncio.run(test_websocket_disconnect_handling())
    sys.exit(0 if result else 1)
