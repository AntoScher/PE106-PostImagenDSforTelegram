import pytest
import time
from app.cache import MemoryCache, cached, cache_invalidate


class TestMemoryCache:
    """Тесты для кэша в памяти"""
    
    def test_cache_init(self):
        """Тест инициализации кэша"""
        cache = MemoryCache(default_ttl=3600)
        assert cache.default_ttl == 3600
        assert cache.size() == 0
    
    def test_cache_set_get(self):
        """Тест установки и получения значения"""
        cache = MemoryCache()
        cache.set("test_key", "test_value")
        assert cache.get("test_key") == "test_value"
        assert cache.size() == 1
    
    def test_cache_get_nonexistent(self):
        """Тест получения несуществующего ключа"""
        cache = MemoryCache()
        assert cache.get("nonexistent") is None
    
    def test_cache_delete(self):
        """Тест удаления ключа"""
        cache = MemoryCache()
        cache.set("test_key", "test_value")
        assert cache.get("test_key") == "test_value"
        
        cache.delete("test_key")
        assert cache.get("test_key") is None
        assert cache.size() == 0
    
    def test_cache_clear(self):
        """Тест очистки кэша"""
        cache = MemoryCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert cache.size() == 2
        
        cache.clear()
        assert cache.size() == 0
        assert cache.get("key1") is None
        assert cache.get("key2") is None
    
    def test_cache_ttl_expiration(self):
        """Тест истечения TTL"""
        cache = MemoryCache(default_ttl=1)  # 1 секунда
        cache.set("test_key", "test_value")
        assert cache.get("test_key") == "test_value"
        
        time.sleep(1.1)  # Ждем истечения TTL
        assert cache.get("test_key") is None
        assert cache.size() == 0
    
    def test_cache_custom_ttl(self):
        """Тест пользовательского TTL"""
        cache = MemoryCache(default_ttl=3600)
        cache.set("test_key", "test_value", ttl=1)  # 1 секунда
        assert cache.get("test_key") == "test_value"
        
        time.sleep(1.1)
        assert cache.get("test_key") is None
    
    def test_cache_key_generation(self):
        """Тест генерации ключей"""
        cache = MemoryCache()
        
        # Тест с одинаковыми аргументами
        key1 = cache._generate_key("arg1", kwarg1="value1")
        key2 = cache._generate_key("arg1", kwarg1="value1")
        assert key1 == key2
        
        # Тест с разными аргументами
        key3 = cache._generate_key("arg2", kwarg1="value1")
        assert key1 != key3
        
        # Тест с разным порядком kwargs
        key4 = cache._generate_key("arg1", kwarg2="value2", kwarg1="value1")
        key5 = cache._generate_key("arg1", kwarg1="value1", kwarg2="value2")
        assert key4 == key5


class TestCacheDecorators:
    """Тесты для декораторов кэширования"""
    
    def test_cached_decorator(self):
        """Тест декоратора @cached"""
        call_count = 0
        
        @cached(ttl=3600)
        def test_function(arg1, arg2, kwarg1=None):
            nonlocal call_count
            call_count += 1
            return f"result_{arg1}_{arg2}_{kwarg1}"
        
        # Первый вызов
        result1 = test_function("a", "b", kwarg1="c")
        assert result1 == "result_a_b_c"
        assert call_count == 1
        
        # Второй вызов с теми же аргументами
        result2 = test_function("a", "b", kwarg1="c")
        assert result2 == "result_a_b_c"
        assert call_count == 1  # Функция не вызывалась снова
        
        # Вызов с другими аргументами
        result3 = test_function("x", "y", kwarg1="z")
        assert result3 == "result_x_y_z"
        assert call_count == 2
    
    def test_cached_decorator_with_key_prefix(self):
        """Тест декоратора @cached с префиксом ключа"""
        call_count = 0
        
        @cached(ttl=3600, key_prefix="test_prefix")
        def test_function(arg):
            nonlocal call_count
            call_count += 1
            return f"result_{arg}"
        
        result1 = test_function("test")
        result2 = test_function("test")
        
        assert result1 == result2
        assert call_count == 1
    
    def test_cache_invalidate_decorator(self):
        """Тест декоратора @cache_invalidate"""
        from app.cache import cache
        
        # Сначала добавляем данные в кэш
        cache.set("test_key_1", "value1")
        cache.set("test_key_2", "value2")
        cache.set("other_key", "value3")
        
        assert cache.size() == 3
        
        @cache_invalidate(pattern="test_key")
        def invalidate_function():
            return "invalidated"
        
        result = invalidate_function()
        assert result == "invalidated"
        assert cache.size() == 1  # Остался только other_key
        assert cache.get("other_key") == "value3"
    
    def test_cache_invalidate_no_pattern(self):
        """Тест декоратора @cache_invalidate без паттерна"""
        from app.cache import cache
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert cache.size() == 2
        
        @cache_invalidate()
        def invalidate_function():
            return "invalidated"
        
        result = invalidate_function()
        assert result == "invalidated"
        assert cache.size() == 0


class TestCacheIntegration:
    """Интеграционные тесты кэширования"""
    
    def test_cache_with_complex_objects(self):
        """Тест кэширования сложных объектов"""
        cache = MemoryCache()
        
        complex_data = {
            "list": [1, 2, 3],
            "dict": {"a": 1, "b": 2},
            "string": "test",
            "number": 42
        }
        
        cache.set("complex_key", complex_data)
        retrieved = cache.get("complex_key")
        
        assert retrieved == complex_data
        assert retrieved["list"] == [1, 2, 3]
        assert retrieved["dict"]["a"] == 1
    
    def test_cache_concurrent_access(self):
        """Тест конкурентного доступа к кэшу"""
        import threading
        
        cache = MemoryCache()
        results = []
        
        def worker(thread_id):
            for i in range(10):
                key = f"thread_{thread_id}_key_{i}"
                cache.set(key, f"value_{thread_id}_{i}")
                value = cache.get(key)
                results.append((thread_id, i, value))
        
        threads = []
        for i in range(3):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(results) == 30
        assert cache.size() == 30
        
        # Проверяем, что все значения корректны
        for thread_id, i, value in results:
            expected = f"value_{thread_id}_{i}"
            assert value == expected
    
    def test_cache_memory_efficiency(self):
        """Тест эффективности использования памяти"""
        cache = MemoryCache()
        
        # Добавляем много данных
        for i in range(1000):
            cache.set(f"key_{i}", f"value_{i}" * 100)  # Большие значения
        
        assert cache.size() == 1000
        
        # Проверяем, что все данные доступны
        for i in range(1000):
            value = cache.get(f"key_{i}")
            assert value == f"value_{i}" * 100
        
        # Очищаем кэш
        cache.clear()
        assert cache.size() == 0
