#!/bin/bash
# scripts/fix_web_interface.sh - Fix web interface startup issue

echo "🌐 Fixing Web Interface Startup Issue..."
echo "========================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

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

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

print_status "Diagnosing web interface issue..."

# Check current container status
print_status "Checking container status..."
docker-compose ps

# Check if web interface files exist
print_status "Checking web interface files..."
if [ ! -f "src/interfaces/web/app.py" ]; then
    print_error "Web interface app.py not found!"
    print_status "The web interface implementation may be incomplete"
fi

# Check main.py for web startup
print_status "Checking main.py startup logic..."
if ! grep -q "web\|flask\|fastapi" src/main.py; then
    print_warning "No web server startup found in main.py"
fi

# Solution 1: Start web interface separately
print_status "Creating separate web interface startup script..."
cat > scripts/start_web.sh << 'EOF'
#!/bin/bash
# Start web interface separately

echo "🌐 Starting Web Interface..."

# Start the web interface in background
docker-compose exec trading-bot python src/main.py web --port 5000 --host 0.0.0.0 &

echo "✅ Web interface should be available at: http://localhost:5000"
echo "📊 Check status with: docker logs trading-bot | grep -i web"
EOF

chmod +x scripts/start_web.sh

# Solution 2: Create web-only service 
print_status "Creating web-only docker service option..."
cat > docker-compose.web.yml << 'EOF'
version: '3.8'

services:
  trading-bot-web:
    build: .
    container_name: trading-bot-web
    ports:
      - "5000:5000"
    environment:
      - MONGODB_URL=mongodb://mongodb:27017/trading_bot
      - CCXT_GATEWAY_URL=http://ccxt-bridge:3000
      - QUICKCHART_URL=http://quickchart:8080
      - WEB_ONLY=true
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    depends_on:
      - mongodb
      - ccxt-bridge
      - quickchart
    command: python src/main.py web --port 5000 --host 0.0.0.0
    restart: unless-stopped
EOF

# Solution 3: Quick test commands
print_status "Creating web interface test commands..."
cat > scripts/test_web.sh << 'EOF'
#!/bin/bash
# Test web interface

echo "🧪 Testing Web Interface..."

# Test if web server is responding
echo "Testing web server response..."
curl -v http://localhost:5000/ 2>&1 | head -20

echo ""
echo "Testing web health endpoint..."
curl -s http://localhost:5000/health || echo "Health endpoint not available"

echo ""
echo "Testing web API endpoints..."
curl -s http://localhost:5000/api/status || echo "API status endpoint not available"

echo ""
echo "🔍 Checking container logs for web-related messages..."
docker logs trading-bot 2>&1 | grep -i -E "(web|flask|fastapi|5000)" | tail -10
EOF

chmod +x scripts/test_web.sh

print_success "Web interface fix scripts created!"
echo ""
echo "🚀 Available Solutions:"
echo ""
echo "1️⃣  Start web interface separately:"
echo "   ./scripts/start_web.sh"
echo ""
echo "2️⃣  Use web-only service:"
echo "   docker-compose -f docker-compose.web.yml up -d"
echo ""  
echo "3️⃣  Test current web interface:"
echo "   ./scripts/test_web.sh"
echo ""
echo "4️⃣  Check container logs for web startup:"
echo "   docker logs trading-bot | grep -i web"
echo ""
echo "🎯 The issue is likely that the main bot process starts only the trading engine,"
echo "   but not the web server. The web interface needs to be started separately"
echo "   or the main.py needs to be modified to start both services."