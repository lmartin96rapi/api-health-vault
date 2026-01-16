import logging
import sys
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime, timedelta
from app.config import settings


class RequestIDFormatter(logging.Formatter):
    """Custom formatter that includes RequestID in log format."""
    
    def format(self, record: logging.LogRecord) -> str:
        # Extract RequestID from extra data
        request_id = getattr(record, 'RequestID', None)
        if not request_id:
            request_id = getattr(record, 'request_id', None)
        
        # If not in extra, try to extract from message string
        if not request_id and record.getMessage():
            import re
            # Look for "RequestID: <uuid>" pattern in message
            match = re.search(r'RequestID:\s*([a-f0-9-]{36})', record.getMessage(), re.IGNORECASE)
            if match:
                request_id = match.group(1)
                # Remove RequestID from message to avoid duplication
                record.msg = re.sub(r'\s*\|\s*RequestID:\s*[a-f0-9-]{36}', '', record.msg, flags=re.IGNORECASE)
                record.args = ()  # Clear args since we modified msg
        
        # Format: YYYY-MM-DD HH:MM:SS - LEVEL - [REQUEST_ID] - [file:line] - function - message
        # If no Request ID, use [SYSTEM]
        # Always set request_id fresh to avoid double brackets
        if request_id:
            # Remove brackets if already present (in case of double formatting)
            clean_request_id = request_id.strip('[]')
            record.request_id = f'[{clean_request_id}]'
        else:
            record.request_id = '[SYSTEM]'
        
        base_format = '%(asctime)s - %(levelname)s - %(request_id)s - [%(filename)s:%(lineno)d] - %(funcName)s - %(message)s'
        
        # Create temporary formatter with the format
        temp_formatter = logging.Formatter(base_format, datefmt='%Y-%m-%d %H:%M:%S')
        return temp_formatter.format(record)


def setup_logging() -> None:
    """
    Configure application-wide logging with daily file rotation.
    Creates log directory if it doesn't exist and sets up handlers.
    """
    # Create log directory if it doesn't exist
    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Get log level from environment or config
    log_level = settings.get_log_level()
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Human-readable format: YYYY-MM-DD HH:MM:SS - LEVEL - REQUEST_ID - [file:line] - function - message | context
    log_format = RequestIDFormatter(datefmt='%Y-%m-%d %H:%M:%S')
    
    # Console handler (stdout) - for development
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)
    
    # File handler with daily rotation
    # File naming: app-YYYY-MM-DD.log
    # Rotates at midnight each day
    log_file = log_dir / "app.log"
    file_handler = TimedRotatingFileHandler(
        filename=str(log_file),
        when='midnight',
        interval=1,
        backupCount=settings.LOG_RETENTION_DAYS,
        encoding='utf-8'
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(log_format)
    file_handler.suffix = "%Y-%m-%d"  # Format: app.log.2025-01-15
    root_logger.addHandler(file_handler)
    
    # Suppress noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    # Get logger for this module
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured - Level: {log_level}, Directory: {log_dir.absolute()}")


def cleanup_old_logs() -> None:
    """
    Delete log files older than the retention period.
    Runs on application startup and should be scheduled for daily execution.
    """
    log_dir = Path(settings.LOG_DIR)
    
    if not log_dir.exists():
        return
    
    retention_days = settings.LOG_RETENTION_DAYS
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    
    logger = logging.getLogger(__name__)
    deleted_count = 0
    
    try:
        # Find all log files
        for log_file in log_dir.glob("app.log.*"):
            try:
                # Extract date from filename (app.log.YYYY-MM-DD)
                date_str = log_file.suffix.lstrip('.')
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                
                if file_date < cutoff_date:
                    log_file.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted old log file: {log_file.name}")
            except (ValueError, OSError) as e:
                logger.warning(f"Error processing log file {log_file.name}: {str(e)}")
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old log file(s) (older than {retention_days} days)")
    except Exception as e:
        logger.error(f"Error during log cleanup: {str(e)}", exc_info=True)

