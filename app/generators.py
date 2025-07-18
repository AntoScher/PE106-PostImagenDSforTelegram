import os
import time
import requests
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)


class ContentGenerator:
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable not set")
        self.timeout = 60  # Увеличиваем таймаут до 60 секунд

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
        """Генерация полного поста по теме в одном запросе"""
        try:
            # Оптимизированный промпт для генерации всего контента в одном запросе
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