"""
Production configuration
"""
import os
from typing import List

# Security
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is required in production")

# CORS
ALLOWED_ORIGINS: List[str] = [
    "https://your-domain.com",
    "https://www.your-domain.com",
    "https://app.your-domain.com",
]

# Trusted Hosts
TRUSTED_HOSTS: List[str] = [
    "your-domain.com",
    "www.your-domain.com",
    "api.your-domain.com",
]

# Database (if using external database)
DATABASE_URL = os.getenv("DATABASE_URL")

# Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "json"
LOG_FILE = "/var/log/app/app.log"
LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

# API Configuration
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "60"))
MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB

# Rate Limiting
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))

# Cache
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))
CACHE_MAX_SIZE = int(os.getenv("CACHE_MAX_SIZE", "1000"))

# Monitoring
ENABLE_METRICS = os.getenv("ENABLE_METRICS", "true").lower() == "true"
METRICS_PORT = int(os.getenv("METRICS_PORT", "9090"))

# Health Checks
HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))
HEALTH_CHECK_TIMEOUT = int(os.getenv("HEALTH_CHECK_TIMEOUT", "10"))

# External APIs
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY")

if not DEEPSEEK_API_KEY:
    raise ValueError("DEEPSEEK_API_KEY environment variable is required")

if not STABILITY_API_KEY:
    raise ValueError("STABILITY_API_KEY environment variable is required")

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_ENABLED = os.getenv("TELEGRAM_ENABLED", "true").lower() == "true"

# Server
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
WORKERS = int(os.getenv("WORKERS", "4"))

# SSL/TLS
SSL_CERT_FILE = os.getenv("SSL_CERT_FILE")
SSL_KEY_FILE = os.getenv("SSL_KEY_FILE")

# Backup
BACKUP_ENABLED = os.getenv("BACKUP_ENABLED", "true").lower() == "true"
BACKUP_INTERVAL_HOURS = int(os.getenv("BACKUP_INTERVAL_HOURS", "24"))
BACKUP_RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "7"))

# Performance
MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "100"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))

# Security Headers
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    ),
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
}

# Alerts
ALERT_EMAIL = os.getenv("ALERT_EMAIL")
ALERT_WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL")

# Performance Monitoring
ENABLE_PROFILING = os.getenv("ENABLE_PROFILING", "false").lower() == "true"
PROFILING_OUTPUT_DIR = os.getenv("PROFILING_OUTPUT_DIR", "/tmp/profiling")

# Error Reporting
SENTRY_DSN = os.getenv("SENTRY_DSN")
ENABLE_SENTRY = bool(SENTRY_DSN)

# Feature Flags
FEATURE_FLAGS = {
    "enable_webhooks": os.getenv("ENABLE_WEBHOOKS", "true").lower() == "true",
    "enable_admin_panel": os.getenv("ENABLE_ADMIN_PANEL", "true").lower() == "true",
    "enable_metrics": ENABLE_METRICS,
    "enable_backup": BACKUP_ENABLED,
}
