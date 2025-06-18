#!/bin/bash
# quick-start.sh
# Quick test setup script for Trading Bot

set -e  # Exit on any error

echo "🚀 Trading Bot - Quick Start Setup"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if Docker is running
check_docker() {
    print_status "Checking Docker..."
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    print_success "Docker is running"
}

# Check if docker-compose is available
check_docker_compose() {
    print_status "Checking Docker Compose..."
    if command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    elif docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        print_error "Docker Compose is not available. Please install Docker Compose."
        exit 1
    fi
    
    print_success "Docker Compose is available: $COMPOSE_CMD"
}

# Check if ccxt-bridge image exists
check_ccxt_image() {
    print_status "Checking ccxt-bridge image..."
    if docker image inspect mat/ccxt-bridge:latest &> /dev/null; then
        print_success "ccxt-bridge image found: mat/ccxt-bridge:latest"
    else
        print_error "ccxt-bridge image not found: mat/ccxt-bridge:latest"
        print_warning "Please build or pull the ccxt-bridge image first"
        exit 1
    fi
}

# Setup environment file
setup_env() {
    print_status "Setting up environment configuration..."
    
    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            cp .env.example .env
            print_success "Created .env from .env.example"
            
            # Generate secure keys
            print_status "Generating secure keys..."
            
            # Generate SECRET_KEY
            SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || openssl rand -base64 32)
            sed -i.bak "s/your_secret_key_min_32_characters_long_change_this/$SECRET_KEY/" .env
            
            # Generate ENCRYPTION_KEY
            ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || echo "NEED_TO_GENERATE_MANUALLY")
            if [ "$ENCRYPTION_KEY" != "NEED_TO_GENERATE_MANUALLY" ]; then
                sed -i.bak "s/fernet_key_44_characters_base64_encoded_here_change_this/$ENCRYPTION_KEY/" .env
            fi
            
            # Generate JWT_SECRET
            JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || openssl rand -base64 32)
            sed -i.bak "s/your_jwt_secret_key_for_authentication_change_this/$JWT_SECRET/" .env
            
            # Clean up backup file
            rm -f .env.bak
            
            print_success "Generated secure keys"
        else
            print_error ".env.example file not found. Please create it first."
            exit 1
        fi
    else
        print_success ".env file already exists"
    fi
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    mkdir -p logs data config mongodb/init
    
    # Create a basic config file
    cat > config/trading.yaml << EOF
# Basic trading configuration for testing
trading:
  default_mode: paper
  supported_exchanges: [kucoin, binance]
  supported_timeframes: [1m, 5m, 15m, 30m, 1h, 4h, 8h, 1d, 1w]
  max_concurrent_trades: 5
  default_quote_currency: USDT

risk_management:
  global_balance_limit: 0.5
  per_trade_budget: 100
  stop_loss_percentage: 0.05
  take_profit_percentage: 0.15

backtesting:
  default_start_balance: 10000
  commission: 0.0005
  slippage: 0.0002
EOF

    print_success "Created directories and basic configuration"
}

# Start services
start_services() {
    print_status "Starting services with Docker Compose..."
    
    # Pull/build images
    print_status "Pulling required images..."
    $COMPOSE_CMD pull mongodb redis quickchart
    
    # Start services
    print_status "Starting all services..."
    $COMPOSE_CMD up -d
    
    print_success "Services started!"
}

# Wait for services to be ready
wait_for_services() {
    print_status "Waiting for services to be ready..."
    
    # Wait for MongoDB
    print_status "Waiting for MongoDB..."
    for i in {1..30}; do
        if $COMPOSE_CMD exec -T mongodb mongosh --eval "db.adminCommand('ping')" &> /dev/null; then
            break
        fi
        sleep 2
    done
    
    # Wait for ccxt-bridge
    print_status "Waiting for ccxt-bridge..."
    for i in {1..30}; do
        if $COMPOSE_CMD exec -T ccxt-bridge curl -f http://localhost:3000/health &> /dev/null; then
            break
        fi
        sleep 2
    done
    
    # Wait for quickchart
    print_status "Waiting for quickchart..."
    for i in {1..30}; do
        if curl -f http://localhost:8080/healthcheck &> /dev/null; then
            break
        fi
        sleep 2
    done
    
    print_success "All services are ready!"
}

# Test services
test_services() {
    print_status "Testing service connectivity..."
    
    # Test MongoDB
    if $COMPOSE_CMD exec -T mongodb mongosh --eval "db.adminCommand('ping')" &> /dev/null; then
        print_success "MongoDB: ✅ Connected"
    else
        print_error "MongoDB: ❌ Connection failed"
    fi
    
    # Test ccxt-bridge (internal)
    if $COMPOSE_CMD exec -T ccxt-bridge curl -f http://localhost:3000/health &> /dev/null; then
        print_success "ccxt-bridge: ✅ Available (internal)"
    else
        print_error "ccxt-bridge: ❌ Not available"
    fi
    
    # Test quickchart
    if curl -f http://localhost:8080/healthcheck &> /dev/null; then
        print_success "quickchart: ✅ Available at http://localhost:8080"
    else
        print_error "quickchart: ❌ Not available"
    fi
    
    # Test Redis
    if $COMPOSE_CMD exec -T redis redis-cli ping &> /dev/null; then
        print_success "Redis: ✅ Connected"
    else
        print_warning "Redis: ⚠️  Connection issue (non-critical)"
    fi
    
    # Test Trading Bot (when it's built)
    sleep 5
    if curl -f http://localhost:5000/health &> /dev/null; then
        print_success "Trading Bot: ✅ Available at http://localhost:5000"
    else
        print_warning "Trading Bot: ⚠️  Still starting up..."
    fi
}

# Show useful information
show_info() {
    echo ""
    echo "🎉 Setup Complete!"
    echo "=================="
    echo ""
    echo "📱 Web Interface: http://localhost:5000"
    echo "📊 QuickChart: http://localhost:8080"
    echo "🗄️  MongoDB: localhost:27017"
    echo "🔄 Redis: localhost:6379"
    echo ""
    echo "🔧 Useful Commands:"
    echo "  View logs:        $COMPOSE_CMD logs -f trading-bot"
    echo "  Stop services:    $COMPOSE_CMD down"
    echo "  Restart:          $COMPOSE_CMD restart trading-bot"
    echo "  Check status:     $COMPOSE_CMD ps"
    echo ""
    echo "📝 Next Steps:"
    echo "  1. Open http://localhost:5000 in your browser"
    echo "  2. Configure your exchange API keys"
    echo "  3. Set up your trading strategies"
    echo "  4. Start with paper trading mode"
    echo ""
    echo "🔍 Test Market Data:"
    echo "  $COMPOSE_CMD exec trading-bot python bot.py test-data BTC/USDT 1h"
    echo ""
}

# Main execution
main() {
    echo ""
    check_docker
    check_docker_compose
    check_ccxt_image
    setup_env
    create_directories
    start_services
    wait_for_services
    test_services
    show_info
    
    print_success "Trading Bot is ready for testing! 🚀"
}

# Handle Ctrl+C
trap 'echo -e "\n${RED}Setup interrupted${NC}"; exit 1' INT

# Run main function
main "$@"