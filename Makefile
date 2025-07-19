PHONY: run source-venv docker-run docker-build docker-push docker-login docker-logout docker-all dev lint lint-fix

run:
	@echo "Running the application..."
	@if [ ! -d "venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv venv; \
	fi
	@echo "Activating virtual environment and running application..."
	@. venv/bin/activate && \
		pip install -qr requirements.txt && \
		uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload --log-level info
run-prod:
	@echo "Running the application in production mode..."
	@if [ ! -d "venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv venv; \
	fi
	@echo "Activating virtual environment and running application..."
	@. venv/bin/activate && \
		pip install -qr requirements.txt && \
		uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4 --log-level warning --no-access-log
clean:
	@echo "Cleaning up..."
	@rm -rf venv
	@find src -type f -name "*.pyc" -delete
	@find src -type d -name "__pycache__" -exec rm -rf {} +
	@echo "Cleanup complete."
dev:
	@echo "Setting up development environment..."
	@if [ ! -d "venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv venv; \
	fi
	@. venv/bin/activate && \
		echo "Installing dependencies..." && \
		pip install -q --upgrade pip && \
		pip install -qr requirements.txt && \
		echo "Development environment is ready, run 'make run' to start the application."
docker-run:
	@echo "Running Docker container..."
	@docker compose up

docker-build:
	@echo "Building Docker image..."
	@docker build -t creditro.azurecr.io/fastapi:latest .

docker-push:
	@echo "Pushing Docker image to Azure Container Registry..."
	@docker push creditro.azurecr.io/fastapi:latest

docker-login:
	@echo "Logging in to Azure Container Registry..."
	@az acr login --name creditro

docker-logout:
	@echo "Logging out from Azure Container Registry..."
	@az acr logout --name creditro
docker-all:
	@echo "Building and running Docker container..."
	@$(MAKE) docker-build
	@$(MAKE) docker-login
	@$(MAKE) docker-push
db:
	@echo "Setting up database..."
	@docker compose up -d

lint:
	@echo "Running Ruff linter..."
	@if [ ! -d "venv" ]; then \
		echo "Virtual environment not found. Please run 'make dev' first."; \
		exit 1; \
	fi
	@. venv/bin/activate && \
		ruff check ./src

lint-fix:
	@echo "Running Ruff linter with auto-fix..."
	@if [ ! -d "venv" ]; then \
		echo "Virtual environment not found. Please run 'make dev' first."; \
		exit 1; \
	fi
	@. venv/bin/activate && \
		ruff check --fix ./src

test:
	@echo "Running Ruff linter with auto-fix..."
	@if [ ! -d "venv" ]; then \
		echo "Virtual environment not found. Please run 'make dev' first."; \
		exit 1; \
	fi
	@. venv/bin/activate && \
		PYTHONPATH=src pytest tests --maxfail=1 --disable-warnings -v