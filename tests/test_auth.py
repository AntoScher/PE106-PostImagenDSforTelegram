import pytest
from unittest.mock import patch, MagicMock
import os
from app.auth import (
    auth_service, verify_password, get_password_hash, 
    create_access_token, authenticate_user, fake_users_db
)
from app.security import SecurityConfig


class TestAuthService:
    """Тесты для сервиса аутентификации"""
    
    def test_login_success(self):
        """Тест успешного входа"""
        token = auth_service.login("admin", "admin123")
        assert token is not None
        assert token.access_token is not None
        assert token.token_type == "bearer"
    
    def test_login_invalid_credentials(self):
        """Тест входа с неверными данными"""
        token = auth_service.login("admin", "wrong_password")
        assert token is None
    
    def test_login_nonexistent_user(self):
        """Тест входа несуществующего пользователя"""
        token = auth_service.login("nonexistent", "password")
        assert token is None
    
    def test_register_success(self):
        """Тест успешной регистрации"""
        success = auth_service.register(
            "newuser", 
            "newuser@example.com", 
            "password123", 
            "New User"
        )
        assert success is True
        assert "newuser" in fake_users_db
    
    def test_register_existing_user(self):
        """Тест регистрации существующего пользователя"""
        success = auth_service.register(
            "admin", 
            "admin@example.com", 
            "password123", 
            "Admin"
        )
        assert success is False
    
    def test_change_password_success(self):
        """Тест успешной смены пароля"""
        success = auth_service.change_password("user", "user123", "newpassword123")
        assert success is True
    
    def test_change_password_wrong_old_password(self):
        """Тест смены пароля с неверным старым паролем"""
        success = auth_service.change_password("user", "wrong_password", "newpassword123")
        assert success is False


class TestPasswordHashing:
    """Тесты для хеширования паролей"""
    
    def test_password_hashing(self):
        """Тест хеширования пароля"""
        password = "test_password"
        hashed = get_password_hash(password)
        assert hashed != password
        assert verify_password(password, hashed) is True
    
    def test_password_verification_wrong_password(self):
        """Тест проверки неверного пароля"""
        password = "test_password"
        hashed = get_password_hash(password)
        assert verify_password("wrong_password", hashed) is False


class TestTokenCreation:
    """Тесты для создания токенов"""
    
    def test_create_access_token(self):
        """Тест создания токена доступа"""
        data = {"sub": "testuser"}
        token = create_access_token(data)
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0


class TestUserAuthentication:
    """Тесты для аутентификации пользователей"""
    
    def test_authenticate_user_success(self):
        """Тест успешной аутентификации пользователя"""
        user = authenticate_user(fake_users_db, "admin", "admin123")
        assert user is not None
        assert user.username == "admin"
    
    def test_authenticate_user_wrong_password(self):
        """Тест аутентификации с неверным паролем"""
        user = authenticate_user(fake_users_db, "admin", "wrong_password")
        assert user is None
    
    def test_authenticate_nonexistent_user(self):
        """Тест аутентификации несуществующего пользователя"""
        user = authenticate_user(fake_users_db, "nonexistent", "password")
        assert user is None


class TestSecurityConfig:
    """Тесты для конфигурации безопасности"""
    
    def test_validate_password_valid(self):
        """Тест валидации корректного пароля"""
        password = "ValidPass123!"
        is_valid, message = SecurityConfig.validate_password(password)
        assert is_valid is True
        assert "valid" in message.lower()
    
    def test_validate_password_too_short(self):
        """Тест валидации короткого пароля"""
        password = "short"
        is_valid, message = SecurityConfig.validate_password(password)
        assert is_valid is False
        assert "characters" in message
    
    def test_validate_password_no_special_chars(self):
        """Тест валидации пароля без специальных символов"""
        password = "ValidPass123"
        is_valid, message = SecurityConfig.validate_password(password)
        assert is_valid is False
        assert "special" in message
    
    def test_validate_password_no_numbers(self):
        """Тест валидации пароля без цифр"""
        password = "ValidPass!"
        is_valid, message = SecurityConfig.validate_password(password)
        assert is_valid is False
        assert "number" in message
    
    def test_validate_password_no_uppercase(self):
        """Тест валидации пароля без заглавных букв"""
        password = "validpass123!"
        is_valid, message = SecurityConfig.validate_password(password)
        assert is_valid is False
        assert "uppercase" in message


class TestAuthIntegration:
    """Интеграционные тесты аутентификации"""
    
    def test_full_auth_flow(self):
        """Тест полного цикла аутентификации"""
        # Регистрация
        success = auth_service.register(
            "testuser", 
            "test@example.com", 
            "TestPass123!", 
            "Test User"
        )
        assert success is True
        
        # Вход
        token = auth_service.login("testuser", "TestPass123!")
        assert token is not None
        
        # Смена пароля
        success = auth_service.change_password("testuser", "TestPass123!", "NewPass123!")
        assert success is True
        
        # Вход с новым паролем
        token = auth_service.login("testuser", "NewPass123!")
        assert token is not None
        
        # Очистка
        if "testuser" in fake_users_db:
            del fake_users_db["testuser"]
