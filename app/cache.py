import hashlib
import json
import time
from typing import Any, Optional, Dict
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class MemoryCache:
    """Простое кэширование в памяти"""
    
    def __init__(self, default_ttl: int = 3600):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Генерация ключа кэша на основе аргументов"""
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items())
        }
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Получение значения из кэша"""
        if key not in self._cache:
            return None
        
        cache_entry = self._cache[key]
        if time.time() > cache_entry['expires_at']:
            del self._cache[key]
            return None
        
        logger.debug(f"Cache hit for key: {key}")
        return cache_entry['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Установка значения в кэш"""
        ttl = ttl or self.default_ttl
        self._cache[key] = {
            'value': value,
            'expires_at': time.time() + ttl
        }
        logger.debug(f"Cache set for key: {key}, TTL: {ttl}s")
    
    def delete(self, key: str) -> None:
        """Удаление значения из кэша"""
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache deleted for key: {key}")
    
    def clear(self) -> None:
        """Очистка всего кэша"""
        self._cache.clear()
        logger.info("Cache cleared")
    
    def size(self) -> int:
        """Размер кэша"""
        return len(self._cache)


# Глобальный экземпляр кэша
cache = MemoryCache()


def cached(ttl: Optional[int] = None, key_prefix: str = ""):
    """Декоратор для кэширования результатов функций"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Генерируем ключ кэша
            cache_key = f"{key_prefix}:{cache._generate_key(*args, **kwargs)}"
            
            # Пытаемся получить из кэша
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Выполняем функцию и кэшируем результат
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator


def cache_invalidate(pattern: str = None):
    """Декоратор для инвалидации кэша"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            if pattern:
                # Удаляем все ключи, соответствующие паттерну
                keys_to_delete = [key for key in cache._cache.keys() if pattern in key]
                for key in keys_to_delete:
                    cache.delete(key)
                logger.info(f"Invalidated {len(keys_to_delete)} cache entries with pattern: {pattern}")
            else:
                # Очищаем весь кэш
                cache.clear()
            
            return result
        return wrapper
    return decorator
