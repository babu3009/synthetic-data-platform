"""Test script to run the relational job directly"""
import sys
from pathlib import Path

# Add the backend directory to the path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.jobs.relational_job import run_relational_job

# Run the job for the test request
request_id = "f65c30af-0b2b-492c-8565-9959185398a3"

print(f"Starting relational job for request {request_id}...")
try:
    run_relational_job(request_id)
    print("Job completed successfully!")
except Exception as e:
    print(f"Job failed with error: {e}")
    import traceback
    traceback.print_exc()
