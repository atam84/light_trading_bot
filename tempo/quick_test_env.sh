# .env.example
# Copy this file to .env and update the values

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================
MONGODB_URL=mongodb://trader:secure_trading_password@mongodb:27017/trading_bot
MONGO_USERNAME=trader
MONGO_PASSWORD=secure_trading_password

# =============================================================================
# SECURITY CONFIGURATION
# =============================================================================
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=your_secret_key_min_32_characters_long_change_this

# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=fernet_key_44_characters_base64_encoded_here_change_this

# Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
JWT_SECRET=your_jwt_secret_key_for_authentication_change_this

# =============================================================================
# EXTERNAL SERVICES (Internal Docker Network)
# =============================================================================
CCXT_GATEWAY_URL=http://ccxt-bridge:3000
QUICKCHART_URL=http://quickchart:3400
REDIS_URL=redis://:redis_trading_password@redis:6379/0

# =============================================================================
# WEB APPLICATION
# =============================================================================
FLASK_ENV=development
WEB_HOST=0.0.0.0
WEB_PORT=5000
LOG_LEVEL=INFO

# =============================================================================
# TRADING CONFIGURATION
# =============================================================================
DEFAULT_EXCHANGE=kucoin
DEFAULT_QUOTE_CURRENCY=USDT
DEFAULT_FEE_RATE=0.0005

# Risk Management Defaults
GLOBAL_BALANCE_LIMIT=0.5
PER_TRADE_BUDGET=100
MAX_CONCURRENT_TRADES=10
STOP_LOSS_PERCENTAGE=0.05
TAKE_PROFIT_PERCENTAGE=0.15

# =============================================================================
# TELEGRAM BOT (Optional)
# =============================================================================
# Get token from @BotFather on Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_if_needed

# =============================================================================
# EXCHANGE API KEYS (Will be stored encrypted in database)
# =============================================================================
# These are examples - you'll add them via the web interface
# KUCOIN_API_KEY=your_kucoin_api_key
# KUCOIN_API_SECRET=your_kucoin_api_secret
# KUCOIN_PASSPHRASE=your_kucoin_passphrase

# BINANCE_API_KEY=your_binance_api_key
# BINANCE_API_SECRET=your_binance_api_secret

# =============================================================================
# DEVELOPMENT/TESTING
# =============================================================================
TESTING=false
MOCK_TRADING=false
PAPER_TRADING_BALANCE=10000