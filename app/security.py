from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import time
import hashlib
import secrets
from typing import List, Optional
import os
from .logger import log_security_event

# Конфигурация CORS
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8080",
    "https://your-domain.com",
    "https://www.your-domain.com",
]

# Дополнительные домены из переменных окружения
additional_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
ALLOWED_ORIGINS.extend([origin.strip() for origin in additional_origins if origin.strip()])

# Trusted hosts
TRUSTED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "your-domain.com",
    "www.your-domain.com",
]

# Дополнительные хосты из переменных окружения
additional_hosts = os.getenv("TRUSTED_HOSTS", "").split(",")
TRUSTED_HOSTS.extend([host.strip() for host in additional_hosts if host.strip()])


def setup_security_middleware(app: FastAPI) -> None:
    """Настройка middleware безопасности"""
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=[
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-Requested-With",
        ],
    )
    
    # Trusted Host middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=TRUSTED_HOSTS
    )
    
    # Gzip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Security headers middleware
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


class RateLimitExceeded(HTTPException):
    """Исключение для превышения лимита запросов"""
    def __init__(self, retry_after: int = 60):
        super().__init__(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)}
        )


class SecurityMiddleware:
    """Middleware для дополнительной безопасности"""
    
    def __init__(self):
        self.request_counts = {}
        self.blocked_ips = set()
        self.suspicious_patterns = [
            "script", "javascript:", "vbscript:", "onload=", "onerror=",
            "../", "..\\", "union select", "drop table", "insert into",
            "exec(", "eval(", "document.cookie", "window.location"
        ]
    
    async def __call__(self, request: Request, call_next):
        # Проверка заблокированных IP
        client_ip = self._get_client_ip(request)
        if client_ip in self.blocked_ips:
            log_security_event("blocked_ip_access", details={"ip": client_ip})
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Проверка подозрительных паттернов
        if self._is_suspicious_request(request):
            log_security_event("suspicious_request", details={
                "ip": client_ip,
                "path": str(request.url.path),
                "query": str(request.query_params)
            })
            self.blocked_ips.add(client_ip)
            raise HTTPException(status_code=403, detail="Suspicious request detected")
        
        # Проверка размера запроса
        if request.method in ["POST", "PUT"]:
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB
                raise HTTPException(status_code=413, detail="Request too large")
        
        response = await call_next(request)
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Получение реального IP клиента"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def _is_suspicious_request(self, request: Request) -> bool:
        """Проверка на подозрительные паттерны"""
        # Проверка URL
        url_str = str(request.url).lower()
        for pattern in self.suspicious_patterns:
            if pattern in url_str:
                return True
        
        # Проверка User-Agent
        user_agent = request.headers.get("user-agent", "").lower()
        suspicious_agents = ["sqlmap", "nikto", "nmap", "scanner"]
        for agent in suspicious_agents:
            if agent in user_agent:
                return True
        
        return False


def validate_input(data: str, max_length: int = 1000) -> bool:
    """Валидация входных данных"""
    if not data or len(data) > max_length:
        return False
    
    # Проверка на подозрительные символы
    dangerous_chars = ["<", ">", "&", '"', "'", "\\", "/"]
    for char in dangerous_chars:
        if char in data:
            return False
    
    return True


def sanitize_filename(filename: str) -> str:
    """Очистка имени файла"""
    # Удаляем опасные символы
    dangerous_chars = ["<", ">", ":", '"', "|", "?", "*", "\\", "/"]
    for char in dangerous_chars:
        filename = filename.replace(char, "_")
    
    # Ограничиваем длину
    if len(filename) > 255:
        filename = filename[:255]
    
    return filename


def generate_secure_token(length: int = 32) -> str:
    """Генерация безопасного токена"""
    return secrets.token_urlsafe(length)


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """Хеширование пароля с солью"""
    if salt is None:
        salt = secrets.token_hex(16)
    
    # Используем PBKDF2 для хеширования
    import hashlib
    import os
    
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000,  # iterations
        dklen=32
    )
    
    return key.hex(), salt


def verify_password_hash(password: str, hash_value: str, salt: str) -> bool:
    """Проверка хеша пароля"""
    computed_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(computed_hash, hash_value)


class SecurityConfig:
    """Конфигурация безопасности"""
    
    # Настройки паролей
    MIN_PASSWORD_LENGTH = 8
    REQUIRE_SPECIAL_CHARS = True
    REQUIRE_NUMBERS = True
    REQUIRE_UPPERCASE = True
    
    # Настройки токенов
    TOKEN_EXPIRY_HOURS = 24
    REFRESH_TOKEN_EXPIRY_DAYS = 30
    
    # Настройки сессий
    MAX_SESSIONS_PER_USER = 5
    SESSION_TIMEOUT_MINUTES = 30
    
    # Настройки rate limiting
    REQUESTS_PER_MINUTE = 60
    REQUESTS_PER_HOUR = 1000
    BURST_LIMIT = 10
    
    @classmethod
    def validate_password(cls, password: str) -> tuple[bool, str]:
        """Валидация пароля"""
        if len(password) < cls.MIN_PASSWORD_LENGTH:
            return False, f"Password must be at least {cls.MIN_PASSWORD_LENGTH} characters long"
        
        if cls.REQUIRE_SPECIAL_CHARS and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            return False, "Password must contain at least one special character"
        
        if cls.REQUIRE_NUMBERS and not any(c.isdigit() for c in password):
            return False, "Password must contain at least one number"
        
        if cls.REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"
        
        return True, "Password is valid"


# Глобальный экземпляр middleware безопасности
security_middleware = SecurityMiddleware()
