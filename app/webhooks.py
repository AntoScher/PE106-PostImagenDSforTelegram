from fastapi import APIRouter, BackgroundTasks, Request
from pydantic import BaseModel
from .telegram_bot import telegram_bot

router = APIRouter()


class WebhookRequest(BaseModel):
    event: str
    data: dict


@router.post("/webhook", include_in_schema=False)
async def handle_webhook(
        request: Request,
        webhook: WebhookRequest,
        background_tasks: BackgroundTasks
):
    BASE_URL = str(request.base_url).rstrip("/")
    message = ""

    if webhook.event == "new_generation":
        topic = webhook.data.get("topic", "unknown topic")
        title = webhook.data.get("title", "untitled")
        message = (
            f"🚀 <b>Новый пост сгенерирован!</b>\n"
            f"📌 Тема: <code>{topic}</code>\n"
            f"📝 Заголовок: {title}\n"
            f"🌐 Ссылка: <a href='{BASE_URL}/docs'>Swagger UI</a>"
        )

    elif webhook.event == "health_check":
        message = "🟢 API работает корректно!"

    elif webhook.event == "error":
        error = webhook.data.get("message", "unknown error")
        message = f"⚠️ <b>Ошибка в API!</b>\n{error}"

    # Отправляем уведомление
    telegram_bot.send_async(background_tasks, message)

    return {"status": "notification_sent"}