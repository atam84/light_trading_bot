# README-QUICK-TEST.md

# 🚀 Trading Bot - Quick Test Setup

Ready-to-use Docker configuration for testing the trading bot with your local ccxt-bridge image.

## 📋 Prerequisites

- **Docker** & **Docker Compose** installed
- **ccxt-bridge** local image: `mat/ccxt-bridge:latest`
- **4GB RAM** available for containers

## ⚡ Quick Start (30 seconds)

```bash
# 1. Make the script executable
chmod +x quick-start.sh

# 2. Run the setup script
./quick-start.sh
```

That's it! The script will:
- ✅ Check all prerequisites
- ✅ Generate secure keys automatically
- ✅ Create necessary directories
- ✅ Start all services
- ✅ Test connectivity
- ✅ Show access URLs

## 🌐 Access Points

| Service | URL | Purpose |
|---------|-----|---------|
| **Trading Bot Web UI** | http://localhost:5000 | Main dashboard |
| **QuickChart** | http://localhost:8080 | Chart generation |
| **MongoDB** | localhost:27017 | Database (if needed) |

## 🔧 Manual Setup (Alternative)

If you prefer manual setup:

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Edit .env file with your settings
nano .env

# 3. Start services
docker-compose up -d

# 4. Check logs
docker-compose logs -f trading-bot
```

## 📊 Service Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Trading Bot   │    │   ccxt-bridge   │    │   QuickChart    │
│   Port: 5000    │◄──►│   Port: 3000    │    │   Port: 8080    │
│   (External)    │    │   (Internal)    │    │   (External)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                                               │
         ▼                                               ▼
┌─────────────────┐                        ┌─────────────────┐
│    MongoDB      │                        │     Redis       │
│   Port: 27017   │                        │   Port: 6379    │
│   (External)    │                        │   (External)    │
└─────────────────┘                        └─────────────────┘
```

## 🧪 Testing Commands

```bash
# Check all services status
docker-compose ps

# View trading bot logs
docker-compose logs -f trading-bot

# Test market data
docker-compose exec trading-bot python bot.py test-data BTC/USDT 1h

# Check bot status
docker-compose exec trading-bot python bot.py status

# Test ccxt-bridge connectivity (internal)
docker-compose exec trading-bot curl http://ccxt-bridge:3000/health
```

## ⚙️ Configuration

### Exchange API Keys
Add your exchange API keys via the web interface:
1. Open http://localhost:5000
2. Go to Settings → Exchanges
3. Add your KuCoin/Binance credentials

### Trading Strategies
Configure strategies via:
- **Web UI**: http://localhost:5000/strategies
- **CLI**: `docker-compose exec trading-bot python bot.py strategies list`

## 🔒 Security Notes

- All API keys are **encrypted** before storage
- ccxt-bridge runs **internal only** (no external access)
- Default credentials are for **testing only**
- Change passwords in production

## 🛠️ Useful Commands

### Service Management
```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart trading bot
docker-compose restart trading-bot

# View all logs
docker-compose logs

# Shell access
docker-compose exec trading-bot bash
```

### Trading Operations
```bash
# CLI access
docker-compose exec trading-bot python bot.py --help

# Check balance
docker-compose exec trading-bot python bot.py balance

# List strategies
docker-compose exec trading-bot python bot.py strategies list

# Start paper trading
docker-compose exec trading-bot python bot.py start --mode paper
```

### Database Operations
```bash
# MongoDB shell access
docker-compose exec mongodb mongosh

# Check database
docker-compose exec mongodb mongosh trading_bot --eval "show collections"

# Redis CLI access
docker-compose exec redis redis-cli
```

## 🚨 Troubleshooting

### Common Issues

#### ccxt-bridge image not found
```bash
# Check if image exists
docker images | grep ccxt-bridge

# If missing, build or pull your image
# docker build -t mat/ccxt-bridge:latest /path/to/ccxt-bridge
```

#### Services not starting
```bash
# Check Docker resources
docker system df

# Free up space if needed
docker system prune

# Check logs for errors
docker-compose logs ccxt-bridge
```

#### Web UI not accessible
```bash
# Check if trading-bot is running
docker-compose ps

# Check logs for errors
docker-compose logs trading-bot

# Restart if needed
docker-compose restart trading-bot
```

### Health Checks
```bash
# All services health
curl http://localhost:5000/health

# QuickChart health
curl http://localhost:8080/healthcheck

# MongoDB connection
docker-compose exec mongodb mongosh --eval "db.adminCommand('ping')"
```

## 📈 Next Steps

1. **Configure Exchange**: Add API keys in web interface
2. **Set Strategy**: Choose or create trading strategy
3. **Paper Trading**: Test with virtual money first
4. **Monitor**: Watch logs and performance
5. **Live Trading**: When ready, switch to live mode

## 🆘 Support

### Log Files
- Trading Bot: `docker-compose logs trading-bot`
- All Services: `docker-compose logs`
- System: `./logs/trading_bot.log`

### Quick Diagnostics
```bash
# Run diagnostics
docker-compose exec trading-bot python bot.py diagnose

# Check connectivity
docker-compose exec trading-bot python scripts/test_connectivity.py
```

---

**Ready to trade! 🎯**

For detailed documentation, see: `docs/deployment-and-testing.md`