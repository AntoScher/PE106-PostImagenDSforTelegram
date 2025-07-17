import os
import requests
from dotenv import load_dotenv

load_dotenv()


class ContentGenerator:
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable not set")

    def generate_with_deepseek(self, prompt, max_tokens=1024, temperature=0.7):
        """Генерация текста через DeepSeek API"""
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
        except Exception as e:
            error_msg = f"Ошибка при генерации: {str(e)}"
            if response.status_code == 401:
                error_msg += " | Неверный API ключ"
            elif response.status_code == 429:
                error_msg += " | Превышен лимит запросов"
            return error_msg

    def generate_post(self, topic: str):
        """Генерация полного поста по теме"""
        # Генерация заголовка
        title = self.generate_with_deepseek(
            f"Придумай цепляющий заголовок для поста на тему: {topic}",
            max_tokens=50
        )

        if not title or "Ошибка" in title:
            return {
                "title": f"Ошибка: {topic}",
                "meta_description": "",
                "post_content": "Не удалось сгенерировать заголовок"
            }

        # Генерация мета-описания
        meta_description = self.generate_with_deepseek(
            f"Создай мета-описание длиной 120-160 символов для поста: {title}",
            max_tokens=100
        )

        # Генерация контента
        post_content = self.generate_with_deepseek(
            f"""Напиши SEO-оптимизированный пост на тему "{topic}" со структурой:
            ## {title}
            - Используй подзаголовки H3
            - Пиши короткими абзацами
            - Добавь практические примеры
            - Сделай текст полезным и легким для чтения""",
            max_tokens=2048
        )

        return {
            "topic": topic,
            "title": title,
            "meta_description": meta_description,
            "post_content": post_content
        }