from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from .generators import ContentGenerator

import logging

logger = logging.getLogger(__name__)



# Сначала создаем экземпляр приложения
app = FastAPI(
    title="Blog Content Generator API",
    description="API для генерации блог-постов с помощью DeepSeek AI",
    version="1.0.0",
    openapi_tags=[
        {
            "name": "Генерация",
            "description": "Операции для генерации контента"
        },
        {
            "name": "Утилиты",
            "description": "Вспомогательные эндпоинты"
        }
    ]
)

# Middleware должен регистрироваться ПОСЛЕ создания app
@app.middleware("http")
async def catch_exceptions(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "details": str(e)
            }
        )

# Монтирование статических файлов
app.mount("/static", StaticFiles(directory="static"), name="static")

# Инициализация генератора с ленивой загрузкой
def get_content_generator():
    if not hasattr(get_content_generator, "instance"):
        get_content_generator.instance = ContentGenerator()
    return get_content_generator.instance

# Модели запросов/ответов
class GenerateRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=100,
                      example="Здоровое питание",
                      description="Тема для генерации поста")

class PostResponse(BaseModel):
    topic: str
    title: str
    meta_description: str
    post_content: str

class ErrorResponse(BaseModel):
    error: str
    details: str = None

# Эндпоинты
@app.get("/", tags=["Утилиты"], summary="Проверка работоспособности API")
async def health_check():
    return {"status": "active", "message": "Blog Generator API работает"}

@app.post("/generate",
          response_model=PostResponse,
          responses={500: {"model": ErrorResponse}},
          tags=["Генерация"],
          summary="Генерация поста по теме")
async def generate_post(
    request: GenerateRequest,
    generator: ContentGenerator = Depends(get_content_generator)
):
    try:
        result = generator.generate_post(request.topic)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Ошибка генерации контента",
                "details": str(e)
            }
        )

@app.get("/topics",
         tags=["Утилиты"],
         summary="Получить список предопределенных тем")
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

# Отдельная обработка favicon для избежания ошибок 404
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/favicon.ico")