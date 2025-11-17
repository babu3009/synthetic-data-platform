# Backend Startup Guide

## Error Logging

The backend now includes comprehensive error logging with full tracebacks.

### Log Files

All logs are written to `apps/backend/logs/`:
- **`app.log`** - All logs (INFO, WARNING, ERROR) with rotation
- **`errors.log`** - Only errors with full Python tracebacks (ERROR and CRITICAL)

## Starting the Backend

### Option 1: Using VS Code Debug (Recommended for Development)

1. Open VS Code
2. Go to Run and Debug (Ctrl+Shift+D)
3. Select "Python: FastAPI" configuration
4. Press F5 to start debugging

### Option 2: Using PowerShell Script (Windows)

```powershell
cd apps\backend
.\start_backend.ps1
```

### Option 3: Direct uvicorn command

```powershell
cd apps\backend
conda activate conda-synthetic-data
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir app
```

### Option 4: Using Python script

```powershell
cd apps\backend
conda activate conda-synthetic-data
python run_dev.py
```

## Viewing Logs

### Real-time log monitoring

```powershell
# Watch error log in real-time
Get-Content apps\backend\logs\errors.log -Wait -Tail 20

# Watch all logs in real-time
Get-Content apps\backend\logs\app.log -Wait -Tail 20
```

### View recent errors

```powershell
# Last 50 lines of error log
Get-Content apps\backend\logs\errors.log -Tail 50

# Search for specific error
Select-String -Path apps\backend\logs\errors.log -Pattern "UNHANDLED EXCEPTION" -Context 5,10
```

## Troubleshooting

### Multiprocessing Errors on Windows

If you see `BrokenPipeError` or `EOFError` related to multiprocessing:
- Use the PowerShell script or Python startup script instead of direct uvicorn
- These scripts include `multiprocessing.freeze_support()` which fixes Windows issues

### Port Already in Use

```powershell
# Find process using port 8000
Get-NetTCPConnection -LocalPort 8000 | Select-Object -ExpandProperty OwningProcess

# Stop the process (replace PID with actual process ID)
Stop-Process -Id <PID> -Force
```

## Debugging API Errors

When you encounter a 500 Internal Server Error:

1. **Reproduce the error** by making the API call
2. **Check the error log**:
   ```powershell
   code apps\backend\logs\errors.log
   ```
3. Look for entries with `UNHANDLED EXCEPTION`
4. The full Python traceback will show:
   - The exact file and line number
   - The complete call stack
   - The exception type and message

## Log Format

Each log entry includes:
```
YYYY-MM-DD HH:MM:SS | LEVEL    | module_name | function_name:line | message
```

For errors, additional context is logged:
- Request method and URL
- Client IP address
- Full Python traceback
- Exception type and message
