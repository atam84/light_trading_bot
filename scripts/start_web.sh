#!/bin/bash
# Start web interface separately

echo "🌐 Starting Web Interface..."

# Start the web interface in background
docker-compose exec trading-bot python src/main.py web --port 5000 --host 0.0.0.0 &

echo "✅ Web interface should be available at: http://localhost:5000"
echo "📊 Check status with: docker logs trading-bot | grep -i web"
