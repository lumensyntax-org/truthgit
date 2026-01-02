# TruthGit API Server Dockerfile
FROM python:3.12-slim

# Force rebuild - v2
ARG CACHEBUST=2

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY src/ src/

# Force cache invalidation for pip install - v3
ARG PIP_CACHEBUST=3

# Install TruthGit with cloud dependencies (Vertex AI, Anthropic, OpenAI)
RUN echo "Cache bust: ${PIP_CACHEBUST}" && pip install --no-cache-dir -e ".[cloud]" google-cloud-aiplatform

# Create .truth directory for repository
RUN mkdir -p /app/.truth

# Expose port (Railway uses $PORT)
EXPOSE 8000

# Run the API server - Railway provides $PORT
CMD ["sh", "-c", "uvicorn truthgit.api.server:app --host 0.0.0.0 --port ${PORT:-8000}"]
