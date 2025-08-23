import pytest
from unittest.mock import patch, MagicMock
import os
from app.telegram_bot import TelegramBot, TelegramConfig


class TestTelegramConfig:
    def test_telegram_config_creation(self):
        """Тест создания конфигурации Telegram"""
        config = TelegramConfig(
            bot_token="test_token",
            chat_id="test_chat_id",
            enabled=True
        )
        assert config.bot_token == "test_token"
        assert config.chat_id == "test_chat_id"
        assert config.enabled is True


class TestTelegramBot:
    @patch.dict(os.environ, {
        'TELEGRAM_BOT_TOKEN': 'test_token',
        'TELEGRAM_CHAT_ID': 'test_chat_id',
        'TELEGRAM_ENABLED': 'true'
    })
    def test_init_success(self):
        """Тест успешной инициализации бота"""
        bot = TelegramBot()
        assert bot.config.bot_token == 'test_token'
        assert bot.config.chat_id == 'test_chat_id'
        assert bot.config.enabled is True

    @patch.dict(os.environ, {
        'TELEGRAM_BOT_TOKEN': '',
        'TELEGRAM_CHAT_ID': '',
        'TELEGRAM_ENABLED': 'false'
    })
    def test_init_disabled(self):
        """Тест инициализации отключенного бота"""
        bot = TelegramBot()
        assert bot.config.enabled is False

    @patch('app.telegram_bot.requests.post')
    async def test_send_notification_success(self, mock_post):
        """Тест успешной отправки уведомления"""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        with patch.dict(os.environ, {
            'TELEGRAM_BOT_TOKEN': 'test_token',
            'TELEGRAM_CHAT_ID': 'test_chat_id',
            'TELEGRAM_ENABLED': 'true'
        }):
            bot = TelegramBot()
            await bot.send_notification("Test message")
            
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[1]['json']['text'] == "Test message"
            assert call_args[1]['json']['chat_id'] == "test_chat_id"

    @patch('app.telegram_bot.requests.post')
    async def test_send_notification_disabled(self, mock_post):
        """Тест отправки уведомления при отключенном боте"""
        with patch.dict(os.environ, {
            'TELEGRAM_ENABLED': 'false'
        }):
            bot = TelegramBot()
            await bot.send_notification("Test message")
            
            mock_post.assert_not_called()

    @patch('app.telegram_bot.requests.post')
    async def test_send_notification_error(self, mock_post):
        """Тест обработки ошибки отправки уведомления"""
        mock_post.side_effect = Exception("Network error")

        with patch.dict(os.environ, {
            'TELEGRAM_BOT_TOKEN': 'test_token',
            'TELEGRAM_CHAT_ID': 'test_chat_id',
            'TELEGRAM_ENABLED': 'true'
        }):
            bot = TelegramBot()
            # Не должно вызывать исключение
            await bot.send_notification("Test message")

    @patch('app.telegram_bot.requests.post')
    async def test_send_image_success(self, mock_post):
        """Тест успешной отправки изображения"""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        with patch.dict(os.environ, {
            'TELEGRAM_BOT_TOKEN': 'test_token',
            'TELEGRAM_CHAT_ID': 'test_chat_id',
            'TELEGRAM_ENABLED': 'true'
        }):
            bot = TelegramBot()
            test_image_base64 = "dGVzdF9pbWFnZV9kYXRh"  # base64 для "test_image_data"
            await bot.send_image(test_image_base64, "Test caption")
            
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[1]['data']['caption'] == "Test caption"

    def test_send_async(self):
        """Тест асинхронной отправки сообщения"""
        with patch.dict(os.environ, {
            'TELEGRAM_ENABLED': 'true'
        }):
            bot = TelegramBot()
            background_tasks = MagicMock()
            
            bot.send_async(background_tasks, "Test message")
            
            background_tasks.add_task.assert_called_once()

    def test_send_async_disabled(self):
        """Тест асинхронной отправки при отключенном боте"""
        with patch.dict(os.environ, {
            'TELEGRAM_ENABLED': 'false'
        }):
            bot = TelegramBot()
            background_tasks = MagicMock()
            
            bot.send_async(background_tasks, "Test message")
            
            background_tasks.add_task.assert_not_called()
