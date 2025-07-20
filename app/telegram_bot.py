import os
import logging
from fastapi import BackgroundTasks
from pydantic import BaseModel
import requests

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
        """Отправка текстового сообщения в Telegram"""
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
    
    async def send_image(self, image_base64: str, caption: str = ""):
        """Отправка изображения в Telegram"""
        if not self.config.enabled or not self.config.bot_token or not self.config.chat_id:
            logger.warning("Telegram notifications disabled, image not sent")
            return
        
        url = f"https://api.telegram.org/bot{self.config.bot_token}/sendPhoto"
        
        try:
            # Декодируем base64 в байты
            import base64
            image_bytes = base64.b64decode(image_base64)
            
            # Создаем временный файл в памяти
            from io import BytesIO
            image_file = BytesIO(image_bytes)
            image_file.name = 'image.jpg'
            
            files = {'photo': image_file}
            data = {'chat_id': self.config.chat_id, 'caption': caption}
            
            response = requests.post(url, files=files, data=data, timeout=30)
            response.raise_for_status()
            logger.info("Image sent to Telegram successfully")
        except Exception as e:
            logger.error(f"Failed to send image to Telegram: {str(e)}")
            raise
    
    def send_async(self, background_tasks: BackgroundTasks, message: str):
        """Добавляет отправку сообщения в фоновые задачи"""
        if self.config.enabled:
            background_tasks.add_task(self.send_notification, message)
    
    def send_image_async(self, background_tasks: BackgroundTasks, image_bytes: bytes, caption: str):
        """Добавляет отправку изображения в фоновые задачи"""
        if self.config.enabled:
            background_tasks.add_task(self.send_image, image_bytes, caption)

# Создаем экземпляр бота
telegram_bot = TelegramBot()