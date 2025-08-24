import pytest
from unittest.mock import patch, MagicMock, mock_open
from PIL import Image
from io import BytesIO
import os
from app.image_generator import ImageGenerator


class TestImageGenerator:
    @patch.dict(os.environ, {'STABILITY_API_KEY': 'test_key'})
    def test_init_success(self):
        """Тест успешной инициализации генератора изображений"""
        generator = ImageGenerator()
        assert generator.api_key == 'test_key'
        assert generator.api_url == "https://api.stability.ai/v2beta/stable-image/generate/sd3"

    def test_init_no_api_key(self):
        """Тест инициализации без API ключа"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="STABILITY_API_KEY environment variable not set"):
                ImageGenerator()

    @patch('app.image_generator.Path')
    def test_get_font_path_windows(self, mock_path):
        """Тест поиска шрифта в Windows"""
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance

        with patch.dict(os.environ, {'STABILITY_API_KEY': 'test_key'}):
            generator = ImageGenerator()
            assert generator.font_path == "C:/Windows/Fonts/arial.ttf"

    @patch('app.image_generator.Path')
    def test_get_font_path_linux(self, mock_path):
        """Тест поиска шрифта в Linux"""
        # Windows шрифт не найден
        mock_windows_path = MagicMock()
        mock_windows_path.exists.return_value = False
        
        # Linux шрифт найден
        mock_linux_path = MagicMock()
        mock_linux_path.exists.return_value = True
        
        mock_path.side_effect = [mock_windows_path, mock_linux_path]

        with patch.dict(os.environ, {'STABILITY_API_KEY': 'test_key'}):
            generator = ImageGenerator()
            assert generator.font_path == "/usr/share/fonts/truetype/freefont/FreeMono.ttf"

    @patch('app.image_generator.requests.post')
    def test_generate_image_success(self, mock_post):
        """Тест успешной генерации изображения"""
        # Мокаем успешный ответ
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"fake_image_data"
        mock_post.return_value = mock_response

        with patch.dict(os.environ, {'STABILITY_API_KEY': 'test_key'}):
            generator = ImageGenerator()
            result = generator.generate_image("Test prompt")
            
            assert isinstance(result, BytesIO)
            assert result.getvalue() == b"fake_image_data"

    @patch('app.image_generator.requests.post')
    def test_generate_image_error(self, mock_post):
        """Тест обработки ошибки генерации изображения"""
        # Мокаем ошибку
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_post.return_value = mock_response

        with patch.dict(os.environ, {'STABILITY_API_KEY': 'test_key'}):
            generator = ImageGenerator()
            with pytest.raises(Exception, match="Image generation error"):
                generator.generate_image("Test prompt")

    @patch('app.image_generator.Image.open')
    @patch('app.image_generator.ImageDraw.Draw')
    @patch('app.image_generator.ImageFont.truetype')
    def test_add_text_to_image_success(self, mock_font, mock_draw, mock_image_open):
        """Тест успешного добавления текста к изображению"""
        # Создаем мок изображения
        mock_img = MagicMock()
        mock_img.size = (800, 600)
        mock_img.convert.return_value = mock_img
        mock_image_open.return_value = mock_img
        
        # Мокаем шрифт
        mock_font_instance = MagicMock()
        mock_font.return_value = mock_font_instance
        
        # Мокаем рисование
        mock_draw_instance = MagicMock()
        mock_draw_instance.textlength.return_value = 100
        mock_draw.return_value = mock_draw_instance

        with patch.dict(os.environ, {'STABILITY_API_KEY': 'test_key'}):
            generator = ImageGenerator()
            generator.font_path = "test_font.ttf"
            
            # Создаем тестовый поток изображения
            test_image_io = BytesIO(b"fake_image_data")
            result = generator.add_text_to_image(test_image_io, "Test text")
            
            assert isinstance(result, BytesIO)

    @patch('app.image_generator.Image.open')
    @patch('app.image_generator.ImageDraw.Draw')
    def test_add_text_to_image_font_error(self, mock_draw, mock_image_open):
        """Тест обработки ошибки шрифта"""
        # Создаем мок изображения
        mock_img = MagicMock()
        mock_img.size = (800, 600)
        mock_img.convert.return_value = mock_img

        # Создаем мок для ImageDraw
        mock_draw_instance = MagicMock()
        mock_draw_instance.textlength.return_value = 100  # Возвращаем число вместо MagicMock
        mock_draw.return_value = mock_draw_instance

        mock_image_open.return_value = mock_img

        with patch.dict(os.environ, {'STABILITY_API_KEY': 'test_key'}):
            generator = ImageGenerator()
            generator.font_path = "nonexistent_font.ttf"
            
            # Создаем тестовый поток изображения
            test_image_io = BytesIO(b"fake_image_data")
            result = generator.add_text_to_image(test_image_io, "Test text")
            
            assert isinstance(result, BytesIO)

    @patch('app.image_generator.ImageGenerator.generate_image')
    @patch('app.image_generator.ImageGenerator.add_text_to_image')
    def test_generate_image_with_text(self, mock_add_text, mock_generate):
        """Тест полной генерации изображения с текстом"""
        # Мокаем генерацию изображения
        mock_image_stream = BytesIO(b"fake_image_data")
        mock_generate.return_value = mock_image_stream
        
        # Мокаем добавление текста
        mock_result = BytesIO(b"result_image_data")
        mock_add_text.return_value = mock_result

        with patch.dict(os.environ, {'STABILITY_API_KEY': 'test_key'}):
            generator = ImageGenerator()
            result = generator.generate_image_with_text("Test prompt", "Test text")
            
            assert result == mock_result
            mock_generate.assert_called_once_with("Test prompt")
            mock_add_text.assert_called_once_with(mock_image_stream, "Test text")
