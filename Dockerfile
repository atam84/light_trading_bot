# Dockerfile (FIXED - Remove problematic entrypoint)
# Multi-stage build for optimized production image

# Build stage
FROM python:3.10-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1


RUN apt-get clean && rm -rf /var/lib/apt/lists/* && \
    apt-get update --allow-insecure-repositories || true

# Fix potential GPG errors on Debian Bookworm
RUN apt-get -o Acquire::AllowInsecureRepositories=true update && apt-get -o Acquire::AllowInsecureRepositories=true install -y --no-install-recommends \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*


# Install system dependencies for building
RUN apt-get -o Acquire::AllowInsecureRepositories=true update && apt-get -o Acquire::AllowInsecureRepositories=true install -y \
    gcc \
    g++ \
    make \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Install additional dependencies for trading interface
RUN pip install --no-cache-dir \
    python-jose[cryptography]==3.3.0 \
    passlib[bcrypt]==1.7.4 \
    python-multipart==0.0.6 \
    aiohttp==3.9.1 \
    jinja2==3.1.2 \
    pytest-asyncio==0.21.1 \
    httpx==0.25.2

# Production stage
FROM python:3.10-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies
RUN apt-get clean && rm -rf /var/lib/apt/lists/* && \
    apt-get update --allow-insecure-repositories || true
RUN apt-get -o Acquire::AllowInsecureRepositories=true update && apt-get -o Acquire::AllowInsecureRepositories=true install -y \
    curl \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create application directory
WORKDIR /app

# Create non-root user for security
RUN groupadd -r trader && useradd -r -g trader -u 1000 trader

# Create necessary directories
RUN mkdir -p /app/{src,logs,data,config} && \
    chown -R trader:trader /app

# Copy application code
COPY --chown=trader:trader src/ ./src/
COPY --chown=trader:trader config/ ./config/
COPY --chown=trader:trader config.yaml .env.example ./
COPY --chown=trader:trader startup.py ./startup.py

# REMOVED: Problematic entrypoint.sh copy and setup
# COPY --chown=trader:trader docker/entrypoint.sh /entrypoint.sh
# RUN chmod +x /entrypoint.sh

# Create volume mount points
VOLUME ["/app/logs", "/app/data", "/app/config"]

# Expose ports
EXPOSE 5000 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Switch to non-root user
USER trader

# REMOVED: Problematic entrypoint
# ENTRYPOINT ["/entrypoint.sh"]

# FIXED: Use startup.py directly (no dual process)
CMD ["python", "startup.py", "--host", "0.0.0.0", "--port", "5000"]

