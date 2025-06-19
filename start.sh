#!/bin/bash
# start.sh
# Universal start script for Light Trading Bot

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_banner() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    🤖 LIGHT TRADING BOT 🤖                   ║"
    echo "║                  Quick Start Deployment                     ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --docker       Start with Docker Compose"
    echo "  --local        Start locally with Python"
    echo "  --dev          Start in development mode"
    echo "  --help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --docker    # Start with Docker (recommended)"
    echo "  $0 --local     # Start locally"
    echo "  $0 --dev       # Development mode with auto-reload"
}

start_docker() {
    print_status "Starting with Docker Compose..."
    
    # Check Docker installation
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed!"
        echo "Please install Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed!"
        echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
        exit 1
    fi
    
    # Make deploy script executable and run it
    chmod +x deploy-docker.sh
    ./deploy-docker.sh
}

start_local() {
    print_status "Starting locally with Python..."
    
    # Check Python installation
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed!"
        exit 1
    fi
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        print_status "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    print_status "Activating virtual environment..."
    source venv/bin/activate
    
    # Install dependencies
    print_status "Installing dependencies..."
    pip install -r requirements.txt
    pip install python-jose[cryptography] passlib[bcrypt] python-multipart aiohttp jinja2
    
    # Start the application
    print_status "Starting Trading Bot..."
    python startup.py
}

start_dev() {
    print_status "Starting in development mode..."
    
    # Same as local but with debug flag
    if [ ! -d "venv" ]; then
        print_status "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    source venv/bin/activate
    pip install -r requirements.txt
    pip install python-jose[cryptography] passlib[bcrypt] python-multipart aiohttp jinja2
    
    # Start with debug mode
    python startup.py --debug --host 127.0.0.1
}

# Main script logic
print_banner

# Parse command line arguments
case "$1" in
    --docker)
        start_docker
        ;;
    --local)
        start_local
        ;;
    --dev)
        start_dev
        ;;
    --help)
        show_help
        ;;
    "")
        # No arguments - show interactive menu
        echo "How would you like to start the Trading Bot?"
        echo ""
        echo "1) Docker (Recommended - includes all services)"
        echo "2) Local Python (Requires MongoDB and Redis separately)"
        echo "3) Development mode (Local with debug)"
        echo "4) Help"
        echo ""
        read -p "Choose an option [1-4]: " choice
        
        case $choice in
            1)
                start_docker
                ;;
            2)
                start_local
                ;;
            3)
                start_dev
                ;;
            4)
                show_help
                ;;
            *)
                print_error "Invalid option. Use --help for usage information."
                exit 1
                ;;
        esac
        ;;
    *)
        print_error "Unknown option: $1"
        show_help
        exit 1
        ;;
esac
