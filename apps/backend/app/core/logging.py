import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler


def configure_logging(level: int | str = "INFO", log_dir: str = "logs") -> None:
    """Configure application logging with file and console handlers.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory to store log files (relative to app root)
    """
    # Normalize level if it's a string
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    # Create logs directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Define log format with detailed information
    detailed_format = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler (INFO and above)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(detailed_format)
    
    # File handler for all logs (rotating, 10MB per file, keep 10 files)
    all_logs_file = log_path / "app.log"
    all_handler = RotatingFileHandler(
        all_logs_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,
        encoding="utf-8"
    )
    all_handler.setLevel(logging.DEBUG)
    all_handler.setFormatter(detailed_format)
    
    # File handler for errors only (rotating, 10MB per file, keep 20 files)
    error_logs_file = log_path / "errors.log"
    error_handler = RotatingFileHandler(
        error_logs_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=20,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_format)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Add handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(all_handler)
    root_logger.addHandler(error_handler)
    
    # Log initial message
    logging.info(
        f"Logging configured: level={level}, log_dir={log_path.absolute()}"
    )
