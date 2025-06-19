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
