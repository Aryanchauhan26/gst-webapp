# =============================================================================
# GST Intelligence Platform - Production Docker Image
# Multi-stage build for optimized production deployment
# =============================================================================

# =============================================================================
# Stage 1: Build Dependencies
# =============================================================================
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILD_DATE
ARG VERSION=2.0.0
ARG ENVIRONMENT=production

# Labels for metadata
LABEL maintainer="GST Intelligence Platform" \
      version="${VERSION}" \
      description="GST compliance analytics platform with AI insights" \
      build-date="${BUILD_DATE}"

# Set environment variables for build
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies required for Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    libjpeg-dev \
    libpng-dev \
    zlib1g-dev \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf2.0-dev \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn

# =============================================================================
# Stage 2: Production Runtime
# =============================================================================
FROM python:3.11-slim as production

# Set runtime environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=production \
    PORT=8000 \
    WORKERS=1 \
    TIMEOUT=30 \
    KEEP_ALIVE=2 \
    MAX_REQUESTS=1000 \
    MAX_REQUESTS_JITTER=50

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 \
    libxslt1.1 \
    libjpeg62-turbo \
    libpng16-16 \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi8 \
    shared-mime-info \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/static/uploads /app/logs /app/data && \
    chown -R appuser:appuser /app && \
    chmod +x /app/start.py

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE ${PORT}

# Default command
CMD ["python", "-m", "gunicorn", "main:app", "--bind", "0.0.0.0:8000", "--workers", "1", "--worker-class", "uvicorn.workers.UvicornWorker", "--timeout", "30", "--keep-alive", "2", "--max-requests", "1000", "--max-requests-jitter", "50", "--preload", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info"]

# =============================================================================
# Stage 3: Development Environment (Optional)
# =============================================================================
FROM production as development

# Switch back to root for development tools installation
USER root

# Install development dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    vim \
    tree \
    htop \
    sqlite3 \
    postgresql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Install development Python packages
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    pytest-cov \
    black \
    isort \
    flake8 \
    mypy \
    pre-commit \
    ipython \
    jupyter

# Set development environment
ENV ENVIRONMENT=development \
    DEBUG=True \
    LOG_LEVEL=DEBUG

# Switch back to appuser
USER appuser

# Development command with hot reload
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-level", "debug"]

# =============================================================================
# Stage 4: Testing Environment
# =============================================================================
FROM development as testing

# Switch to root for test setup
USER root

# Install additional testing tools
RUN pip install --no-cache-dir \
    pytest-xdist \
    pytest-mock \
    pytest-benchmark \
    coverage \
    tox

# Set testing environment
ENV ENVIRONMENT=testing \
    POSTGRES_DSN=postgresql://test:test@localhost:5432/test_db

# Switch back to appuser
USER appuser

# Testing command
CMD ["python", "-m", "pytest", "-v", "--cov=.", "--cov-report=html", "--cov-report=term"]

# =============================================================================
# Build Instructions:
# =============================================================================
# Production build:
# docker build --target production -t gst-intelligence:latest .
#
# Development build:
# docker build --target development -t gst-intelligence:dev .
#
# Testing build:
# docker build --target testing -t gst-intelligence:test .
#
# Build with custom args:
# docker build --build-arg VERSION=2.1.0 --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') -t gst-intelligence:v2.1.0 .
# =============================================================================