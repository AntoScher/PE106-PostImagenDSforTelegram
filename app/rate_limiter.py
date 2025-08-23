import time
import logging
from typing import Dict, Tuple, Optional
from collections import defaultdict
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class RateLimiter:
    """Простой rate limiter на основе sliding window"""
    
    def __init__(self, requests_per_minute: int = 60, requests_per_hour: int = 1000):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.minute_requests: Dict[str, list] = defaultdict(list)
        self.hour_requests: Dict[str, list] = defaultdict(list)
    
    def _cleanup_old_requests(self, client_id: str, current_time: float):
        """Очистка старых запросов"""
        # Очистка минутных запросов (старше 60 секунд)
        self.minute_requests[client_id] = [
            req_time for req_time in self.minute_requests[client_id]
            if current_time - req_time < 60
        ]
        
        # Очистка часовых запросов (старше 3600 секунд)
        self.hour_requests[client_id] = [
            req_time for req_time in self.hour_requests[client_id]
            if current_time - req_time < 3600
        ]
    
    def is_allowed(self, client_id: str) -> Tuple[bool, Dict[str, int]]:
        """Проверка, разрешен ли запрос"""
        current_time = time.time()
        self._cleanup_old_requests(client_id, current_time)
        
        # Проверка лимитов
        minute_count = len(self.minute_requests[client_id])
        hour_count = len(self.hour_requests[client_id])
        
        minute_allowed = minute_count < self.requests_per_minute
        hour_allowed = hour_count < self.requests_per_hour
        
        if minute_allowed and hour_allowed:
            # Добавляем текущий запрос
            self.minute_requests[client_id].append(current_time)
            self.hour_requests[client_id].append(current_time)
            
            return True, {
                'minute_remaining': self.requests_per_minute - minute_count - 1,
                'hour_remaining': self.requests_per_hour - hour_count - 1
            }
        
        return False, {
            'minute_remaining': max(0, self.requests_per_minute - minute_count),
            'hour_remaining': max(0, self.requests_per_hour - hour_count)
        }


# Глобальный экземпляр rate limiter
rate_limiter = RateLimiter()


def get_client_id(request: Request) -> str:
    """Получение идентификатора клиента"""
    # Приоритет: X-Forwarded-For -> X-Real-IP -> client.host
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    return request.client.host if request.client else "unknown"


def rate_limit_middleware(request: Request, call_next):
    """Middleware для rate limiting"""
    client_id = get_client_id(request)
    
    # Пропускаем health check и статические файлы
    if request.url.path in ["/", "/docs", "/openapi.json", "/favicon.ico"]:
        return call_next(request)
    
    is_allowed, limits = rate_limiter.is_allowed(client_id)
    
    if not is_allowed:
        logger.warning(f"Rate limit exceeded for client: {client_id}")
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "message": "Too many requests. Please try again later.",
                "limits": limits
            },
            headers={
                "X-RateLimit-Minute-Remaining": str(limits['minute_remaining']),
                "X-RateLimit-Hour-Remaining": str(limits['hour_remaining']),
                "Retry-After": "60"
            }
        )
    
    # Добавляем заголовки с информацией о лимитах
    response = call_next(request)
    response.headers["X-RateLimit-Minute-Remaining"] = str(limits['minute_remaining'])
    response.headers["X-RateLimit-Hour-Remaining"] = str(limits['hour_remaining'])
    
    return response


def rate_limit_decorator(requests_per_minute: int = 60, requests_per_hour: int = 1000):
    """Декоратор для rate limiting конкретных эндпоинтов"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Здесь можно добавить логику для конкретных эндпоинтов
            # Пока используем глобальный rate limiter
            return func(*args, **kwargs)
        return wrapper
    return decorator
