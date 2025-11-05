# 🚀 Quick Reference - Conda Environment

## Environment: `conda-synthetic-data`

### Activation
```powershell
conda activate conda-synthetic-data
```

### Deactivation
```powershell
conda deactivate
```

### Check Status
```powershell
# List all environments (active has *)
conda info --envs

# Check active environment
echo $env:CONDA_DEFAULT_ENV
```

### Package Management
```powershell
# List installed packages
conda list
pip list

# Install new package
pip install <package-name>

# Update package
pip install --upgrade <package-name>

# Export environment
conda env export > environment.yml
pip freeze > requirements.txt
```

### VS Code
- **Reload Window**: `Ctrl+Shift+P` → "Developer: Reload Window"
- **Select Interpreter**: `Ctrl+Shift+P` → "Python: Select Interpreter"
- Current: `Python 3.11.14 ('conda-synthetic-data')`

### Development Commands
```powershell
# Activate first!
conda activate conda-synthetic-data

# Navigate to backend
cd C:\Code\python\synthetic-data-platform\apps\backend

# Run validation
python validate_implementation.py

# Run tests
pytest

# Start server
uvicorn app.main:app --reload

# Database migrations
alembic upgrade head
alembic revision --autogenerate -m "message"

# Seed database
python -m app.scripts.seed_db
```

### Helper Scripts
```powershell
# From apps/backend directory
.\activate-conda.ps1
```

### Troubleshooting
```powershell
# If imports fail
conda activate conda-synthetic-data
pip install --force-reinstall <package-name>

# If VS Code doesn't detect
# 1. Reload window: Ctrl+Shift+P → Reload
# 2. Select interpreter: Ctrl+Shift+P → Select Interpreter

# Check Python path
python -c "import sys; print(sys.executable)"
# Should show: C:\Users\Isaiyavan Karan\.conda\envs\conda-synthetic-data\python.exe
```

### Environment Details
- **Python**: 3.11.14
- **Location**: `C:\Users\Isaiyavan Karan\.conda\envs\conda-synthetic-data\`
- **Conda**: `C:\ProgramData\miniforge3\`
- **Packages**: 34 installed

### Key Packages
| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | 0.121.0 | Web framework |
| uvicorn | 0.38.0 | ASGI server |
| sqlalchemy | 2.0.44 | Database ORM |
| alembic | 1.17.1 | Migrations |
| pydantic | 2.12.4 | Validation |
| pytest | 8.4.2 | Testing |

### Documentation
- `ENVIRONMENT.md` - Complete environment guide
- `CONDA_MIGRATION_COMPLETE.md` - Setup summary
- `ENVIRONMENT_SETUP_COMPLETE.md` - Detailed docs

---
**Status**: ✅ Ready for Development
