# README.md

# 🤖 Light Trading Bot

A comprehensive, multi-interface cryptocurrency trading bot that supports backtesting, paper trading, and live trading across multiple exchanges.

![Trading Bot Banner](docs/images/banner.png)

## 🌟 Features

- **🎯 Multi-Mode Trading**: Live trading, paper trading, and backtesting
- **🏢 Multi-Exchange Support**: Integration via ccxt-gateway (KuCoin, Binance, OKX, Bybit)
- **🖥️ Multi-Interface Control**: CLI, Web Dashboard, and Telegram Bot
- **📊 Advanced Strategies**: Simple buy/sell, grid trading, and indicator-based strategies
- **🛡️ Risk Management**: Configurable limits, stop-loss, take-profit, and position sizing
- **📈 Comprehensive Analytics**: Performance metrics, backtesting reports, and chart visualization
- **🔒 Security**: Encrypted API keys, authentication, and rate limiting
- **🐳 Docker Ready**: Complete containerized deployment with docker-compose

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **Docker & Docker Compose** (recommended)
- **MongoDB** (for data storage)
- **Redis** (for caching)

### 1. Project Setup

```bash
# Clone or create project directory
mkdir trading_bot && cd trading_bot

# Run the setup script
chmod +x scripts/setup_project.sh
./scripts/setup_project.sh
```

### 2. Environment Configuration

```bash
# Copy and configure environment variables
cp .env.example .env

# Edit .env with your settings
nano .env
```

**Essential Configuration:**
```bash
# Security (IMPORTANT: Change these!)
SECRET_KEY=your-secret-key-here
ENCRYPTION_KEY=your-fernet-encryption-key

# Database
MONGODB_URL=mongodb://localhost:27017/trading_bot
REDIS_URL=redis://localhost:6379/0

# External Services
CCXT_GATEWAY_URL=http://localhost:3000
QUICKCHART_URL=http://localhost:8080

# Telegram Bot (Optional)
TELEGRAM_BOT_TOKEN=your-bot-token-here
```

### 3. Installation Options

#### Option A: Docker Deployment (Recommended)

```bash
# Start the complete stack
docker-compose up -d

# View logs
docker-compose logs -f trading-bot

# Stop the stack
docker-compose down
```

#### Option B: Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Start MongoDB and Redis locally
# (Install and configure separately)

# Run the application
python src/main.py start --mode paper
```

## 🎮 Usage

### CLI Interface

```bash
# Start the bot
python src/main.py start --mode paper --strategy simple_buy_sell

# View status
python src/main.py status --detailed

# Run backtest
python src/main.py backtest --strategy grid_trading --symbol BTC/USDT

# Start web interface
python src/main.py web --port 5000

# Start Telegram bot
python src/main.py telegram

# View logs
python src/main.py logs --follow

# Show configuration
python src/main.py config --validate
```

### Web Dashboard

Access the web interface at `http://localhost:5000`:

- **📊 Dashboard**: Portfolio overview and performance metrics
- **💹 Trading**: Manual trading interface and order management
- **📈 Strategies**: Strategy configuration and marketplace
- **🧪 Backtesting**: Historical strategy testing and analysis
- **⚙️ Settings**: Account, exchange, and notification configuration

### Telegram Bot Commands

```
/start - Initialize bot
/status - Show trading status
/balance - Account balances
/trades - Active trades
/buy BTC/USDT 100 - Buy $100 of BTC
/sell BTC/USDT 0.001 - Sell 0.001 BTC
/stop - Emergency stop all trading
/strategies - List available strategies
/backtest strategy_name BTC/USDT - Quick backtest
```

## 📊 Trading Modes

### 1. Paper Trading (Default)
- **Safe testing** with simulated money
- **Real-time data** from exchanges
- **Realistic execution** with fees and slippage
- **Perfect for beginners** and strategy testing

```bash
python src/main.py start --mode paper
```

### 2. Live Trading
- **Real money trading** with actual exchanges
- **Full risk management** and safety controls
- **API key encryption** and secure storage
- **Comprehensive logging** and audit trail

```bash
python src/main.py start --mode live --strategy grid_trading
```

### 3. Backtesting
- **Historical data analysis** for strategy validation
- **Performance metrics** (Sharpe ratio, drawdown, win rate)
- **Multiple timeframes** and comprehensive reports
- **Export results** to CSV/JSON

```bash
python src/main.py backtest \
  --strategy indicator_based \
  --symbol BTC/USDT \
  --start-date 2024-01-01 \
  --end-date 2024-02-01
```

## 🧠 Trading Strategies

### Built-in Strategies

#### 1. Simple Buy/Sell
```yaml
strategy:
  type: simple_buy_sell
  config:
    buy_threshold: -5.0    # Buy when price drops 5%
    sell_threshold: 10.0   # Sell when profit reaches 10%
    timeframe: 1h
    lookback_period: 24
```

#### 2. Grid Trading
```yaml
strategy:
  type: grid_trading
  config:
    grid_levels: 10
    grid_spacing: 1.0      # 1% between grid levels
    base_amount: 100       # $100 per grid level
    upper_limit: 50000     # Upper price limit
    lower_limit: 40000     # Lower price limit
```

#### 3. Indicator-Based
```yaml
strategy:
  type: indicator_based
  config:
    timeframe: 4h
    entry_indicators:
      - type: RSI
        period: 14
        oversold: 30
    exit_indicators:
      - type: RSI
        period: 14
        overbought: 70
```

### Custom Strategy Development

Create custom strategies by extending the base strategy class:

```python
# src/strategies/custom/my_strategy.py
from strategies.base.base_strategy import BaseStrategy

class MyCustomStrategy(BaseStrategy):
    def __init__(self, config):
        super().__init__(config)
        
    async def should_buy(self, data):
        # Your buy logic here
        return signal, confidence
        
    async def should_sell(self, data):
        # Your sell logic here
        return signal, confidence
```

## 🛡️ Risk Management

### Configuration Options

```yaml
risk_management:
  global_balance_limit: 0.5     # Use max 50% of balance
  per_trade_budget: 100         # $100 per trade
  max_concurrent_trades: 10     # Max 10 open positions
  max_trades_per_symbol: 2      # Max 2 positions per symbol
  stop_loss: 0.05              # 5% stop loss
  take_profit: 0.15            # 15% take profit
  trailing_stop: true          # Enable trailing stops
```

### Emergency Controls

- **Panic Button**: Stop all trading immediately
- **Position Limits**: Automatic position sizing
- **Balance Protection**: Prevent over-exposure
- **API Rate Limiting**: Protect against API abuse

## 🔧 Configuration

### Database Configuration

```yaml
# MongoDB setup
MONGODB_URL=mongodb://localhost:27017/trading_bot

# Collections created automatically:
# - users (user accounts)
# - exchanges (API configurations)
# - strategies (trading strategies)
# - trades (trade history)
# - backtests (backtest results)
```

### Exchange Configuration

Add exchange API keys via the web interface or environment variables:

```bash
# KuCoin
KUCOIN_API_KEY=your_api_key
KUCOIN_API_SECRET=your_secret
KUCOIN_PASSPHRASE=your_passphrase

# Binance
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_secret
```

### Telegram Bot Setup

1. Create a bot via [@BotFather](https://t.me/botfather)
2. Add the bot token to your `.env` file
3. Get your user ID and add to allowed users
4. Start the bot: `python src/main.py telegram`

## 📈 API Integration

### ccxt-gateway Integration

The bot uses ccxt-gateway for exchange integration:

```bash
# Market data
curl "http://localhost:3000/marketdata?symbol=BTC/USDT&interval=1h&limit=150"

# Account balance
curl -H "X-EXCHANGE: kucoin" \
     -H "X-API-KEY: your_key" \
     http://localhost:3000/balance

# Place trade
curl -X POST http://localhost:3000/trade \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTC/USDT","side":"buy","type":"market","amount":0.01}'
```

### Chart Generation

Charts are generated using QuickChart:

```bash
# Generate candlestick chart
curl -X POST http://localhost:8080/chart \
  -H "Content-Type: application/json" \
  -d '{"chart":{"type":"candlestick","data":{...}}}'
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/          # Unit tests
pytest tests/integration/   # Integration tests
pytest tests/e2e/          # End-to-end tests

# Run with coverage
pytest --cov=src tests/
```

### Test Configuration

```bash
# Use test environment
export ENVIRONMENT=testing
export TESTING=true

# Run with mock APIs
export MOCK_EXTERNAL_APIS=true
python src/main.py start --mode paper
```

## 📊 Monitoring & Logging

### Log Levels and Locations

```bash
# Application logs
logs/trading_bot.log        # Main application log
logs/trading/               # Trading-specific logs
logs/errors/                # Error logs
logs/audit/                 # Audit trail
```

### Monitoring Stack (Optional)

Enable monitoring with the monitoring profile:

```bash
# Start with monitoring
docker-compose --profile monitoring up -d

# Access monitoring dashboards
http://localhost:9090       # Prometheus
http://localhost:3001       # Grafana (admin/admin123)
```

## 🔒 Security Best Practices

### API Key Security
- ✅ API keys are encrypted using Fernet encryption
- ✅ Keys are stored securely in MongoDB
- ✅ Environment variables for sensitive data
- ✅ No keys logged or exposed in plain text

### Authentication
- ✅ Secure password hashing with bcrypt
- ✅ JWT tokens for API authentication
- ✅ Session management with secure cookies
- ✅ Rate limiting on all endpoints

### Network Security
- ✅ CORS configuration for web interface
- ✅ Input validation and sanitization
- ✅ SQL injection prevention (NoSQL)
- ✅ XSS protection

## 🚀 Deployment

### Production Deployment

1. **Generate secure keys:**
```bash
# Generate Fernet key for encryption
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Generate secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

2. **Configure production environment:**
```bash
# Set production variables
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=your-generated-secret-key
ENCRYPTION_KEY=your-generated-fernet-key
```

3. **Deploy with Docker:**
```bash
# Production deployment
docker-compose -f docker-compose.yml --profile production up -d
```

### Scaling Considerations

- **Database**: Use MongoDB Atlas or dedicated MongoDB cluster
- **Cache**: Use Redis Cluster for high availability
- **Load Balancing**: Use nginx or cloud load balancer
- **Monitoring**: Implement Prometheus + Grafana for metrics

## 📚 Documentation

- **[API Documentation](docs/api/)** - Complete API reference
- **[User Guide](docs/user_guide/)** - Detailed user manual
- **[Development Guide](docs/development/)** - Contributing guidelines
- **[Deployment Guide](docs/deployment/)** - Production deployment

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Run tests: `pytest`
5. Submit a pull request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt

# Install pre-commit hooks
pre-commit install

# Run linting and formatting
black src/
flake8 src/
mypy src/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

**This software is for educational and research purposes only. Cryptocurrency trading involves substantial risk of loss. Use at your own risk. The authors are not responsible for any financial losses.**

## 🆘 Support

- **GitHub Issues**: Report bugs and request features
- **Documentation**: Check the [docs](docs/) directory
- **Telegram**: Join our community group (if available)

## 🏗️ Roadmap

### Version 0.1 (Current)
- ✅ Core trading engine
- ✅ Multi-interface support
- ✅ Basic strategies
- ✅ Risk management
- ✅ Docker deployment

### Version 0.2 (Planned)
- 🔄 AI signal analysis
- 🔄 Advanced backtesting
- 🔄 Strategy marketplace
- 🔄 Mobile app
- 🔄 Social trading features

---

**Made with ❤️ by the Trading Bot Team**

*Last updated: 2024-01-20*