import traceback
import sys

try:
    from app.main import app
    print(f"SUCCESS: App loaded - {app.title}")
    sys.exit(0)
except Exception as e:
    print("ERROR during import:")
    traceback.print_exc()
    sys.exit(1)
