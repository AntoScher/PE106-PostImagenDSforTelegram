import re
from typing import Optional, List
from pydantic import BaseModel, Field, validator
import logging

logger = logging.getLogger(__name__)


class TopicValidator:
    """Валидатор для тем постов"""
    
    # Запрещенные слова и паттерны
    FORBIDDEN_WORDS = [
        'спам', 'реклама', 'взлом', 'хак', 'взломать', 'обмануть',
        'spam', 'hack', 'crack', 'cheat', 'scam', 'fraud'
    ]
    
    FORBIDDEN_PATTERNS = [
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        r'[<>{}[\]]',
        r'\b\d{4,}\b',  # Слишком длинные числа
    ]
    
    @classmethod
    def validate_topic(cls, topic: str) -> tuple[bool, Optional[str]]:
        """
        Валидация темы поста
        
        Returns:
            tuple: (is_valid, error_message)
        """
        if not topic or not topic.strip():
            return False, "Тема не может быть пустой"
        
        topic = topic.strip()
        
        # Проверка длины
        if len(topic) < 3:
            return False, "Тема должна содержать минимум 3 символа"
        
        if len(topic) > 100:
            return False, "Тема не должна превышать 100 символов"
        
        # Проверка на запрещенные слова
        topic_lower = topic.lower()
        for forbidden_word in cls.FORBIDDEN_WORDS:
            if forbidden_word in topic_lower:
                return False, f"Тема содержит запрещенное слово: {forbidden_word}"
        
        # Проверка на запрещенные паттерны
        for pattern in cls.FORBIDDEN_PATTERNS:
            if re.search(pattern, topic):
                return False, "Тема содержит недопустимые символы или паттерны"
        
        # Проверка на повторяющиеся символы
        if re.search(r'(.)\1{4,}', topic):
            return False, "Тема содержит слишком много повторяющихся символов"
        
        return True, None


class ImagePromptValidator:
    """Валидатор для промптов изображений"""
    
    FORBIDDEN_IMAGE_WORDS = [
        'nude', 'naked', 'porn', 'sex', 'violence', 'blood', 'gore',
        'обнаженный', 'насилие', 'кровь', 'порно', 'секс'
    ]
    
    @classmethod
    def validate_image_prompt(cls, prompt: str) -> tuple[bool, Optional[str]]:
        """
        Валидация промпта для изображения
        
        Returns:
            tuple: (is_valid, error_message)
        """
        if not prompt or not prompt.strip():
            return False, "Промпт не может быть пустым"
        
        prompt = prompt.strip()
        
        # Проверка длины
        if len(prompt) < 10:
            return False, "Промпт должен содержать минимум 10 символов"
        
        if len(prompt) > 500:
            return False, "Промпт не должен превышать 500 символов"
        
        # Проверка на запрещенные слова для изображений
        prompt_lower = prompt.lower()
        for forbidden_word in cls.FORBIDDEN_IMAGE_WORDS:
            if forbidden_word in prompt_lower:
                return False, f"Промпт содержит запрещенное слово: {forbidden_word}"
        
        return True, None


class EnhancedGenerateRequest(BaseModel):
    """Улучшенная модель запроса генерации"""
    
    topic: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Тема для генерации поста"
    )
    
    style: Optional[str] = Field(
        None,
        max_length=50,
        description="Стиль написания (например: 'профессиональный', 'разговорный')"
    )
    
    language: Optional[str] = Field(
        "ru",
        regex="^[a-z]{2}$",
        description="Язык контента (ru, en, etc.)"
    )
    
    @validator('topic')
    def validate_topic(cls, v):
        is_valid, error_msg = TopicValidator.validate_topic(v)
        if not is_valid:
            raise ValueError(error_msg)
        return v.strip()
    
    @validator('style')
    def validate_style(cls, v):
        if v is not None:
            v = v.strip()
            if len(v) > 50:
                raise ValueError("Стиль не должен превышать 50 символов")
        return v


class ImageRequest(BaseModel):
    """Модель запроса генерации изображения"""
    
    prompt: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Промпт для генерации изображения"
    )
    
    size: Optional[str] = Field(
        "1024x1024",
        regex="^(1024x1024|1024x1792|1792x1024)$",
        description="Размер изображения"
    )
    
    @validator('prompt')
    def validate_prompt(cls, v):
        is_valid, error_msg = ImagePromptValidator.validate_image_prompt(v)
        if not is_valid:
            raise ValueError(error_msg)
        return v.strip()


class WebhookValidator:
    """Валидатор для вебхуков"""
    
    ALLOWED_EVENTS = [
        'new_generation',
        'health_check', 
        'error',
        'image_generated',
        'post_published'
    ]
    
    @classmethod
    def validate_webhook_data(cls, event: str, data: dict) -> tuple[bool, Optional[str]]:
        """
        Валидация данных вебхука
        
        Returns:
            tuple: (is_valid, error_message)
        """
        if event not in cls.ALLOWED_EVENTS:
            return False, f"Неизвестное событие: {event}"
        
        if not isinstance(data, dict):
            return False, "Данные должны быть объектом"
        
        # Специфичная валидация для разных событий
        if event == 'new_generation':
            required_fields = ['topic', 'title']
            for field in required_fields:
                if field not in data:
                    return False, f"Отсутствует обязательное поле: {field}"
        
        elif event == 'error':
            if 'message' not in data:
                return False, "Отсутствует поле 'message' для события error"
        
        return True, None


def sanitize_text(text: str) -> str:
    """Очистка текста от потенциально опасных символов"""
    if not text:
        return ""
    
    # Удаляем HTML теги
    text = re.sub(r'<[^>]+>', '', text)
    
    # Удаляем потенциально опасные символы
    text = re.sub(r'[<>{}[\]]', '', text)
    
    # Нормализуем пробелы
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def validate_file_size(file_size: int, max_size_mb: int = 10) -> tuple[bool, Optional[str]]:
    """Валидация размера файла"""
    max_size_bytes = max_size_mb * 1024 * 1024
    
    if file_size > max_size_bytes:
        return False, f"Размер файла превышает {max_size_mb}MB"
    
    return True, None


def validate_file_type(filename: str, allowed_extensions: List[str] = None) -> tuple[bool, Optional[str]]:
    """Валидация типа файла"""
    if allowed_extensions is None:
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif']
    
    file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
    
    if f'.{file_ext}' not in allowed_extensions:
        return False, f"Неподдерживаемый тип файла. Разрешены: {', '.join(allowed_extensions)}"
    
    return True, None
