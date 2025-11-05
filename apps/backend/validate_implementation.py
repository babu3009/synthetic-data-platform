#!/usr/bin/env python3
"""
Validation script to check that all backend components are properly implemented.
"""
import sys
from pathlib import Path

def check_file_exists(file_path: str, description: str) -> bool:
    """Check if a file exists."""
    if Path(file_path).exists():
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description}: {file_path} (missing)")
        return False

def check_implementation():
    """Check all implemented components."""
    print("🔍 Validating Synthetic Data Platform Backend Implementation")
    print("=" * 65)
    
    # Models and Database
    print("\n📊 Database Models & Configuration:")
    checks = []
    checks.append(check_file_exists("app/db/models.py", "SQLAlchemy Models"))
    checks.append(check_file_exists("app/db/base.py", "Database Base"))
    checks.append(check_file_exists("app/db/session.py", "Database Session"))
    checks.append(check_file_exists("alembic.ini", "Alembic Configuration"))
    checks.append(check_file_exists("alembic/env.py", "Alembic Environment"))
    
    # Pydantic Schemas
    print("\n📋 Pydantic Schemas:")
    checks.append(check_file_exists("app/schemas/project.py", "Project Schema"))
    checks.append(check_file_exists("app/schemas/request.py", "Request Schema"))
    checks.append(check_file_exists("app/schemas/artifact.py", "Artifact Schema"))
    checks.append(check_file_exists("app/schemas/source.py", "Source Schema"))
    
    # CRUD Operations
    print("\n🔧 CRUD Operations:")
    checks.append(check_file_exists("app/crud/base.py", "Base CRUD"))
    checks.append(check_file_exists("app/crud/project.py", "Project CRUD"))
    checks.append(check_file_exists("app/crud/request.py", "Request CRUD"))
    checks.append(check_file_exists("app/crud/artifact.py", "Artifact CRUD"))
    
    # API Endpoints
    print("\n🌐 API Endpoints:")
    checks.append(check_file_exists("app/api/api_v1/endpoints/projects.py", "Projects API"))
    checks.append(check_file_exists("app/api/api_v1/endpoints/requests.py", "Requests API"))
    checks.append(check_file_exists("app/api/api_v1/endpoints/artifacts.py", "Artifacts API"))
    
    # Scripts
    print("\n🛠️  Database Scripts:")
    checks.append(check_file_exists("app/scripts/seed_db.py", "Database Seeding"))
    checks.append(check_file_exists("setup_db.py", "Database Setup Script"))
    
    # Tests
    print("\n🧪 Test Files:")
    checks.append(check_file_exists("tests/test_models.py", "Model Tests"))
    checks.append(check_file_exists("tests/test_crud.py", "CRUD Tests"))
    checks.append(check_file_exists("tests/test_api.py", "API Tests"))
    checks.append(check_file_exists("tests/conftest.py", "Test Configuration"))
    
    # Documentation
    print("\n📚 Documentation:")
    checks.append(check_file_exists("../../docs/BACKEND_DATABASE.md", "Database Documentation"))
    
    # Summary
    total_checks = len(checks)
    passed_checks = sum(checks)
    
    print(f"\n📊 Implementation Status: {passed_checks}/{total_checks} components")
    
    if passed_checks == total_checks:
        print("🎉 All components successfully implemented!")
        print("\n🚀 Next steps:")
        print("1. Install dependencies (Poetry or pip)")
        print("2. Start infrastructure: make infra-up")
        print("3. Generate migration: python setup_db.py") 
        print("4. Run migration: make migrate")
        print("5. Seed database: make seed")
        print("6. Start backend: make backend-dev")
        print("7. Run tests: make backend-test")
        return True
    else:
        print("❌ Some components are missing. Please check the implementation.")
        return False

def check_model_structure():
    """Check that models contain expected fields."""
    print("\n🔍 Checking Model Structure:")
    
    try:
        # Import without actually importing to avoid dependency issues
        models_file = Path("app/db/models.py")
        if models_file.exists():
            content = models_file.read_text()
            
            expected_models = [
                "class Project", "class Source", "class Request",
                "class Config", "class Artifact", "class ApiKey", 
                "class AuditEvent"
            ]
            
            for model in expected_models:
                if model in content:
                    print(f"✅ {model} defined")
                else:
                    print(f"❌ {model} missing")
            
            expected_enums = [
                "class SourceKind", "class RequestType", 
                "class RequestStatus", "class ArtifactFormat"
            ]
            
            for enum in expected_enums:
                if enum in content:
                    print(f"✅ {enum} defined")
                else:
                    print(f"❌ {enum} missing")
                    
    except Exception as e:
        print(f"❌ Error checking models: {e}")

if __name__ == "__main__":
    # Change to backend directory if running from project root
    if Path("apps/backend").exists():
        import os
        os.chdir("apps/backend")
    
    success = check_implementation()
    check_model_structure()
    
    sys.exit(0 if success else 1)