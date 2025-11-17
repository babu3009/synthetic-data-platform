"""
Debug script to test the estimate endpoint locally
"""
import asyncio
import sys
sys.path.insert(0, "apps/backend")

from app.services.estimator import estimate_relational

# Test schema that might be causing issues
test_schema = {
    "tables": [
        {
            "name": "students",
            "columns": [
                {"name": "id", "dtype": "int"},
                {"name": "name", "dtype": "text"}
            ]
        }
    ]
}

test_rows_per_table = {}

try:
    result = estimate_relational(test_schema, test_rows_per_table)
    print("SUCCESS!")
    print(f"Result: {result}")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
