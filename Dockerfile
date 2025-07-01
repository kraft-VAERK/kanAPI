# Build stage: install dependencies and compile any requirements
FROM python:3.13-alpine3.22 AS build

# Create venv in /opt
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install build dependencies and requirements
COPY requirements.txt /requirements.txt
RUN apk add --no-cache --virtual .build-deps gcc musl-dev linux-headers libffi-dev \
    && pip install --no-cache-dir -r /requirements.txt \
    && apk del .build-deps

# Test stage: run tests and validations
FROM build AS test
WORKDIR /app
COPY . .
# Run your tests here - uncomment and modify as needed
RUN PYTHONPATH=src pytest tests --maxfail=1 --disable-warnings -v

# Final stage: copy only what's needed for production
FROM python:3.13-alpine3.22 AS production

# Copy venv from build stage
COPY --from=build /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code only (avoid dev files)
COPY --from=test /app/src /app/src
# If you have other files needed for production, copy them explicitly
COPY --from=test /app/requirements.txt /app/

# Add curl for healthcheck
RUN apk add --no-cache curl

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 CMD [ "curl", "-f", "http://localhost:8000/health/live" ]

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application using Uvicorn
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--log-level", "warning", "--no-access-log"]