"""Test script to verify logging setup and start backend."""
import sys
import subprocess
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "apps" / "backend"
sys.path.insert(0, str(backend_path))

try:
    print("Testing imports...")
    from app.core.logging import configure_logging
    print("✓ Logging module imported")
    
    from app.main import app
    print("✓ FastAPI app imported")
    
    print("\n✓ All imports successful!")
    print("\nYou can now start the backend with:")
    print("  cd apps/backend")
    print("  uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload")
    print("\nLogs will be written to:")
    print("  apps/backend/logs/app.log")
    print("  apps/backend/logs/errors.log")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
