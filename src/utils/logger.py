"""Structured logging setup for DataPilot."""
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs JSON logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "component": getattr(record, "component", "unknown"),
            "user_id": getattr(record, "user_id", None),
            "state": getattr(record, "state", None),
            "message": record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add any extra fields
        for key, value in record.__dict__.items():
            if key not in ["name", "msg", "args", "created", "filename", 
                          "funcName", "levelname", "levelno", "lineno", 
                          "module", "msecs", "message", "pathname", "process",
                          "processName", "relativeCreated", "thread", "threadName",
                          "exc_info", "exc_text", "stack_info", "component",
                          "user_id", "state"]:
                log_data[key] = value
        
        return json.dumps(log_data)


def setup_logger(config: Dict[str, Any]) -> logging.Logger:
    """
    Set up structured logging based on configuration.
    
    Args:
        config: Logging configuration dict with 'level', 'format', 'file' keys
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("datapilot")
    logger.setLevel(getattr(logging, config.get("level", "INFO")))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    if config.get("format") == "json":
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
    logger.addHandler(console_handler)
    
    # File handler if specified
    if config.get("file"):
        log_file = Path(config["file"])
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        if config.get("format") == "json":
            file_handler.setFormatter(JSONFormatter())
        else:
            file_handler.setFormatter(
                logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            )
        logger.addHandler(file_handler)
    
    return logger

