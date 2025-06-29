PHONY: run source-venv docker-run docker-build docker-push docker-login docker-logout docker-all dev

run:
	@echo "Running the application..."
	@if [ ! -d "venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv venv; \
	fi
	@echo "Activating virtual environment and running application..."
	@. venv/bin/activate && \
		pip install -qr requirements.txt && \
		python3 main.py dev

clean:
	@echo "Cleaning up..."
	@rm -rf venv
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@echo "Cleanup complete."


source-venv:
	@echo "Sourcing environment variables..."
	@if [ -f "venv/bin/activate" ]; then \
		echo "Use: 'source venv/bin/activate' to activate the virtual environment in your current shell"; \
	else \
		echo "Virtual environment not found. Please run 'make run' first."; \
	fi
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

dev:
	@echo "Setting up development environment..."
	@if [ ! -d "venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv venv; \
	fi
	@echo "Activating virtual environment and installing dependencies..."
	@. venv/bin/activate && \
		pip install -r requirements.txt && \
		echo "Development environment ready. Run 'source venv/bin/activate' to activate in your current shell."