## kanAPI

Only the OG's will know.

Frameworks:

- fastAPI
- Redis
- Database to been chosen.

# Makefile Commands

```bash
make dev            # Set up and install dependencies for development
make run            # Run the application
make clean          # Remove virtual environment and Python cache files
make docker-run     # Start the app in a Docker container
make docker-build   # Build the Docker image
make docker-push    # Push the Docker image to the registry
make docker-login   # Log in to Azure Container Registry
make docker-logout  # Log out from Azure Container Registry
make docker-all     # Build, log in, and push Docker image
make lint           # Run Ruff linter on the code
make lint-fix       # Run Ruff linter and auto-fix issues
make test           # Run all tests with pytest
```
