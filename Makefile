PHONY: run run-prod dev lint lint-fix frontend test seed seed-fga db clean docker-run docker-build docker-push docker-login docker-logout docker-all


run:
	@echo "Starting backend + frontend in background..."
	@uv sync
	@cd frontend && npm install --silent
	@mkdir -p logs
	@nohup uv run uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload --log-level info > logs/backend.log 2>&1 & echo $$! > .backend.pid
	@nohup sh -c 'cd frontend && npm run dev' > logs/frontend.log 2>&1 & echo $$! > .frontend.pid
	@echo "  Backend:  http://localhost:8000"
	@echo "  Frontend: http://localhost:5173"
	@echo "  Logs:     logs/backend.log  logs/frontend.log"

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
	@docker compose down -v --remove-orphans 2>/dev/null || true
	@for pid_file in .backend.pid .frontend.pid; do \
		if [ -f $$pid_file ]; then \
			kill $$(cat $$pid_file) 2>/dev/null && echo "  Killed PID $$(cat $$pid_file)"; \
			rm -f $$pid_file; \
		fi; \
	done
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
	@uv run python3 -m src.api.db.seed_fga

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

