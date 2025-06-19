#!/bin/bash

# Trading Bot Docker Entrypoint Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] SUCCESS:${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# Function to wait for service to be ready
wait_for_service() {
    local service_name=$1
    local service_url=$2
    local max_attempts=30
    local attempt=1

    log "Waiting for $service_name to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$service_url" >/dev/null 2>&1; then
            success "$service_name is ready!"
            return 0
        fi
        
        log "Attempt $attempt/$max_attempts: $service_name not ready yet..."
        sleep 30
        attempt=$((attempt + 1))
    done
    
    error "$service_name failed to become ready after $max_attempts attempts"
    return 1
}

# Function to check database connection
check_database() {
    log "Checking database connection..."
    
    # Try to connect to MongoDB
    if command -v mongosh >/dev/null 2>&1; then
        if mongosh "$MONGODB_URL" --eval "db.adminCommand('ping')" >/dev/null 2>&1; then
            success "MongoDB connection successful"
        else
            error "Failed to connect to MongoDB at $MONGODB_URL"
            return 1
        fi
    else
        warn "mongosh not available, skipping MongoDB connection test"
    fi
    
    # Try to connect to Redis
    if command -v redis-cli >/dev/null 2>&1; then
        if redis-cli -u "$REDIS_URL" ping >/dev/null 2>&1; then
            success "Redis connection successful"
        else
            error "Failed to connect to Redis at $REDIS_URL"
            return 1
        fi
    else
        warn "redis-cli not available, skipping Redis connection test"
    fi
}

# Function to initialize application
initialize_app() {
    log "Initializing Trading Bot application..."
    
    # Create necessary directories
    mkdir -p /app/logs/{trading,system,errors,audit}
    mkdir -p /app/data/{backtest,exports,cache}
    
    # Set proper permissions
    chmod 755 /app/logs /app/data
    
    # Copy default configuration if .env doesn't exist
    if [ ! -f /app/.env ]; then
        if [ -f /app/.env.example ]; then
            log "Creating .env from .env.example..."
            cp /app/.env.example /app/.env
        else
            warn "No .env.example found, creating minimal .env..."
            cat > /app/.env << EOF
# Minimal configuration for Docker deployment
ENVIRONMENT=production
DEBUG=false
MONGODB_URL=${MONGODB_URL:-mongodb://mongodb:27017/trading_bot}
REDIS_URL=${REDIS_URL:-redis://redis:6379/0}
CCXT_GATEWAY_URL=${CCXT_GATEWAY_URL:-http://ccxt-bridge:3000}
QUICKCHART_URL=${QUICKCHART_URL:-http://quickchart:3400}
SECRET_KEY=${SECRET_KEY:-change-me-in-production}
ENCRYPTION_KEY=${ENCRYPTION_KEY:-generate-new-fernet-key}
LOG_LEVEL=${LOG_LEVEL:-INFO}
EOF
        fi
    fi
    
    success "Application initialized successfully"
}

# Function to run health checks
health_check() {
    log "Running health checks..."
    
    # Check if Python dependencies are available
    python -c "import fastapi, pymongo, redis, httpx" 2>/dev/null || {
        error "Required Python packages not available"
        return 1
    }
    
    # Check configuration
    python src/main.py config --validate >/dev/null 2>&1 || {
        warn "Configuration validation failed, but continuing..."
    }
    
    success "Health checks completed"
}

# Main execution
main() {
    log "🤖 Starting Trading Bot Container..."
    log "Container ID: $(hostname)"
    log "Environment: ${ENVIRONMENT:-development}"
    log "Python version: $(python --version)"
    
    # Wait for external dependencies if URLs are provided
    if [ -n "$MONGODB_URL" ] && [[ "$MONGODB_URL" == *"mongodb:"* ]]; then
        # Extract host and port from MongoDB URL for health check
        MONGO_HOST=$(echo "$MONGODB_URL" | sed -n 's/.*\/\/\([^:]*\):.*/\1/p')
        MONGO_PORT=$(echo "$MONGODB_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
        if [ -n "$MONGO_HOST" ] && [ -n "$MONGO_PORT" ]; then
            wait_for_service "MongoDB" "http://$MONGO_HOST:$MONGO_PORT" || true
        fi
    fi
    
    if [ -n "$CCXT_GATEWAY_URL" ]; then
        wait_for_service "ccxt-gateway" "$CCXT_GATEWAY_URL/ticker?symbol=BTC/USDT" || true
    fi
    
    if [ -n "$QUICKCHART_URL" ]; then
        wait_for_service "QuickChart" "$QUICKCHART_URL/ticker?symbol=BTC/USDTcheck" || true
    fi
    
    # Initialize application
    initialize_app || {
        error "Failed to initialize application"
        exit 1
    }
    
    # Check database connections
    check_database || {
        warn "Database connection check failed, but continuing..."
    }
    
    # Run health checks
    health_check || {
        warn "Health checks failed, but continuing..."
    }
    
    success "🚀 Trading Bot is ready to start!"
    
    # If no arguments provided, start with default command
    if [ $# -eq 0 ]; then
        log "No command specified, starting with default mode..."
        exec python src/main.py start --mode paper --daemon
    else
        log "Executing command: $*"
        exec "$@"
    fi
}

# Trap signals for graceful shutdown
trap 'log "Received shutdown signal, stopping..."; exit 0' SIGTERM SIGINT

# Run main function
main "$@"
