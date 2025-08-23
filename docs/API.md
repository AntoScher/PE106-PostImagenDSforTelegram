# API Documentation

## Обзор

Blog Content Generator API - это RESTful API для автоматической генерации блог-постов с изображениями с использованием AI технологий.

**Base URL:** `https://your-domain.com`  
**Version:** 3.0.0  
**Authentication:** Bearer Token (JWT)

## Аутентификация

API использует JWT токены для аутентификации. Для получения токена используйте эндпоинт `/auth/login`.

### Получение токена

```http
POST /auth/login
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Использование токена

Добавьте заголовок `Authorization` к вашим запросам:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Эндпоинты

### Аутентификация

#### POST /auth/login
Вход в систему.

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "string",
  "token_type": "bearer"
}
```

#### POST /auth/register
Регистрация нового пользователя.

**Request Body:**
```json
{
  "username": "string (3-50 chars)",
  "email": "string (valid email)",
  "password": "string (min 8 chars)",
  "full_name": "string (1-100 chars)"
}
```

**Response:** `200 OK`
```json
{
  "message": "User registered successfully"
}
```

#### POST /auth/change-password
Смена пароля (требует аутентификации).

**Request Body:**
```json
{
  "old_password": "string",
  "new_password": "string (min 8 chars)"
}
```

**Response:** `200 OK`
```json
{
  "message": "Password changed successfully"
}
```

#### GET /auth/me
Получение информации о текущем пользователе (требует аутентификации).

**Response:** `200 OK`
```json
{
  "username": "string",
  "email": "string",
  "full_name": "string",
  "disabled": false
}
```

### Генерация контента

#### POST /generate
Генерация поста и изображения по теме (требует аутентификации).

**Request Body:**
```json
{
  "topic": "string (3-100 chars)",
  "style": "string (optional, max 50 chars)",
  "language": "string (optional, default: 'ru')"
}
```

**Response:** `200 OK`
```json
{
  "topic": "string",
  "title": "string",
  "meta_description": "string",
  "post_content": "string",
  "image": "string (base64 encoded)"
}
```

### Утилиты

#### GET /
Проверка работоспособности API.

**Response:** `200 OK`
```json
{
  "status": "active",
  "message": "Blog Generator API работает"
}
```

#### GET /topics
Получение списка предопределенных тем.

**Response:** `200 OK`
```json
{
  "topics": [
    "Преимущества медитации",
    "Здоровое питание для занятых людей",
    "Советы по управлению временем",
    "Как начать свой бизнес",
    "Путешествия по бюджету"
  ]
}
```

#### GET /image/{topic}
Получение изображения для темы.

**Response:** `200 OK`
```
Binary image data (JPEG)
```

### Мониторинг

#### GET /metrics
Получение метрик API.

**Response:** `200 OK`
```json
{
  "uptime_seconds": 3600,
  "total_requests": 150,
  "successful_requests": 145,
  "failed_requests": 5,
  "success_rate": 96.67,
  "average_response_time": 0.245,
  "requests_per_minute": 2.5,
  "unique_clients": 12,
  "top_endpoints": {
    "POST /generate": 45,
    "GET /topics": 30
  },
  "error_distribution": {
    "500": 3,
    "400": 2
  }
}
```

#### GET /health
Проверка здоровья системы.

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "timestamp": 1640995200.0,
  "checks": {
    "database": {
      "status": "healthy",
      "timestamp": 1640995200.0,
      "details": true
    },
    "external_apis": {
      "status": "healthy",
      "timestamp": 1640995200.0,
      "details": true
    },
    "disk_space": {
      "status": "healthy",
      "timestamp": 1640995200.0,
      "details": true
    }
  }
}
```

#### GET /cache/status
Статус кэша.

**Response:** `200 OK`
```json
{
  "size": 15,
  "default_ttl": 3600
}
```

#### POST /cache/clear
Очистка кэша.

**Response:** `200 OK`
```json
{
  "message": "Cache cleared successfully"
}
```

### Администрирование

#### GET /admin/users
Получение списка пользователей (только для администраторов).

**Response:** `200 OK`
```json
{
  "users": [
    {
      "username": "admin",
      "email": "admin@example.com",
      "full_name": "Administrator",
      "disabled": false
    },
    {
      "username": "user",
      "email": "user@example.com",
      "full_name": "Regular User",
      "disabled": false
    }
  ]
}
```

#### POST /admin/users/{username}/disable
Отключение пользователя (только для администраторов).

**Response:** `200 OK`
```json
{
  "message": "User username disabled successfully"
}
```

#### POST /admin/users/{username}/enable
Включение пользователя (только для администраторов).

**Response:** `200 OK`
```json
{
  "message": "User username enabled successfully"
}
```

## Коды ошибок

| Код | Описание |
|-----|----------|
| 400 | Bad Request - Неверные данные запроса |
| 401 | Unauthorized - Требуется аутентификация |
| 403 | Forbidden - Недостаточно прав |
| 404 | Not Found - Ресурс не найден |
| 429 | Too Many Requests - Превышен лимит запросов |
| 500 | Internal Server Error - Внутренняя ошибка сервера |

## Rate Limiting

API использует rate limiting для защиты от злоупотреблений:

- **60 запросов в минуту** на IP адрес
- **1000 запросов в час** на IP адрес

При превышении лимита возвращается код `429` с заголовками:
- `X-RateLimit-Minute-Remaining`
- `X-RateLimit-Hour-Remaining`
- `Retry-After`

## Примеры использования

### Python (requests)

```python
import requests

# Аутентификация
auth_response = requests.post('https://your-domain.com/auth/login', json={
    'username': 'your_username',
    'password': 'your_password'
})
token = auth_response.json()['access_token']

# Генерация поста
headers = {'Authorization': f'Bearer {token}'}
response = requests.post('https://your-domain.com/generate', json={
    'topic': 'Преимущества медитации',
    'style': 'профессиональный'
}, headers=headers)

post_data = response.json()
print(f"Заголовок: {post_data['title']}")
print(f"Контент: {post_data['post_content']}")
```

### JavaScript (fetch)

```javascript
// Аутентификация
const authResponse = await fetch('https://your-domain.com/auth/login', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        username: 'your_username',
        password: 'your_password'
    })
});

const { access_token } = await authResponse.json();

// Генерация поста
const response = await fetch('https://your-domain.com/generate', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${access_token}`
    },
    body: JSON.stringify({
        topic: 'Преимущества медитации',
        style: 'профессиональный'
    })
});

const postData = await response.json();
console.log(`Заголовок: ${postData.title}`);
console.log(`Контент: ${postData.post_content}`);
```

### cURL

```bash
# Аутентификация
TOKEN=$(curl -X POST https://your-domain.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"your_username","password":"your_password"}' \
  | jq -r '.access_token')

# Генерация поста
curl -X POST https://your-domain.com/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"topic":"Преимущества медитации","style":"профессиональный"}'
```

## Webhooks

API поддерживает webhooks для интеграции с внешними системами. Подробная документация по webhooks доступна в отдельном разделе.

## Поддержка

Для получения поддержки обращайтесь:
- Email: support@your-domain.com
- Документация: https://your-domain.com/docs
- Swagger UI: https://your-domain.com/docs
