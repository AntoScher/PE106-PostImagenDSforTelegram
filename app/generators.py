import os
import logging
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class ContentGenerator:
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable not set")
        self.timeout = 30

    def generate_with_deepseek(self, prompt, max_tokens=1024, temperature=0.7):
        """Генерация текста через DeepSeek API"""
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }

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
                return "Ошибка: Неверный формат ответа от DeepSeek API"

            return result['choices'][0]['message']['content'].strip()

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else None
            if status_code == 401:
                return "Ошибка: Неверный API ключ DeepSeek"
            elif status_code == 429:
                return "Ошибка: Превышен лимит запросов"
            return f"HTTP ошибка: {status_code or 'нет статуса'}"

        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка сети: {str(e)}")
            return f"Ошибка сети: {str(e)}"

        except Exception as e:
            logger.exception(f"Неизвестная ошибка: {str(e)}")
            return f"Критическая ошибка: {str(e)}"

    def generate_post(self, topic: str):
        """Генерация полного поста по теме"""
        # Генерация заголовка с проверкой
        title = self.generate_with_deepseek(
            f"Придумай цепляющий SEO-заголовок для поста на тему: {topic}",
            max_tokens=70
        )

        if not title or title.startswith("Ошибка"):
            return {
                "topic": topic,
                "title": f"Ошибка генерации заголовка для: {topic}",
                "meta_description": "",
                "post_content": ""
            }

        # Генерация мета-описания
        meta_prompt = (
            f"Создай мета-описание длиной 120-160 символов для поста: '{title}'. "
            f"Тема: {topic}. Включи основные ключевые слова."
        )
        meta_description = self.generate_with_deepseek(meta_prompt, max_tokens=160)

        # Генерация контента
        content_prompt = (
            f"Напиши развернутый SEO-оптимизированный пост на тему '{topic}' со структурой:\n"
            f"Заголовок: {title}\n"
            "- Используй подзаголовки H2 и H3\n"
            "- Короткие абзацы по 2-3 предложения\n"
            "- Маркированные списки для перечислений\n"
            "- Практические примеры и кейсы\n"
            "- Естественное включение ключевых слов\n"
            "- Заключение с выводом"
        )
        post_content = self.generate_with_deepseek(content_prompt, max_tokens=2048)

        return {
            "topic": topic,
            "title": title,
            "meta_description": meta_description,
            "post_content": post_content
        }