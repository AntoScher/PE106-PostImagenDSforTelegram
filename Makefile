.PHONY: help install test lint format clean run docker-build docker-run production

help: ## Показать справку
	@echo "Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Установить зависимости
	pip install -r requirements.txt
	pip install -e .

test: ## Запустить тесты
	pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing

test-watch: ## Запустить тесты в режиме наблюдения
	pytest tests/ -v --cov=app -f

lint: ## Проверить код линтерами
	flake8 app/ tests/
	black --check app/ tests/
	isort --check-only app/ tests/
	bandit -r app/

format: ## Отформатировать код
	black app/ tests/
	isort app/ tests/

clean: ## Очистить временные файлы
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .coverage htmlcov/ .pytest_cache/ build/ dist/

run: ## Запустить приложение локально
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-prod: ## Запустить приложение в продакшн режиме
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

docker-build: ## Собрать Docker образ
	docker build -t blog-generator .

docker-run: ## Запустить Docker контейнер
	docker run -p 8000:8000 --env-file .env blog-generator

docker-compose-up: ## Запустить с Docker Compose
	docker-compose up --build

docker-compose-down: ## Остановить Docker Compose
	docker-compose down

security-check: ## Проверить безопасность
	bandit -r app/ -f json -o bandit-report.json
	safety check --json --output safety-report.json

ci: ## Запустить все проверки CI
	make lint
	make test
	make security-check

dev-setup: ## Настройка окружения разработки
	pip install -r requirements.txt
	pip install black isort flake8 bandit safety pytest-cov
	cp env.example .env
	@echo "Не забудьте настроить переменные окружения в .env файле!"

deploy-staging: ## Деплой на staging
	@echo "Деплой на staging окружение..."

deploy-production: ## Деплой на production
	@echo "Деплой на production окружение..."

monitoring: ## Запустить мониторинг
	@echo "Метрики API: http://localhost:8000/metrics"
	@echo "Здоровье системы: http://localhost:8000/health"
	@echo "Статус кэша: http://localhost:8000/cache/status"

docs: ## Открыть документацию API
	@echo "Swagger UI: http://localhost:8000/docs"
	@echo "ReDoc: http://localhost:8000/redoc"

production: ## Запустить в production режиме
	@echo "Запуск в production режиме..."
	@chmod +x scripts/start_production.sh
	@./scripts/start_production.sh start

production-stop: ## Остановить production приложение
	@echo "Остановка production приложения..."
	@./scripts/start_production.sh stop

production-restart: ## Перезапустить production приложение
	@echo "Перезапуск production приложения..."
	@./scripts/start_production.sh restart

production-status: ## Статус production приложения
	@./scripts/start_production.sh status

production-logs: ## Показать логи production
	@./scripts/start_production.sh logs

production-health: ## Проверить здоровье production
	@./scripts/start_production.sh health

production-metrics: ## Показать метрики production
	@./scripts/start_production.sh metrics

auth-test: ## Тестирование аутентификации
	@echo "Запуск тестов аутентификации..."
	pytest tests/test_auth.py -v

cache-test: ## Тестирование кэширования
	@echo "Запуск тестов кэширования..."
	pytest tests/test_cache.py -v

security-test: ## Тестирование безопасности
	@echo "Запуск тестов безопасности..."
	pytest tests/test_security.py -v

full-test: ## Полный набор тестов
	@echo "Запуск всех тестов..."
	pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing

backup: ## Создать резервную копию
	@echo "Создание резервной копии..."
	@mkdir -p backups
	@tar -czf backups/backup-$(shell date +%Y%m%d-%H%M%S).tar.gz \
		--exclude=__pycache__ \
		--exclude=*.pyc \
		--exclude=.git \
		--exclude=logs \
		--exclude=backups \
		.

deploy: ## Деплой на production
	@echo "Деплой на production..."
	@make production-stop || true
	@make backup
	@git pull origin main
	@make install
	@make production
