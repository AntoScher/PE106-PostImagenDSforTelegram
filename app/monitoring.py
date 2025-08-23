import time
import logging
from typing import Dict, Any, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from fastapi import Request, Response
import json

logger = logging.getLogger(__name__)


@dataclass
class RequestMetrics:
    """Метрики запроса"""
    path: str
    method: str
    status_code: int
    response_time: float
    timestamp: datetime = field(default_factory=datetime.now)
    client_ip: str = ""
    user_agent: str = ""


@dataclass
class APIMetrics:
    """Метрики API"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    requests_per_minute: int = 0
    unique_clients: set = field(default_factory=set)
    endpoint_usage: Dict[str, int] = field(default_factory=dict)
    error_counts: Dict[str, int] = field(default_factory=dict)


class MetricsCollector:
    """Сборщик метрик"""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.request_history: deque = deque(maxlen=max_history)
        self.metrics = APIMetrics()
        self.start_time = datetime.now()
    
    def record_request(self, request: Request, response: Response, response_time: float):
        """Запись метрик запроса"""
        client_ip = self._get_client_ip(request)
        
        metric = RequestMetrics(
            path=str(request.url.path),
            method=request.method,
            status_code=response.status_code,
            response_time=response_time,
            client_ip=client_ip,
            user_agent=request.headers.get("user-agent", "")
        )
        
        self.request_history.append(metric)
        self._update_metrics(metric)
    
    def _get_client_ip(self, request: Request) -> str:
        """Получение IP клиента"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def _update_metrics(self, metric: RequestMetrics):
        """Обновление общих метрик"""
        self.metrics.total_requests += 1
        
        if 200 <= metric.status_code < 400:
            self.metrics.successful_requests += 1
        else:
            self.metrics.failed_requests += 1
        
        # Обновление среднего времени ответа
        if self.metrics.total_requests == 1:
            self.metrics.average_response_time = metric.response_time
        else:
            self.metrics.average_response_time = (
                (self.metrics.average_response_time * (self.metrics.total_requests - 1) + 
                 metric.response_time) / self.metrics.total_requests
            )
        
        # Уникальные клиенты
        self.metrics.unique_clients.add(metric.client_ip)
        
        # Использование эндпоинтов
        endpoint = f"{metric.method} {metric.path}"
        self.metrics.endpoint_usage[endpoint] = self.metrics.endpoint_usage.get(endpoint, 0) + 1
        
        # Подсчет ошибок
        if metric.status_code >= 400:
            error_type = f"{metric.status_code}"
            self.metrics.error_counts[error_type] = self.metrics.error_counts.get(error_type, 0) + 1
    
    def get_uptime(self) -> timedelta:
        """Получение времени работы"""
        return datetime.now() - self.start_time
    
    def get_recent_requests(self, minutes: int = 5) -> list[RequestMetrics]:
        """Получение недавних запросов"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        return [req for req in self.request_history if req.timestamp > cutoff_time]
    
    def get_requests_per_minute(self) -> int:
        """Получение количества запросов в минуту"""
        recent_requests = self.get_recent_requests(1)
        return len(recent_requests)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Получение сводки метрик"""
        return {
            "uptime_seconds": self.get_uptime().total_seconds(),
            "total_requests": self.metrics.total_requests,
            "successful_requests": self.metrics.successful_requests,
            "failed_requests": self.metrics.failed_requests,
            "success_rate": (
                self.metrics.successful_requests / self.metrics.total_requests * 100
                if self.metrics.total_requests > 0 else 0
            ),
            "average_response_time": round(self.metrics.average_response_time, 3),
            "requests_per_minute": self.get_requests_per_minute(),
            "unique_clients": len(self.metrics.unique_clients),
            "top_endpoints": dict(
                sorted(self.metrics.endpoint_usage.items(), 
                      key=lambda x: x[1], reverse=True)[:5]
            ),
            "error_distribution": self.metrics.error_counts
        }


# Глобальный экземпляр сборщика метрик
metrics_collector = MetricsCollector()


class MonitoringMiddleware:
    """Middleware для мониторинга"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        start_time = time.time()
        
        # Создаем обертку для send
        async def send_wrapper(message):
            await send(message)
            
            if message["type"] == "http.response.start":
                response_time = time.time() - start_time
                
                # Создаем мок объекты для совместимости
                class MockRequest:
                    def __init__(self, scope):
                        self.url = type('URL', (), {'path': scope['path']})()
                        self.method = scope['method']
                        self.headers = dict(scope['headers'])
                        self.client = type('Client', (), {'host': 'unknown'})()
                
                class MockResponse:
                    def __init__(self, status_code):
                        self.status_code = status_code
                
                request = MockRequest(scope)
                response = MockResponse(message.get('status', 500))
                
                metrics_collector.record_request(request, response, response_time)
        
        await self.app(scope, receive, send_wrapper)


class HealthChecker:
    """Проверка здоровья системы"""
    
    def __init__(self):
        self.checks = {}
        self.last_check = {}
    
    def add_check(self, name: str, check_func, interval_seconds: int = 60):
        """Добавление проверки здоровья"""
        self.checks[name] = {
            'function': check_func,
            'interval': interval_seconds
        }
    
    def check_health(self) -> Dict[str, Any]:
        """Выполнение всех проверок здоровья"""
        current_time = time.time()
        results = {}
        
        for name, check_info in self.checks.items():
            # Проверяем, нужно ли выполнять проверку
            last_check_time = self.last_check.get(name, 0)
            if current_time - last_check_time < check_info['interval']:
                # Возвращаем кэшированный результат
                continue
            
            try:
                result = check_info['function']()
                results[name] = {
                    'status': 'healthy' if result else 'unhealthy',
                    'timestamp': current_time,
                    'details': result
                }
                self.last_check[name] = current_time
            except Exception as e:
                results[name] = {
                    'status': 'error',
                    'timestamp': current_time,
                    'error': str(e)
                }
                self.last_check[name] = current_time
        
        return results


# Глобальный экземпляр проверки здоровья
health_checker = HealthChecker()


def check_database_connection():
    """Проверка подключения к базе данных (заглушка)"""
    # В данном проекте нет БД, поэтому возвращаем True
    return True


def check_external_apis():
    """Проверка доступности внешних API"""
    try:
        # Здесь можно добавить проверки DeepSeek и Stability AI
        return True
    except Exception as e:
        logger.error(f"External API check failed: {e}")
        return False


def check_disk_space():
    """Проверка свободного места на диске"""
    try:
        import shutil
        total, used, free = shutil.disk_usage("/")
        free_gb = free / (1024**3)
        return free_gb > 1.0  # Минимум 1GB свободного места
    except Exception as e:
        logger.error(f"Disk space check failed: {e}")
        return False


# Инициализация проверок здоровья
health_checker.add_check("database", check_database_connection, 30)
health_checker.add_check("external_apis", check_external_apis, 60)
health_checker.add_check("disk_space", check_disk_space, 300)


class PerformanceProfiler:
    """Профилировщик производительности"""
    
    def __init__(self):
        self.profiles = {}
    
    def start_profile(self, name: str):
        """Начало профилирования"""
        self.profiles[name] = time.time()
    
    def end_profile(self, name: str) -> float:
        """Завершение профилирования"""
        if name in self.profiles:
            duration = time.time() - self.profiles[name]
            del self.profiles[name]
            return duration
        return 0.0
    
    def profile(self, name: str):
        """Декоратор для профилирования функций"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                self.start_profile(name)
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = self.end_profile(name)
                    logger.info(f"Profile {name}: {duration:.3f}s")
            return wrapper
        return decorator


# Глобальный экземпляр профилировщика
performance_profiler = PerformanceProfiler()
