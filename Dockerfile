# Use official Python runtime as the base image
FROM python:3.13-alpine3.22

# Set working directory in the container
WORKDIR /app

# Setup python environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements file
COPY requirements.txt .

# Install dependencies - combining build deps installation, pip install, and cleanup in one layer
RUN apk add --no-cache --virtual .build-deps gcc musl-dev linux-headers libffi-dev \
    && pip install --no-cache-dir -r requirements.txt \
    && apk del .build-deps

# Copy the rest of the application
COPY . .

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 CMD [ "curl", "-f", "http://localhost:8000/health/live" ]

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application using Uvicorn
CMD ["python", "src/api/main.py", "prod"]