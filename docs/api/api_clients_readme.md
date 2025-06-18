# API Clients Documentation

## Overview

The API clients module provides integration with external services required for the trading bot:

- **ccxt-gateway**: Trading operations, market data, and account management
- **quickchart**: Chart generation and visualization

## Quick Start

```python
import asyncio
from src.api_clients import api_clients, get_market_data, create_price_chart

async def main():
    # Get market data
    market_data = await get_market_data('BTC/USDT', '1h', 50)
    
    # Create price chart
    chart_bytes = await create_price_chart(market_data, title='BTC/USDT Chart')
    
    # Save chart
    with open('btc_chart.png', 'wb') as f:
        f.write(chart_bytes)

asyncio.run(main())
```

## Architecture

### Base HTTP Client

All API clients inherit from `BaseHTTPClient` which provides:

- **Async/await support** with aiohttp
- **Automatic retries** with exponential backoff
- **Rate limiting** to prevent API abuse
- **Response caching** for performance optimization
- **Comprehensive error handling**

### CCXT Gateway Client

The `CCXTGatewayClient` handles trading operations:

#### Market Data
```python
async with api_clients() as api:
    # Get candlestick data
    market_data = await api.ccxt.get_market_data('BTC/USDT', '1h', 150)
    
    # Get current ticker
    ticker = await api.ccxt.get_ticker('BTC/USDT')
    
    # Get RSI indicator
    rsi = await api.ccxt.get_rsi('BTC/USDT', period=14, interval='1h')
```

#### Account Management
```python
async with api_clients() as api:
    # Get account balance
    balances = await api.ccxt.get_balance(
        exchange='kucoin',
        api_key='your_key',
        api_secret='your_secret',
        passphrase='your_passphrase'
    )
    
    # Get trading assets
    assets = await api.ccxt.get_assets('kucoin', 'key', 'secret')
```

#### Trading Operations
```python
async with api_clients() as api:
    # Place market buy order
    order = await api.ccxt.place_order(
        exchange='kucoin',
        api_key='key',
        api_secret='secret',
        symbol='BTC/USDT',
        side='buy',
        order_type='market',
        amount=0.01
    )
    
    # Place limit sell order
    order = await api.ccxt.place_order(
        exchange='kucoin',
        api_key='key',
        api_secret='secret',
        symbol='BTC/USDT',
        side='sell',
        order_type='limit',
        amount=0.01,
        price=50000.0
    )
    
    # Get order history
    orders = await api.ccxt.get_order_history('kucoin', 'key', 'secret')
```

### QuickChart Client

The `QuickChartClient` handles chart generation:

#### Candlestick Charts
```python
from src.api_clients import ChartConfig, TradeMarker

async with api_clients() as api:
    # Create chart configuration
    config = ChartConfig(
        chart_type='candlestick',
        width=1200,
        height=600,
        title='BTC/USDT Price Chart'
    )
    
    # Add trade markers
    trade_markers = [
        TradeMarker(timestamp, price, 'buy', amount=0.01),
        TradeMarker(timestamp, price, 'sell', amount=0.01)
    ]
    
    # Generate chart
    chart_bytes = await api.charts.create_candlestick_chart(
        market_data=market_data,
        config=config,
        trade_markers=trade_markers,
        color_scheme='dark'
    )
```

#### Performance Charts
```python
async with api_clients() as api:
    # Create performance chart
    portfolio_values = [
        {'x': timestamp, 'y': value} for timestamp, value in portfolio_data
    ]
    
    chart_bytes = await api.charts.create_performance_chart(
        portfolio_values=portfolio_values,
        config=config
    )
```

## Configuration

### Environment Variables

```bash
# API Service URLs
CCXT_GATEWAY_URL=http://ccxt-bridge:3000
QUICKCHART_URL=http://quickchart:8080

# Timeouts and Retries
API_TIMEOUT=30
API_MAX_RETRIES=3

# Rate Limiting
API_RATE_LIMIT_REQUESTS=60
API_RATE_LIMIT_WINDOW=60

# Caching
API_CACHE_ENABLED=true
API_DEFAULT_CACHE_TTL=60
API_MARKET_DATA_CACHE_TTL=60
API_TICKER_CACHE_TTL=10
API_BALANCE_CACHE_TTL=30

# Chart Settings
CHART_DEFAULT_WIDTH=800
CHART_DEFAULT_HEIGHT=400
CHART_DEFAULT_COLOR_SCHEME=default

# Exchange API Keys
KUCOIN_API_KEY=your_kucoin_api_key
KUCOIN_API_SECRET=your_kucoin_api_secret
KUCOIN_PASSPHRASE=your_kucoin_passphrase
KUCOIN_TESTNET=false

BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_api_secret
BINANCE_TESTNET=false
```

### Programmatic Configuration

```python
from src.config.api_config import get_api_config_manager, ExchangeConfig

# Get configuration manager
config_manager = get_api_config_manager()

# Add exchange configuration
exchange_config = ExchangeConfig(
    name='kucoin',
    display_name='KuCoin',
    api_key='your_key',
    api_secret='your_secret',
    passphrase='your_passphrase',
    testnet=False
)
config_manager.add_exchange(exchange_config)

# Update API settings
config_manager.update_config(
    timeout=45,
    max_retries=5,
    cache_enabled=True
)
```

## Data Models

### Market Data
```python
@dataclass
class MarketData:
    symbol: str
    interval: str
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    datetime_str: Optional[str] = None
```

### Balance Information
```python
@dataclass
class BalanceInfo:
    currency: str
    free: float
    used: float
    total: float
```

### Order Information
```python
@dataclass
class OrderInfo:
    id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    type: str  # 'market', 'limit'
    amount: float
    price: Optional[float]
    filled: float
    remaining: float
    status: str
    timestamp: int
    fee: Optional[float] = None
```

## Error Handling

The API clients provide comprehensive error handling:

```python
from src.utils.exceptions import (
    APIError, 
    TradingError, 
    ChartError,
    AuthenticationError,
    RateLimitError
)

try:
    await api.ccxt.get_market_data('INVALID/SYMBOL')
except TradingError as e:
    print(f"Trading error: {e}")
except APIError as e:
    print(f"API error: {e}")
```

### Error Types

- **APIError**: General API communication errors
- **AuthenticationError**: Invalid API credentials
- **RateLimitError**: Rate limit exceeded
- **TradingError**: Trading operation errors
- **ChartError**: Chart generation errors

## Caching

The clients implement intelligent caching:

- **Market data**: 60 seconds TTL
- **Ticker data**: 10 seconds TTL  
- **Balance data**: 30 seconds TTL
- **Chart data**: No caching (always fresh)

### Cache Management

```python
async with api_clients() as api:
    # Clear all caches
    api.ccxt.clear_cache()
    api.charts.clear_cache()
    
    # Get cache statistics
    stats = api.ccxt.get_cache_stats()
    print(f"Cache entries: {stats['total_entries']}")
```

## Rate Limiting

Built-in rate limiting prevents API abuse:

- **Default**: 60 requests per 60 seconds
- **Automatic backoff**: When limits are reached
- **Per-client**: Each client has independent limits

## Health Checks

Monitor API service health:

```python
async with api_clients() as api:
    health = await api.health_check()
    
    if health['ccxt_gateway']:
        print("✅ ccxt-gateway is healthy")
    
    if health['quickchart']:
        print("✅ quickchart is healthy")
```

## Testing

Run the test suite:

```bash
# Run all API client tests
pytest tests/test_api_clients.py -v

# Run with coverage
pytest tests/test_api_clients.py --cov=src.api_clients --cov-report=html
```

### Mock Testing

```python
import pytest
from unittest.mock import patch
from src.api_clients import CCXTGatewayClient

@pytest.mark.asyncio
async def test_get_market_data():
    client = CCXTGatewayClient()
    
    with patch.object(client, 'get') as mock_get:
        mock_get.return_value = APIResponse(200, sample_data, {}, True)
        
        result = await client.get_market_data('BTC/USDT')
        assert len(result) > 0
```

## Examples

See `examples/api_client_examples.py` for comprehensive usage examples:

```bash
# Run examples (configure API keys first)
python examples/api_client_examples.py
```

## Best Practices

1. **Use context managers** for automatic resource cleanup
2. **Handle exceptions** appropriately for your use case
3. **Configure rate limits** based on exchange requirements
4. **Use caching** to reduce API calls and improve performance
5. **Monitor health** of external services
6. **Secure API keys** using environment variables
7. **Test with paper trading** before live trading

## Troubleshooting

### Common Issues

1. **Connection timeouts**
   - Check network connectivity
   - Verify service URLs
   - Increase timeout values

2. **Authentication errors**
   - Verify API credentials
   - Check exchange account status
   - Ensure proper permissions

3. **Rate limiting**
   - Reduce request frequency
   - Implement proper delays
   - Use caching effectively

4. **Chart generation failures**
   - Check quickchart service status
   - Verify chart configuration
   - Ensure data is properly formatted

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# API calls will now show detailed debug information
```

## Support

For issues and questions:

1. Check the logs for detailed error information
2. Verify configuration and API keys
3. Test with simplified examples
4. Check external service status
5. Review error handling documentation