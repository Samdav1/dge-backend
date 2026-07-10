# Stage 1: Build dependencies
FROM --platform=linux/amd64 python:3.12-slim AS builder

WORKDIR /app

# Copy and install python dependencies (pulls pre-compiled binary wheels)
COPY requirements.txt .
RUN pip install --default-timeout=1000 --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Runtime image
FROM --platform=linux/amd64 python:3.12-slim

WORKDIR /app

# Install runtime system packages (like curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed dependencies from builder
COPY --from=builder /install /usr/local

# Copy application source code
COPY . .

# Make entrypoint script executable
RUN chmod +x /app/entrypoint.sh

# Expose ports for FastAPI (HTTP and WebSockets both go through port 8000)
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run entrypoint script (which runs migrations and starts uvicorn)
ENTRYPOINT ["/app/entrypoint.sh"]
