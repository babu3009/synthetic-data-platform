"""
Windows-compatible startup script for FastAPI backend.
Handles multiprocessing issues that occur with uvicorn --reload on Windows.
"""
import sys
import multiprocessing

if __name__ == "__main__":
    # Required for Windows multiprocessing support
    multiprocessing.freeze_support()
    
    # Import after freeze_support
    import uvicorn
    
    # Start uvicorn with reload enabled
    # Use watchfiles instead of default reloader for better Windows compatibility
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=["app"],
        log_level="info",
    )
