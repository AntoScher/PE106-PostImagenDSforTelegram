import logging
import logging.config
import json
import sys
from datetime import datetime
from typing import Any, Dict
from pathlib import Path
import os

# Создаем директорию для логов
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)


class JSONFormatter(logging.Formatter):
    """JSON форматтер для структурированного логирования"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Добавляем дополнительные поля если есть
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'endpoint'):
            log_entry['endpoint'] = record.endpoint
        if hasattr(record, 'method'):
            log_entry['method'] = record.method
        if hasattr(record, 'status_code'):
            log_entry['status_code'] = record.status_code
        if hasattr(record, 'response_time'):
            log_entry['response_time'] = record.response_time
        
        # Добавляем exception info если есть
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False)


class RequestIdFilter(logging.Filter):
    """Фильтр для добавления request_id к логам"""
    
    def __init__(self, name: str = ""):
        super().__init__(name)
        self.request_id = None
    
    def filter(self, record: logging.LogRecord) -> bool:
        if hasattr(record, 'request_id'):
            record.request_id = self.request_id
        return True


def setup_logging(log_level: str = "INFO") -> None:
    """Настройка логирования"""
    
    # Конфигурация логирования
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": JSONFormatter,
            },
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            },
            "detailed": {
                "format": "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s"
            }
        },
        "filters": {
            "request_id": {
                "()": RequestIdFilter,
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "standard",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": log_level,
                "formatter": "json",
                "filename": "logs/app.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf8",
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "json",
                "filename": "logs/error.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf8",
            },
            "access_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "json",
                "filename": "logs/access.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf8",
                "filters": ["request_id"],
            }
        },
        "loggers": {
            "": {
                "handlers": ["console", "file"],
                "level": log_level,
                "propagate": True,
            },
            "app": {
                "handlers": ["console", "file"],
                "level": log_level,
                "propagate": False,
            },
            "app.access": {
                "handlers": ["access_file"],
                "level": "INFO",
                "propagate": False,
            },
            "app.error": {
                "handlers": ["error_file"],
                "level": "ERROR",
                "propagate": False,
            },
            "uvicorn": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["access_file"],
                "level": "INFO",
                "propagate": False,
            },
        },
    }
    
    logging.config.dictConfig(logging_config)


class LoggerMixin:
    """Миксин для добавления логирования к классам"""
    
    @property
    def logger(self) -> logging.Logger:
        return logging.getLogger(self.__class__.__name__)


def log_request(request_id: str, method: str, path: str, status_code: int, 
                response_time: float, user_id: str = None) -> None:
    """Логирование HTTP запросов"""
    logger = logging.getLogger("app.access")
    extra = {
        "request_id": request_id,
        "method": method,
        "endpoint": path,
        "status_code": status_code,
        "response_time": response_time,
    }
    if user_id:
        extra["user_id"] = user_id
    
    logger.info(f"Request processed", extra=extra)


def log_error(error: Exception, context: Dict[str, Any] = None) -> None:
    """Логирование ошибок"""
    logger = logging.getLogger("app.error")
    extra = context or {}
    logger.error(f"Error occurred: {str(error)}", extra=extra, exc_info=True)


def log_security_event(event_type: str, user_id: str = None, 
                      details: Dict[str, Any] = None) -> None:
    """Логирование событий безопасности"""
    logger = logging.getLogger("app.security")
    extra = {
        "event_type": event_type,
        "user_id": user_id,
    }
    if details:
        extra.update(details)
    logger.warning(f"Security event: {event_type}", extra=extra)


def log_performance(operation: str, duration: float, 
                   details: Dict[str, Any] = None) -> None:
    """Логирование производительности"""
    logger = logging.getLogger("app.performance")
    extra = {
        "operation": operation,
        "duration": duration,
    }
    if details:
        extra.update(details)
    logger.info(f"Performance: {operation} took {duration:.3f}s", extra=extra)


# Инициализация логирования при импорте модуля
setup_logging(os.getenv("LOG_LEVEL", "INFO"))
