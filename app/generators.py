import os
import time
import requests
from dotenv import load_dotenv
from pathlib import Path
import logging

# Определяем путь к .env файлу
env_path = Path(__file__).resolve().parent.parent / '.env'

# Загружаем .env с явным указанием кодировки и обработкой BOM
load_dotenv(dotenv_path=env_path, encoding='utf-8-sig')  # Используем utf-8-sig для обработки BOM

logger = logging.getLogger(__name__)

class ContentGenerator:
    def __init__(self):
        # Для отладки: выводим путь к .env
        logger.info(f"Loading .env from: {env_path}")
        if env_path.exists():
            logger.info(".env file exists")
        else:
            logger.error(".env file not found!")

        # Получаем API ключ
        self.api_key = os.getenv("DEEPSEEK_API_KEY")

        # Если ключ не найден, логируем все переменные
        if not self.api_key:
            # Собираем все переменные окружения
            env_vars = "\n".join([f"{k}: {v}" for k, v in os.environ.items()])
            logger.error(f"DEEPSEEK_API_KEY not found. All environment variables:\n{env_vars}")
            raise ValueError("DEEPSEEK_API_KEY environment variable not set")

        logger.info(f"DeepSeek API key loaded: {self.api_key[:5]}...{self.api_key[-5:]}")
        self.timeout = 60  # Таймаут для запросов (60 секунд)

    def generate_with_deepseek(self, prompt, max_tokens=1024, temperature=0.7):
        """Генерация текста через DeepSeek API с повторами"""
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }

        # Пытаемся выполнить запрос с повторами
        for attempt in range(3):  # 3 попытки
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status()
                result = response.json()

                # Проверка структуры ответа
                if not result.get('choices') or not result['choices'][0].get('message', {}).get('content'):
                    logger.error(f"Неверный формат ответа DeepSeek: {result}")
                    return None

                return result['choices'][0]['message']['content'].strip()

            except requests.exceptions.Timeout:
                logger.warning(f"Таймаут запроса (попытка {attempt + 1}/3)")
                if attempt < 2:
                    time.sleep(2)  # Ждем 2 секунды перед повторной попыткой
                    continue
                raise  # После 3 попыток пробрасываем исключение

            except requests.exceptions.RequestException as e:
                logger.error(f"Ошибка сети: {str(e)}")
                raise

    def generate_post(self, topic: str):
        """Генерация полного поста по теме"""
        try:
            # Оптимизированный промпт для генерации всего контента
            prompt = (
                f"Сгенерируй SEO-оптимизированный пост на тему '{topic}' со следующей структурой:\n"
                "1. Цепляющий SEO-заголовок (не более 70 символов)\n"
                "2. Мета-описание длиной 120-160 символов с ключевыми словами\n"
                "3. Основной контент с подзаголовками H2/H3, короткими абзацами, "
                "маркированными списками и практическими примерами\n\n"
                "Формат вывода:\n"
                "Заголовок: [здесь заголовок]\n"
                "Мета-описание: [здесь мета-описание]\n"
                "Контент: [здесь контент]"
            )

            full_content = self.generate_with_deepseek(prompt, max_tokens=3072)

            if not full_content:
                return {
                    "topic": topic,
                    "title": "Ошибка генерации",
                    "meta_description": "",
                    "post_content": "Не удалось получить данные от DeepSeek API"
                }

            # Парсинг ответа
            title = ""
            meta_description = ""
            post_content = ""

            # Извлекаем компоненты из ответа
            if "Заголовок:" in full_content:
                title = full_content.split("Заголовок:", 1)[1].split("\n", 1)[0].strip()
            if "Мета-описание:" in full_content:
                meta_description = full_content.split("Мета-описание:", 1)[1].split("\n", 1)[0].strip()
            if "Контент:" in full_content:
                post_content = full_content.split("Контент:", 1)[1].strip()

            # Очистка от лишних символов
            title = title.strip().lstrip('*# ').strip()
            meta_description = meta_description.strip().lstrip('*# ').strip()
            post_content = post_content.strip().lstrip('*# ').strip()

            return {
                "topic": topic,
                "title": title if title else f"Пост на тему: {topic}",
                "meta_description": meta_description,
                "post_content": post_content
            }

        except Exception as e:
            logger.exception(f"Ошибка генерации поста: {str(e)}")
            return {
                "topic": topic,
                "title": "Ошибка генерации",
                "meta_description": "",
                "post_content": f"Произошла ошибка: {str(e)}"
            }