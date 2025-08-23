import pytest
from unittest.mock import patch, MagicMock
import os
from app.generators import ContentGenerator


class TestContentGenerator:
    @patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'test_key'})
    def test_init_success(self):
        """Тест успешной инициализации генератора"""
        generator = ContentGenerator()
        assert generator.api_key == 'test_key'
        assert generator.timeout == 60

    def test_init_no_api_key(self):
        """Тест инициализации без API ключа"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="DEEPSEEK_API_KEY environment variable not set"):
                ContentGenerator()

    def test_generate_image_prompt(self):
        """Тест генерации промпта для изображения"""
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'test_key'}):
            generator = ContentGenerator()
            prompt = generator.generate_image_prompt("Тестовая тема")
            assert "Тестовая тема" in prompt
            assert "High-quality illustration" in prompt

    @patch('app.generators.requests.post')
    def test_generate_with_deepseek_success(self, mock_post):
        """Тест успешной генерации через DeepSeek"""
        # Мокаем успешный ответ
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'Generated content'}}]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'test_key'}):
            generator = ContentGenerator()
            result = generator.generate_with_deepseek("Test prompt")
            assert result == "Generated content"

    @patch('app.generators.requests.post')
    def test_generate_with_deepseek_timeout_retry(self, mock_post):
        """Тест повторных попыток при таймауте"""
        from requests.exceptions import Timeout
        
        # Первые две попытки - таймаут, третья - успех
        mock_post.side_effect = [
            Timeout("Request timeout"),
            Timeout("Request timeout"),
            MagicMock(
                json=lambda: {'choices': [{'message': {'content': 'Success'}}]},
                raise_for_status=lambda: None
            )
        ]

        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'test_key'}):
            generator = ContentGenerator()
            result = generator.generate_with_deepseek("Test prompt")
            assert result == "Success"
            assert mock_post.call_count == 3

    @patch('app.generators.requests.post')
    def test_generate_with_deepseek_max_retries(self, mock_post):
        """Тест максимального количества попыток"""
        from requests.exceptions import Timeout
        
        # Все попытки заканчиваются таймаутом
        mock_post.side_effect = Timeout("Request timeout")

        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'test_key'}):
            generator = ContentGenerator()
            with pytest.raises(Timeout):
                generator.generate_with_deepseek("Test prompt")
            assert mock_post.call_count == 3

    @patch('app.generators.ContentGenerator.generate_with_deepseek')
    @patch('app.generators.ContentGenerator.generate_image_prompt')
    @patch('app.image_generator.ImageGenerator.generate_image_with_text')
    def test_generate_post_success(self, mock_image_gen, mock_prompt, mock_text_gen):
        """Тест успешной генерации поста"""
        # Мокаем генерацию текста
        mock_text_gen.return_value = """
        Заголовок: Тестовый заголовок
        Мета-описание: Тестовое описание
        Контент: Тестовый контент поста
        """
        
        # Мокаем генерацию изображения
        mock_image_io = MagicMock()
        mock_image_io.getvalue.return_value = b"fake_image_data"
        mock_image_gen.return_value = mock_image_io

        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'test_key'}):
            generator = ContentGenerator()
            result = generator.generate_post("Тестовая тема")
            
            assert result["topic"] == "Тестовая тема"
            assert result["title"] == "Тестовый заголовок"
            assert result["meta_description"] == "Тестовое описание"
            assert "Тестовый контент поста" in result["post_content"]
            assert "image" in result

    @patch('app.generators.ContentGenerator.generate_with_deepseek')
    def test_generate_post_text_generation_failure(self, mock_text_gen):
        """Тест обработки ошибки генерации текста"""
        mock_text_gen.return_value = None

        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'test_key'}):
            generator = ContentGenerator()
            result = generator.generate_post("Тестовая тема")
            
            assert result["topic"] == "Тестовая тема"
            assert result["title"] == "Ошибка генерации"
            assert "Не удалось получить данные от DeepSeek API" in result["post_content"]

    @patch('app.generators.ContentGenerator.generate_with_deepseek')
    def test_generate_post_exception_handling(self, mock_text_gen):
        """Тест обработки исключений при генерации"""
        mock_text_gen.side_effect = Exception("Test error")

        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'test_key'}):
            generator = ContentGenerator()
            result = generator.generate_post("Тестовая тема")
            
            assert result["topic"] == "Тестовая тема"
            assert result["title"] == "Ошибка генерации"
            assert "Test error" in result["post_content"]
