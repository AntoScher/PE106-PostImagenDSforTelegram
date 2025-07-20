import os
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

class ImageGenerator:
    def __init__(self):
        self.api_key = os.getenv("STABILITY_API_KEY")
        if not self.api_key:
            raise ValueError("STABILITY_API_KEY environment variable not set")
        self.api_url = "https://api.stability.ai/v2beta/stable-image/generate/sd3"
        self.font_path = self._get_font_path()
        
    def _get_font_path(self):
        # Пытаемся найти шрифт в системе
        try:
            # Для Windows: шрифт Arial
            font_path = "C:/Windows/Fonts/arial.ttf"
            if Path(font_path).exists():
                return font_path
            
            # Для Linux: пробуем путь к шрифтам
            linux_path = "/usr/share/fonts/truetype/freefont/FreeMono.ttf"
            if Path(linux_path).exists():
                return linux_path
            
            # Если ничего не найдено, используем стандартный шрифт
            return None
        except Exception as e:
            logger.error(f"Font search error: {str(e)}")
            return None

    def generate_image(self, prompt):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "image/*"
        }
        data = {
            "prompt": prompt,
            "output_format": "jpeg",
        }
        files = {"none": ''}

        response = requests.post(
            self.api_url,
            headers=headers,
            files=files,
            data=data,
            stream=True
        )

        if response.status_code == 200:
            return BytesIO(response.content)
        else:
            error_msg = f"Image generation error: {response.status_code}, {response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def add_text_to_image(self, image_stream, text):
        try:
            # Открываем изображение из потока
            img = Image.open(image_stream).convert("RGBA")
            draw = ImageDraw.Draw(img)
            
            # Определяем шрифт
            font_size = 65
            if self.font_path:
                try:
                    font = ImageFont.truetype(self.font_path, font_size)
                except IOError:
                    font = ImageFont.load_default()
                    logger.warning("Font not found, using default")
            else:
                font = ImageFont.load_default()
                logger.warning("Font not found, using default")
            
            # Получаем размеры изображения
            img_width, img_height = img.size
            
            # Разбиваем текст на строки
            lines = []
            line = ""
            for word in text.split():
                # Проверяем ширину строки
                if draw.textlength(line + word, font=font) <= img_width - 200:
                    line += word + " "
                else:
                    lines.append(line.strip())
                    line = word + " "
            lines.append(line.strip())
            
            # Рассчитываем общую высоту текста
            line_height = font_size + 10
            text_height = len(lines) * line_height
            
            # Позиция текста (центрирование по горизонтали, 100px от верха)
            x = (img_width - img_width + 200) // 2
            y = 100
            
            # Создаем полупрозрачный фон для текста
            overlay = Image.new(
                "RGBA", 
                (img_width - 200, text_height + 20), 
                (0, 0, 128, 180)  # Темно-синий с прозрачностью
            )
            img.paste(overlay, (x, y), overlay)
            
            # Рисуем текст
            y_offset = y + 10
            for line in lines:
                text_width = draw.textlength(line, font=font)
                x_pos = (img_width - text_width) // 2
                draw.text((x_pos, y_offset), line, font=font, fill=(255, 255, 255, 255))
                y_offset += line_height
            
            # Сохраняем результат в временный файл
            output = BytesIO()
            img = img.convert("RGB")
            img.save(output, format="JPEG")
            output.seek(0)
            return output
        except Exception as e:
            logger.exception(f"Error adding text to image: {str(e)}")
            raise

    def generate_image_with_text(self, image_prompt, text):
        # Генерируем изображение
        image_stream = self.generate_image(image_prompt)
        # Добавляем текст
        return self.add_text_to_image(image_stream, text)
