# TruthGit API Server Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY src/ src/

# Install TruthGit with local dependencies
RUN pip install --no-cache-dir -e ".[local]"

# Create .truth directory for repository
RUN mkdir -p /app/.truth

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Run the API server
CMD ["uvicorn", "truthgit.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
