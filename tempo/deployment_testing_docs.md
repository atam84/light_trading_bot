# docs/deployment-and-testing.md

# 🚀 Trading Bot - Deployment & Testing Guide

## 📋 Table of Contents
1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Docker Deployment](#docker-deployment)
4. [Manual Deployment](#manual-deployment)
5. [Configuration](#configuration)
6. [Health Checks](#health-checks)
7. [Testing Procedures](#testing-procedures)
8. [Troubleshooting](#troubleshooting)
9. [Monitoring](#monitoring)
10. [Backup & Recovery](#backup-recovery)

---

## 🔧 Prerequisites

### System Requirements
- **OS**: Ubuntu 20.04+ / macOS 12+ / Windows 10+
- **RAM**: Minimum 2GB, Recommended 4GB+
- **Storage**: 10GB free space
- **Network**: Stable internet connection

### Software Dependencies
- **Docker**: 20.10+ & Docker Compose 2.0+
- **Python**: 3.10+ (for manual deployment)
- **Git**: For source code management
- **MongoDB**: 6.0+ (included in Docker setup)

### External Services
- **ccxt-gateway**: Must be running on `http://ccxt-bridge:3000`
- **quickchart**: Must be running on `http://quickchart:8080`
- **Exchange API**: KuCoin, Binance, or supported exchange account

---

## 🌍 Environment Setup

### 1. Clone Repository
```bash
git clone <repository-url>
cd trading-bot
```

### 2. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

### 3. Required Environment Variables
```bash
# Database
MONGODB_URL=mongodb://mongodb:27017/trading_bot
MONGO_USERNAME=trader
MONGO_PASSWORD=secure_password_here

# Security
SECRET_KEY=your_flask_secret_key_32_chars_min
ENCRYPTION_KEY=your_fernet_key_44_chars_base64
JWT_SECRET=your_jwt_secret_key_here

# External Services
CCXT_GATEWAY_URL=http://ccxt-bridge:3000
QUICKCHART_URL=http://quickchart:8080

# Web UI
WEB_HOST=0.0.0.0
WEB_PORT=5000

# Telegram (Optional)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# Trading
DEFAULT_EXCHANGE=kucoin
DEFAULT_QUOTE_CURRENCY=USDT
```

---

## 🐳 Docker Deployment (Recommended)

### 1. Build and Start Services
```bash
# Build and start all services
docker-compose up -d

# Check services status
docker-compose ps

# View logs
docker-compose logs -f trading-bot
```

### 2. Service Health Check
```bash
# Check trading bot health
curl http://localhost:5000/health

# Check API status
curl http://localhost:5000/api/status

# Check MongoDB connection
docker-compose exec mongodb mongosh --eval "db.adminCommand('ping')"
```

### 3. Docker Compose Services
```yaml
services:
  - trading-bot:5000     # Web UI & API
  - mongodb:27017        # Database
  - ccxt-bridge:3000     # Exchange gateway
  - quickchart:8080      # Chart service
  - redis:6379           # Cache (optional)
```

### 4. Docker Commands Reference
```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart specific service
docker-compose restart trading-bot

# View logs
docker-compose logs -f trading-bot

# Execute commands in container
docker-compose exec trading-bot python bot.py status

# Rebuild after code changes
docker-compose build trading-bot
docker-compose up -d trading-bot
```

---

## 🔧 Manual Deployment

### 1. Python Environment Setup
```bash
# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. MongoDB Setup
```bash
# Install MongoDB (Ubuntu)
sudo apt update
sudo apt install mongodb

# Start MongoDB
sudo systemctl start mongodb
sudo systemctl enable mongodb

# Create database and user
mongosh
> use trading_bot
> db.createUser({
    user: "trader",
    pwd: "secure_password",
    roles: ["readWrite"]
  })
```

### 3. Start Application
```bash
# Start web interface
python main.py web

# Start CLI interface
python main.py bot start

# Start with specific mode
python main.py bot start --mode paper
```

---

## ⚙️ Configuration

### 1. Exchange API Configuration
```bash
# Add exchange via CLI
python bot.py config add-exchange kucoin

# Or via web interface
http://localhost:5000/settings/exchanges
```

### 2. Strategy Configuration
```yaml
# config/strategies/simple_buy_sell.yaml
name: "Simple Buy/Sell"
type: "simple"
config:
  buy_threshold: -5.0
  sell_threshold: 10.0
  timeframe: "1h"
  lookback_period: 24
```

### 3. Risk Management Settings
```yaml
# config/risk_management.yaml
global_balance_limit: 0.5  # 50% of balance
per_trade_budget: 100      # USD
max_concurrent_trades: 10
max_trades_per_symbol: 2
stop_loss_percentage: 0.05
take_profit_percentage: 0.15
```

---

## 🏥 Health Checks

### 1. Application Health
```bash
# Web interface health
curl http://localhost:5000/health

# Expected response
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "services": {
    "database": "connected",
    "ccxt_gateway": "available",
    "quickchart": "available"
  }
}
```

### 2. Service Connectivity
```bash
# Test ccxt-gateway
curl http://localhost:3000/health

# Test quickchart
curl http://localhost:8080/healthcheck

# Test database
python -c "
from src.database.connection import DatabaseManager
import asyncio
async def test():
    db = DatabaseManager()
    await db.connect()
    print('Database: Connected')
asyncio.run(test())
"
```

### 3. Trading Bot Status
```bash
# CLI status check
python bot.py status

# API status check
curl http://localhost:5000/api/status

# Expected response
{
  "bot_status": "running",
  "mode": "paper",
  "active_strategies": 2,
  "open_trades": 3,
  "balance": {
    "USDT": 1000.00,
    "BTC": 0.025
  }
}
```

---

## 🧪 Testing Procedures

### 1. Unit Tests
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/unit/ -v
python -m pytest tests/integration/ -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

### 2. Integration Tests
```bash
# Test API clients
python -m pytest tests/integration/test_api_clients.py -v

# Test database operations
python -m pytest tests/integration/test_database.py -v

# Test strategy execution
python -m pytest tests/integration/test_strategies.py -v
```

### 3. End-to-End Tests
```bash
# Test complete trading flow
python -m pytest tests/e2e/test_trading_flow.py -v

# Test web interface
python -m pytest tests/e2e/test_web_interface.py -v

# Test CLI commands
python -m pytest tests/e2e/test_cli_commands.py -v
```

### 4. Manual Testing Checklist

#### Web Interface Testing
- [ ] Login/logout functionality
- [ ] Dashboard displays correctly
- [ ] Strategy management works
- [ ] Trading interface responsive
- [ ] Real-time updates functioning
- [ ] Mobile responsive design

#### CLI Testing
```bash
# Test bot commands
python bot.py status
python bot.py strategies list
python bot.py balance
python bot.py trade history

# Test configuration
python bot.py config show
python bot.py config validate
```

#### Telegram Bot Testing
```bash
# Send commands to bot
/start
/status
/balance
/strategies
/help
```

### 5. Performance Tests
```bash
# Load testing (requires pytest-benchmark)
python -m pytest tests/performance/ --benchmark-only

# Memory usage test
python -m pytest tests/performance/test_memory_usage.py

# API response time test
python -m pytest tests/performance/test_api_performance.py
```

---

## 🚨 Troubleshooting

### Common Issues & Solutions

#### 1. Service Connection Issues
```bash
# Issue: Cannot connect to MongoDB
# Solution: Check MongoDB service
docker-compose logs mongodb
docker-compose restart mongodb

# Issue: ccxt-gateway not responding
# Solution: Verify service status
curl http://localhost:3000/health
docker-compose restart ccxt-bridge
```

#### 2. Authentication Errors
```bash
# Issue: Exchange API authentication failed
# Solution: Verify API keys
python bot.py config show exchanges
python bot.py test-connection kucoin

# Issue: Web login not working
# Solution: Check JWT secret configuration
grep JWT_SECRET .env
```

#### 3. Trading Issues
```bash
# Issue: Orders not executing
# Solution: Check balance and API permissions
python bot.py balance
python bot.py test-trade --dry-run

# Issue: Strategy not generating signals
# Solution: Check market data availability
python bot.py test-data BTC/USDT 1h
```

#### 4. Performance Issues
```bash
# Issue: Slow response times
# Solution: Check system resources
docker stats
python bot.py logs --level debug

# Issue: High memory usage
# Solution: Restart services and check for memory leaks
docker-compose restart trading-bot
```

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python main.py web

# Check detailed logs
tail -f logs/trading_bot.log

# Enable API debug mode
export CCXT_DEBUG=1
python bot.py status
```

---

## 📊 Monitoring

### 1. Log Monitoring
```bash
# View live logs
docker-compose logs -f trading-bot

# Check error logs
grep "ERROR" logs/trading_bot.log

# View specific time range
grep "2024-01-15" logs/trading_bot.log
```

### 2. Performance Monitoring
```bash
# System resources
docker stats

# Application metrics
curl http://localhost:5000/api/metrics

# Database performance
docker-compose exec mongodb mongosh --eval "
  db.runCommand({serverStatus: 1}).metrics
"
```

### 3. Trading Monitoring
```bash
# Active trades
python bot.py trades

# Performance metrics
python bot.py performance

# Balance tracking
python bot.py balance --history
```

### 4. Alert Setup
```yaml
# config/alerts.yaml
alerts:
  balance_threshold: 100  # USD
  trade_failure_limit: 5
  api_error_threshold: 10
  notification_channels:
    - telegram
    - email
```

---

## 💾 Backup & Recovery

### 1. Database Backup
```bash
# Create backup
docker-compose exec mongodb mongodump \
  --db trading_bot \
  --out /backup/$(date +%Y%m%d_%H%M%S)

# Automated backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec mongodb mongodump \
  --db trading_bot \
  --out /backup/$DATE
tar -czf backup_$DATE.tar.gz /backup/$DATE
```

### 2. Configuration Backup
```bash
# Backup configuration files
tar -czf config_backup_$(date +%Y%m%d).tar.gz \
  .env config/ logs/

# Backup trading data
python scripts/export_trades.py --format json \
  --output backups/trades_$(date +%Y%m%d).json
```

### 3. Recovery Procedures
```bash
# Restore database
docker-compose exec mongodb mongorestore \
  --db trading_bot \
  /backup/20240115_143000/trading_bot

# Restore configuration
tar -xzf config_backup_20240115.tar.gz

# Verify restoration
python bot.py config validate
python bot.py status
```

---

## 🔐 Security Checklist

### Pre-Deployment Security
- [ ] Change default passwords
- [ ] Generate strong encryption keys
- [ ] Configure firewall rules
- [ ] Enable SSL/TLS for web interface
- [ ] Review API key permissions
- [ ] Update all dependencies

### Runtime Security
- [ ] Monitor failed login attempts
- [ ] Check API rate limiting
- [ ] Audit trading activities
- [ ] Monitor system logs
- [ ] Verify backup integrity

### Security Commands
```bash
# Check for security updates
pip list --outdated

# Audit dependencies
pip-audit

# Test security configuration
python scripts/security_check.py

# Generate new encryption key
python -c "
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
"
```

---

## 📈 Production Deployment Considerations

### 1. Environment Separation
```bash
# Development
docker-compose -f docker-compose.dev.yml up

# Staging
docker-compose -f docker-compose.staging.yml up

# Production
docker-compose -f docker-compose.prod.yml up
```

### 2. Scaling Configuration
```yaml
# docker-compose.prod.yml
services:
  trading-bot:
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### 3. Monitoring & Alerting
```bash
# Prometheus metrics endpoint
curl http://localhost:5000/metrics

# Grafana dashboard
http://localhost:3000

# Alert manager configuration
docker-compose -f monitoring/docker-compose.yml up
```

---

## 📞 Support & Maintenance

### Regular Maintenance Tasks
- [ ] Weekly: Check logs for errors
- [ ] Weekly: Verify backup integrity
- [ ] Monthly: Update dependencies
- [ ] Monthly: Review trading performance
- [ ] Quarterly: Security audit

### Getting Help
1. Check logs: `docker-compose logs trading-bot`
2. Run diagnostics: `python bot.py diagnose`
3. Check documentation: `docs/`
4. Review test results: `python -m pytest tests/ -v`

### Emergency Procedures
```bash
# Emergency stop all trading
python bot.py emergency-stop

# Emergency backup
./scripts/emergency_backup.sh

# Service restart
docker-compose restart trading-bot
```

---

**Last Updated**: January 2024  
**Version**: 1.0  
**Compatibility**: Trading Bot v0.1+