"""
Setup script to create initial migration and run database setup.
Run this script from the backend directory after ensuring dependencies are installed.
"""
import os
import sys
import subprocess
from pathlib import Path


def run_command(command: str, description: str) -> bool:
    """Run a command and return success status."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(f"Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        print(f"Error: {e.stderr}")
        return False


def main():
    """Main setup function."""
    print("🚀 Setting up Synthetic Data Platform Backend Database")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not Path("alembic.ini").exists():
        print("❌ Please run this script from the apps/backend directory")
        sys.exit(1)
    
    # Check if virtual environment is activated or poetry is available
    commands_to_try = [
        ("poetry --version", "poetry"),
        ("python -c \"import alembic\"", "python with alembic"),
    ]
    
    command_prefix = None
    for cmd, name in commands_to_try:
        if run_command(cmd, f"Checking {name}"):
            if "poetry" in cmd:
                command_prefix = "poetry run "
            else:
                command_prefix = ""
            break
    
    if command_prefix is None:
        print("❌ Neither Poetry nor Python with Alembic found")
        print("Please install dependencies first:")
        print("  - If using Poetry: poetry install")
        print("  - If using pip: pip install -r requirements.txt")
        sys.exit(1)
    
    # Generate initial migration
    migration_cmd = f"{command_prefix}alembic revision --autogenerate -m \"Initial migration with core models\""
    if not run_command(migration_cmd, "Creating initial Alembic migration"):
        print("❌ Failed to create migration")
        sys.exit(1)
    
    print("\n📋 Database setup completed!")
    print("\nNext steps:")
    print("1. Start the infrastructure: make infra-up")
    print("2. Run the migration: make migrate")
    print("3. Seed the database: make seed")
    print("4. Start the backend: make backend-dev")


if __name__ == "__main__":
    main()