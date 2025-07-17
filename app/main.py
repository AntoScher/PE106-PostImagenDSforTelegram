from fastapi import FastAPI, HTTPException
from .generators import ContentGenerator
from pydantic import BaseModel

app = FastAPI(
    title="Blog Content Generator API",
    description="API для генерации блог-постов с помощью DeepSeek AI",
    version="1.0.0"
)

class GenerateRequest(BaseModel):
    topic: str

generator = ContentGenerator()

@app.get("/")
def health_check():
    return {"status": "active", "message": "Blog Generator API is running"}

@app.post("/generate")
def generate_post(request: GenerateRequest):
    try:
        result = generator.generate_post(request.topic)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка генерации контента: {str(e)}"
        )

@app.get("/topics")
def predefined_topics():
    return {
        "topics": [
            "Преимущества медитации",
            "Здоровое питание для занятых людей",
            "Советы по управлению временем",
            "Как начать свой бизнес",
            "Путешествия по бюджету"
        ]
    }