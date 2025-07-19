import os
import requests
import logging
from fastapi import BackgroundTasks
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class TelegramConfig(BaseModel):
    bot_token: str
    chat_id: str
    enabled: bool = True


class TelegramBot:
    def __init__(self):
        self.config = self.load_config()

    def load_config(self) -> TelegramConfig:
        return TelegramConfig(
            bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
            enabled=os.getenv("TELEGRAM_ENABLED", "true").lower() == "true"
        )

    async def send_notification(self, message: str):
        """Отправка сообщения в Telegram"""
        if not self.config.enabled or not self.config.bot_token or not self.config.chat_id:
            logger.warning("Telegram notifications disabled or misconfigured")
            return

        url = f"https://api.telegram.org/bot{self.config.bot_token}/sendMessage"
        payload = {
            "chat_id": self.config.chat_id,
            "text": message,
            "parse_mode": "HTML"
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info("Telegram notification sent successfully")
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {str(e)}")

    def send_async(self, background_tasks: BackgroundTasks, message: str):
        """Добавляет отправку сообщения в фоновые задачи"""
        if self.config.enabled:
            background_tasks.add_task(self.send_notification, message)


# Создаем экземпляр бота для использования
telegram_bot = TelegramBot()