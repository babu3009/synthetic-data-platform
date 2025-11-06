# Python Conda Environment Setup

## Environment Details

- **Environment Name**: `conda-synthetic-data`
- **Python Version**: 3.11.14
- **Location**: `C:\Users\Isaiyavan Karan\.conda\envs\conda-synthetic-data\`
- **Type**: Conda environment (miniforge3)
- **Conda Path**: `C:\ProgramData\miniforge3\`

## Installed Packages

Core dependencies installed:
- **FastAPI** - Modern web framework for building APIs
- **Uvicorn** - ASGI server for FastAPI
- **SQLAlchemy** 2.0.44 - SQL toolkit and ORM
- **Alembic** 1.16.5 - Database migration tool
- **asyncpg** - PostgreSQL async driver
- **psycopg2-binary** - PostgreSQL adapter
- **Pydantic** 2.12.4 - Data validation using Python type hints
- **pydantic-settings** - Settings management
- **python-dotenv** - Environment variable management
- **pytest** - Testing framework
- **pytest-asyncio** - Async support for pytest
- **httpx** - Async HTTP client for testing
- **aiosqlite** - Async SQLite driver for testing

## Activation

### Using Conda (Recommended)
```powershell
# Activate the conda environment
conda activate conda-synthetic-data

# Or using full path
C:\ProgramData\miniforge3\Scripts\activate.bat conda-synthetic-data
```

### PowerShell (Direct)
```powershell
# Use the helper script
.\activate-conda.ps1
```

### Command Prompt (Windows)
```cmd
%windir%\system32\cmd.exe /K C:\ProgramData\miniforge3\Scripts\activate.bat conda-synthetic-data
```

### Deactivation
```powershell
conda deactivate
```

## VS Code Configuration

The workspace is configured to automatically use this environment:

- **Python Interpreter**: `C:\Users\Isaiyavan Karan\.conda\envs\conda-synthetic-data\python.exe`
- **Conda Path**: `C:\ProgramData\miniforge3\Scripts\conda.exe`
- **Environment Manager**: Conda (miniforge3)
- **Auto-activation**: Enabled for new terminals
- **Testing**: pytest enabled for `apps/backend/tests`
- **Formatting**: Configured with Python formatter
- **Import Organization**: Enabled on save

## Verifying Installation

```powershell
# Activate the environment
conda activate conda-synthetic-data

# Check Python version
python --version
# Should show: Python 3.11.14

# List installed packages
pip list

# Or use conda
conda list

# Test imports
python -c "import fastapi, sqlalchemy, pydantic; print('✓ All packages working')"
```

## Adding New Packages

```powershell
# Make sure environment is activated first
conda activate conda-synthetic-data

# Install new package using pip (recommended for Python packages)
pip install <package-name>

# Or using conda
conda install <package-name>

# Install from requirements file
pip install -r requirements.txt

# Save current environment (pip packages)
pip freeze > requirements.txt

# Export conda environment
conda env export > environment.yml
```

## Upgrading Packages

```powershell
# Upgrade a specific package
pip install --upgrade <package-name>

# Upgrade all packages
pip list --outdated
pip install --upgrade <package-name>
```

## Creating requirements.txt / environment.yml

```powershell
# Export current pip packages
pip freeze > requirements.txt

# Export conda environment (complete environment specification)
conda env export > environment.yml

# Install from requirements.txt (fresh environment)
pip install -r requirements.txt

# Create environment from environment.yml
conda env create -f environment.yml
```

## Troubleshooting

### Environment Not Activating

If you see an error about execution policies:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### VS Code Not Using the Environment

1. Open Command Palette (Ctrl+Shift+P)
2. Type "Python: Select Interpreter"
3. Choose `conda-synthetic-data` from the list
4. Or manually select: `C:\Users\Isaiyavan Karan\.conda\envs\conda-synthetic-data\python.exe`
5. Reload VS Code window: Ctrl+Shift+P → "Developer: Reload Window"

### Import Errors

If you see import errors:
```powershell
# Reinstall the package
pip install --force-reinstall <package-name>

# Or reinstall all
pip install --force-reinstall -r requirements.txt
```

### PATH Issues

If `python` command is not found after activation:
```powershell
# Make sure conda is activated
conda activate conda-synthetic-data

# Use full path if needed
& "C:\Users\Isaiyavan Karan\.conda\envs\conda-synthetic-data\python.exe"

# Check if activation worked
Get-Command python

# Verify conda environment
conda info --envs
```

## Conda Environment Management

## LLM Credentials Encryption Environment

For secure storage of LLM provider credentials, configure one of the following options:

1) Local secret key (recommended and simplest)
- Set an application secret used to derive the encryption key:
	- `LLM_SECRET_KEY` = a long, random string (32+ chars). If already a valid Fernet key, it will be used as-is; otherwise a Fernet key is derived from it.
- Ensure the `cryptography` package is installed (it is listed in `requirements.txt`). This enables Fernet encryption.

2) Azure Key Vault (optional)
- Set these environment variables to fetch the key from Key Vault:
	- `KEY_VAULT_URL` = e.g., `https://my-vault.vault.azure.net/`
	- `KEY_VAULT_SECRET_NAME` = the secret name containing your encryption key material
- The app will attempt Key Vault first; if unavailable, it will fall back to `LLM_SECRET_KEY`.

Notes
- Responses never return plaintext credentials; only masked values (e.g., last 4 characters) are shown.
- If `cryptography` is not present, a weak fallback cipher is used for dev/test only. Install `cryptography` for production.

### Listing Environments
```powershell
# List all conda environments
conda env list
# or
conda info --envs
```

### Removing Environment
```powershell
# Remove the conda environment
conda env remove -n conda-synthetic-data
```

### Recreating Environment
```powershell
# Create from scratch
conda create -n conda-synthetic-data python=3.11 -y

# Or create from environment.yml
conda env create -f environment.yml
```

## Next Steps

1. ✅ Environment created and activated
2. ✅ Core dependencies installed
3. ✅ VS Code configured
4. 🔄 Start infrastructure: `cd ../../infra && docker-compose up -d`
5. 🔄 Run database migrations: `alembic upgrade head`
6. 🔄 Seed database: `python -m app.scripts.seed_db`
7. 🔄 Start development server: `uvicorn app.main:app --reload`
8. 🔄 Run tests: `pytest`

## Environment Management

### Recreating the Conda Environment

If you need to start fresh:
```powershell
# Deactivate if active
conda deactivate

# Remove old environment
conda env remove -n conda-synthetic-data

# Create new environment
conda create -n conda-synthetic-data python=3.11 -y

# Activate
conda activate conda-synthetic-data

# Install packages
pip install fastapi uvicorn sqlalchemy alembic asyncpg psycopg2-binary pydantic pydantic-settings python-dotenv pytest pytest-asyncio httpx aiosqlite
```

### Backing Up the Environment

```powershell
# Export requirements
pip freeze > requirements-backup.txt

# To restore
pip install -r requirements-backup.txt
```
