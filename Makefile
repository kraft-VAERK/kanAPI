PHONY: run source-venv docker-run docker-build docker-push docker-login docker-logout docker-all dev lint lint-fix frontend

PYTHON=venv/bin/python3
PIP=venv/bin/pip
UVICORN=venv/bin/uvicorn

run:
	@echo "Starting backend + frontend in background..."
	@if [ ! -d "venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv venv; \
	fi
	@. venv/bin/activate && pip install -qr requirements.txt
	@cd frontend && npm install --silent
	@mkdir -p logs
	@. venv/bin/activate && uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload --log-level info > logs/backend.log 2>&1 &
	@cd frontend && npm run dev > ../logs/frontend.log 2>&1 &
	@echo "  Backend:  http://localhost:8000  (tail logs/backend.log)"
	@echo "  Frontend: http://localhost:5173  (tail logs/frontend.log)"
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
	@echo "Killing processes on project ports..."
	@for port in 8000 5173 9000 9001 5432; do \
		pid=$$(lsof -ti :$$port); \
		if [ -n "$$pid" ]; then \
			echo "  Killing port $$port (PID $$pid)"; \
			kill -9 $$pid 2>/dev/null; \
		else \
			echo "  Port $$port: free"; \
		fi; \
	done
	@echo "Removing venv and cache..."
	@rm -rf venv
	@find src -type f -name "*.pyc" -delete
	@find src -type d -name "__pycache__" -exec rm -rf {} +
	@echo "Done."
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
	@docker build -t kanAPI:latest .

docker-all:
	@echo "Building and running Docker container..."
	@$(MAKE) docker-build
	@$(MAKE) docker-login
	@$(MAKE) docker-push
db:
	@echo "Setting up database..."
	@docker compose up -d

seed:
	@echo "Seeding database..."
	@if [ ! -d "venv" ]; then echo "Run 'make dev' first."; exit 1; fi
	@. venv/bin/activate && PYTHONPATH=src python -m src.api.db.seed

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

frontend:
	@echo "Building frontend..."
	@cd frontend && npm install && npm run build
	@echo "Frontend built to frontend/dist/"

test:
	@echo "Running Ruff linter with auto-fix..."
	@if [ ! -d "venv" ]; then \
		echo "Virtual environment not found. Please run 'make dev' first."; \
		exit 1; \
	fi
	@. venv/bin/activate && \
		PYTHONPATH=src pytest tests --maxfail=1 --disable-warnings -v