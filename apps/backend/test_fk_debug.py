"""Debug FK generation"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.db.session import SessionLocal
from app.db import models
from sqlalchemy import select
import json

# Monkey-patch to add logging
original_sample = None

def logged_sample(parent_pool, degrees, mode):
    result = original_sample(parent_pool, degrees, mode)
    if len(parent_pool) > 0:
        print(f"Sampled FK: {result} from pool of {len(parent_pool)} keys (mode={mode})")
    else:
        print(f"WARNING: Empty parent pool! mode={mode}")
    return result

# Get request and run with logging
db = SessionLocal()
try:
    req = db.execute(select(models.Request).where(models.Request.id == 'f65c30af-0b2b-492c-8565-9959185398a3')).scalar_one_or_none()
    if not req:
        print("Request not found")
        sys.exit(1)
    
    schema = req.params_json.get('schema', {})
    print(f"Schema tables: {[t['name'] for t in schema['tables']]}")
    print(f"Relationships: {len(schema.get('relationships', []))}")
    
    from app.services import relational
    
    # Patch the sampling function
    original_sample = relational._sample_parent_key
    relational._sample_parent_key = logged_sample
    
    # Run generation
    from app.jobs.relational_job import run_relational_job
    run_relational_job('f65c30af-0b2b-492c-8565-9959185398a3')
    
finally:
    db.close()
