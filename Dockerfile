FROM python:3.11-slim

# Установка рабочей директории
WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование приложения
COPY . .

# Порт по умолчанию
EXPOSE 8000

# Команда запуска (exec-форма)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]