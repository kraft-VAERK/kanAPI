PHONY: run run-prod dev lint lint-fix frontend test seed seed-fga db clean docker-run docker-build docker-push docker-login docker-logout docker-all

run:
	@echo "Starting backend + frontend in background..."
	@uv sync
	@cd frontend && npm install --silent
	@mkdir -p logs
	@uv run uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload --log-level info > logs/backend.log 2>&1 &
	@cd frontend && npm run dev > ../logs/frontend.log 2>&1 &
	@echo "  Backend:  http://localhost:8000  (tail logs/backend.log)"
	@echo "  Frontend: http://localhost:5173  (tail logs/frontend.log)"

run-prod:
	@echo "Running the application in production mode..."
	@uv sync
	@uv run uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4 --log-level warning --no-access-log

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
	@echo "Stopping containers and removing volumes..."
# 	@docker compose down -v --remove-orphans 2>/dev/null || true
	@echo "Removing venv and cache..."
	@rm -rf .venv
	@find src -type f -name "*.pyc" -delete
	@find src -type d -name "__pycache__" -exec rm -rf {} +
	@rm -rf logs
	@echo "Done."

dev:
	@echo "Setting up development environment..."
	@uv sync
	@echo "Development environment is ready, run 'make run' to start the application."

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
	@echo "Setting up database services..."
	@docker compose up -d
	@mkdir -p logs
	@for svc in postgres minio openfga-db openfga; do \
		docker logs -f $$svc > logs/$$svc.log 2>&1 & \
	done
	@echo "  Logs: logs/postgres.log  logs/minio.log  logs/openfga-db.log  logs/openfga.log"

seed:
	@echo "Seeding database..."
	@uv run python3 -m src.api.db.seed

seed-fga:
	@echo "Creating OpenFGA store and writing authorization model..."
	@uv run python3 src/api/db/seed_fga.py

lint:
	@echo "Running Ruff linter..."
	@uv run ruff check ./src

lint-fix:
	@echo "Running Ruff linter with auto-fix..."
	@uv run ruff check --fix ./src

frontend:
	@echo "Building frontend..."
	@cd frontend && npm install && npm run build
	@echo "Frontend built to frontend/dist/"

test:
	@echo "Running tests..."
	@uv run pytest tests --maxfail=1 --disable-warnings -v

logs:
	@echo "Opening Grafana dashboard..."
	@open http://localhost:3001/d/kanapi-main/kanapi-observability 2>/dev/null || echo "  Open http://localhost:3001 in your browser"
