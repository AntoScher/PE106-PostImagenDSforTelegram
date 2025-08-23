from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from .generators import ContentGenerator
from .telegram_bot import telegram_bot
from . import webhooks  # Импортируем роутер вебхуков
from .cache import cached, cache_invalidate
from .rate_limiter import rate_limit_middleware
from .monitoring import metrics_collector, health_checker, performance_profiler
from .validators import EnhancedGenerateRequest, ImageRequest, WebhookValidator
from .auth import auth_service, get_current_active_user, require_admin, Token, User
from .security import setup_security_middleware, security_middleware
from .logger import log_request, log_error, log_performance, LoggerMixin
import logging
import io
import time
import uuid
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Создаем экземпляр приложения
app = FastAPI(
    title="Blog Content Generator API",
    description="API для генерации блог-постов с помощью DeepSeek AI",
    version="3.0.0",
    openapi_tags=[
        {
            "name": "Аутентификация",
            "description": "Операции аутентификации и авторизации"
        },
        {
            "name": "Генерация",
            "description": "Операции для генерации контента"
        },
        {
            "name": "Утилиты",
            "description": "Вспомогательные эндпоинты"
        },
        {
            "name": "Мониторинг",
            "description": "Метрики и мониторинг системы"
        },
        {
            "name": "Администрирование",
            "description": "Административные функции"
        }
    ]
)

# Настройка безопасности
setup_security_middleware(app)

# Добавляем middleware для rate limiting и мониторинга
app.middleware("http")(rate_limit_middleware)

# Подключаем роутер вебхуков
app.include_router(webhooks.router, prefix="/api")


# Middleware для обработки исключений и логирования
@app.middleware("http")
async def catch_exceptions_and_log(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        response = await call_next(request)
        response_time = time.time() - start_time
        
        # Логируем запрос
        log_request(
            request_id=request_id,
            method=request.method,
            path=str(request.url.path),
            status_code=response.status_code,
            response_time=response_time
        )
        
        # Добавляем request_id в заголовки
        response.headers["X-Request-ID"] = request_id
        return response
        
    except Exception as e:
        response_time = time.time() - start_time
        
        # Логируем ошибку
        log_error(e, {
            "request_id": request_id,
            "method": request.method,
            "path": str(request.url.path),
            "response_time": response_time
        })
        
        # Отправляем уведомление об ошибке в Telegram
        error_msg = f"⚠️ Ошибка в API: {str(e)}"
        telegram_bot.send_async(BackgroundTasks(), error_msg)

        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "details": str(e),
                "request_id": request_id
            },
            headers={"X-Request-ID": request_id}
        )


# Монтирование статических файлов
app.mount("/static", StaticFiles(directory="static"), name="static")


# Инициализация генератора с ленивой загрузкой
def get_content_generator():
    if not hasattr(get_content_generator, "instance"):
        get_content_generator.instance = ContentGenerator()
    return get_content_generator.instance


# Модели запросов/ответов (используем улучшенную валидацию)


class PostResponse(BaseModel):
    topic: str
    title: str
    meta_description: str
    post_content: str
    image: Optional[str] = Field(None, description="Base64 encoded image")


class ErrorResponse(BaseModel):
    error: str
    details: str = None


# Эндпоинты
@app.get("/", tags=["Утилиты"], summary="Проверка работоспособности API")
async def root_health_check():
    # Отправляем уведомление о работоспособности
    telegram_bot.send_async(BackgroundTasks(), "🟢 API запущен и работает")
    return {"status": "active", "message": "Blog Generator API работает"}


@app.get("/topics",
         tags=["Утилиты"],
         summary="Получить список предопределенных тем")
@cached(ttl=3600, key_prefix="topics")
async def predefined_topics():
    return {
        "topics": [
            "Преимущества медитации",
            "Здоровое питание для занятых людей",
            "Советы по управлению временем",
            "Как начать свой бизнес",
            "Путешествия по бюджету"
        ]
    }





# Эндпоинт для тестирования Telegram
@app.post("/test-telegram",
          include_in_schema=False,
          summary="Тест Telegram уведомлений (скрыто)")
async def test_telegram(
        background_tasks: BackgroundTasks,
        message: str = "Тестовое уведомление от API"
):
    telegram_bot.send_async(background_tasks, f"🔔 {message}")
    return {"status": "test_notification_sent"}


# Обработка favicon
@app.get("/image/{topic}", 
          tags=["Генерация"], 
          summary="Получить изображение для темы")
async def get_image(
    topic: str,
    background_tasks: BackgroundTasks,
    generator: ContentGenerator = Depends(get_content_generator)
):
    try:
        # Генерация изображения
        image_prompt = generator.generate_image_prompt(topic)
        image_io = generator.image_generator.generate_image_with_text(image_prompt, topic)
        
        # Перематываем буфер в начало
        image_io.seek(0)
        
        return StreamingResponse(
            image_io,
            media_type="image/jpeg",
            headers={"Content-Disposition": f"attachment; filename={topic}.jpg"}
        )
    except Exception as e:
        error_msg = f"Ошибка генерации изображения: {str(e)}"
        logger.error(error_msg)
        telegram_bot.send_async(background_tasks, f"⚠️ {error_msg}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Ошибка генерации изображения", "details": str(e)}
        )


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/favicon.ico")


# Эндпоинты мониторинга
@app.get("/metrics",
         tags=["Мониторинг"],
         summary="Получить метрики API")
async def get_metrics():
    """Получение метрик API"""
    return metrics_collector.get_metrics_summary()


@app.get("/health",
         tags=["Мониторинг"],
         summary="Проверка здоровья системы")
async def health_check():
    """Проверка здоровья системы"""
    health_status = health_checker.check_health()
    overall_status = "healthy"
    
    # Проверяем, есть ли проблемы
    for check_name, check_result in health_status.items():
        if check_result.get('status') != 'healthy':
            overall_status = "unhealthy"
            break
    
    return {
        "status": overall_status,
        "timestamp": time.time(),
        "checks": health_status
    }


@app.get("/cache/status",
         tags=["Мониторинг"],
         summary="Статус кэша")
async def cache_status():
    """Получение статуса кэша"""
    from .cache import cache
    return {
        "size": cache.size(),
        "default_ttl": cache.default_ttl
    }


@app.post("/cache/clear",
          tags=["Мониторинг"],
          summary="Очистка кэша")
async def clear_cache():
    """Очистка кэша"""
    from .cache import cache
    cache.clear()
    return {"message": "Cache cleared successfully"}


# Эндпоинты аутентификации
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=100)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., regex=r"^[^@]+@[^@]+\.[^@]+$")
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str = Field(..., min_length=1, max_length=100)


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1, max_length=100)
    new_password: str = Field(..., min_length=8, max_length=100)


@app.post("/auth/login",
          response_model=Token,
          tags=["Аутентификация"],
          summary="Вход в систему")
async def login(request: LoginRequest):
    """Аутентификация пользователя"""
    token = auth_service.login(request.username, request.password)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


@app.post("/auth/register",
          tags=["Аутентификация"],
          summary="Регистрация нового пользователя")
async def register(request: RegisterRequest):
    """Регистрация нового пользователя"""
    success = auth_service.register(
        request.username, 
        request.email, 
        request.password, 
        request.full_name
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    return {"message": "User registered successfully"}


@app.post("/auth/change-password",
          tags=["Аутентификация"],
          summary="Смена пароля")
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Смена пароля пользователя"""
    success = auth_service.change_password(
        current_user.username,
        request.old_password,
        request.new_password
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect old password"
        )
    return {"message": "Password changed successfully"}


@app.get("/auth/me",
         tags=["Аутентификация"],
         summary="Получить информацию о текущем пользователе")
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Получение информации о текущем пользователе"""
    return current_user


# Защищенные эндпоинты генерации
@app.post("/generate",
          response_model=PostResponse,
          responses={500: {"model": ErrorResponse}},
          tags=["Генерация"],
          summary="Сгенерировать пост и изображение по теме")
@performance_profiler.profile("generate_post")
async def generate_post(
        request: EnhancedGenerateRequest,
        background_tasks: BackgroundTasks,
        current_user: User = Depends(get_current_active_user),
        generator: ContentGenerator = Depends(get_content_generator)
):
    """Генерация поста с аутентификацией"""
    start_time = time.time()
    
    try:
        result = generator.generate_post(request.topic, request.style)
        
        # Логируем производительность
        duration = time.time() - start_time
        log_performance("generate_post", duration, {
            "user_id": current_user.username,
            "topic": request.topic
        })

        # Отправляем уведомление в фоне
        telegram_bot.send_async(
            background_tasks,
            f"🚀 Сгенерирован новый пост!\n"
            f"👤 Пользователь: {current_user.username}\n"
            f"📌 Тема: {request.topic}\n"
            f"📝 Заголовок: {result['title']}"
        )

        # Если есть изображение - отправляем в Telegram
        if result.get("image"):
            background_tasks.add_task(
                telegram_bot.send_image,
                result["image"],
                f"🖼️ Изображение для поста: {result['title']}"
            )

        return result
    except Exception as e:
        duration = time.time() - start_time
        log_error(e, {
            "user_id": current_user.username,
            "topic": request.topic,
            "duration": duration
        })
        
        error_msg = f"Ошибка генерации: {str(e)}"
        telegram_bot.send_async(background_tasks, f"⚠️ {error_msg}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Ошибка генерации контента", "details": str(e)}
        )


# Административные эндпоинты
@app.get("/admin/users",
         tags=["Администрирование"],
         summary="Получить список пользователей (только для админов)")
async def get_users(admin: User = Depends(require_admin)):
    """Получение списка пользователей (только для администраторов)"""
    from .auth import fake_users_db
    users = []
    for username, user_data in fake_users_db.items():
        users.append({
            "username": username,
            "email": user_data.get("email"),
            "full_name": user_data.get("full_name"),
            "disabled": user_data.get("disabled", False)
        })
    return {"users": users}


@app.post("/admin/users/{username}/disable",
          tags=["Администрирование"],
          summary="Отключить пользователя (только для админов)")
async def disable_user(username: str, admin: User = Depends(require_admin)):
    """Отключение пользователя (только для администраторов)"""
    from .auth import fake_users_db
    if username not in fake_users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    fake_users_db[username]["disabled"] = True
    return {"message": f"User {username} disabled successfully"}


@app.post("/admin/users/{username}/enable",
          tags=["Администрирование"],
          summary="Включить пользователя (только для админов)")
async def enable_user(username: str, admin: User = Depends(require_admin)):
    """Включение пользователя (только для администраторов)"""
    from .auth import fake_users_db
    if username not in fake_users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    fake_users_db[username]["disabled"] = False
    return {"message": f"User {username} enabled successfully"}