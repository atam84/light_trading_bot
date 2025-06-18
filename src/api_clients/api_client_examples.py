# examples/api_client_examples.py

"""
API Client Usage Examples

This file demonstrates how to use the API clients for various trading operations.
"""

import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta

from src.api_clients import (
    api_clients,
    get_market_data,
    get_account_balance,
    place_trade_order,
    create_price_chart,
    MarketData,
    TradeMarker,
    ChartConfig
)
from src.utils.exceptions import TradingError, ChartError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Example exchange credentials (use environment variables in production)
EXCHANGE_CONFIG = {
    'exchange': 'kucoin',
    'api_key': 'your_api_key_here',
    'api_secret': 'your_api_secret_here',
    'passphrase': 'your_passphrase_here'  # Required for KuCoin
}

async def example_get_market_data():
    """Example: Get market data for BTC/USDT"""
    print("\n=== Getting Market Data ===")
    
    try:
        # Get 1-hour candlestick data
        market_data = await get_market_data(
            symbol='BTC/USDT',
            interval='1h',
            limit=50
        )
        
        print(f"Retrieved {len(market_data)} candles")
        if market_data:
            latest = market_data[-1]
            print(f"Latest candle: Open={latest.open}, High={latest.high}, "
                  f"Low={latest.low}, Close={latest.close}, Volume={latest.volume}")
        
        return market_data
        
    except Exception as e:
        logger.error(f"Failed to get market data: {e}")
        return []

async def example_get_account_info():
    """Example: Get account balance and assets"""
    print("\n=== Getting Account Information ===")
    
    try:
        # Get account balance
        balances = await get_account_balance(
            exchange=EXCHANGE_CONFIG['exchange'],
            api_key=EXCHANGE_CONFIG['api_key'],
            api_secret=EXCHANGE_CONFIG['api_secret'],
            passphrase=EXCHANGE_CONFIG.get('passphrase')
        )
        
        print("Account Balances:")
        for currency, balance in balances.items():
            if balance.total > 0:  # Only show non-zero balances
                print(f"  {currency}: Free={balance.free}, Used={balance.used}, Total={balance.total}")
        
        return balances
        
    except Exception as e:
        logger.error(f"Failed to get account info: {e}")
        return {}

async def example_get_current_price():
    """Example: Get current ticker price"""
    print("\n=== Getting Current Price ===")
    
    try:
        async with api_clients() as api:
            ticker = await api.ccxt.get_ticker('BTC/USDT')
            print(f"BTC/USDT Current Price: ${ticker.last:,.2f}")
            print(f"Bid: ${ticker.bid:,.2f}, Ask: ${ticker.ask:,.2f}")
            print(f"24h Volume: {ticker.volume:,.2f}")
            
            return ticker
            
    except Exception as e:
        logger.error(f"Failed to get current price: {e}")
        return None

async def example_get_rsi_indicator():
    """Example: Get RSI indicator"""
    print("\n=== Getting RSI Indicator ===")
    
    try:
        async with api_clients() as api:
            rsi = await api.ccxt.get_rsi(
                symbol='BTC/USDT',
                period=14,
                interval='1h'
            )
            print(f"BTC/USDT RSI(14): {rsi:.2f}")
            
            # Interpret RSI
            if rsi > 70:
                print("  📈 Potentially overbought")
            elif rsi < 30:
                print("  📉 Potentially oversold")
            else:
                print("  ⚖️ Neutral zone")
            
            return rsi
            
    except Exception as e:
        logger.error(f"Failed to get RSI: {e}")
        return None

async def example_place_orders():
    """Example: Place trading orders (paper trading recommended)"""
    print("\n=== Placing Orders (DEMO) ===")
    
    try:
        # Note: This is for demonstration - use paper trading first!
        print("⚠️  This would place real orders. Use paper trading for testing.")
        
        # Example market buy order
        """
        buy_order = await place_trade_order(
            exchange=EXCHANGE_CONFIG['exchange'],
            api_key=EXCHANGE_CONFIG['api_key'],
            api_secret=EXCHANGE_CONFIG['api_secret'],
            symbol='BTC/USDT',
            side='buy',
            order_type='market',
            amount=0.001,  # 0.001 BTC
            passphrase=EXCHANGE_CONFIG.get('passphrase')
        )
        print(f"Buy order placed: {buy_order.id}")
        """
        
        # Example limit sell order
        """
        sell_order = await place_trade_order(
            exchange=EXCHANGE_CONFIG['exchange'],
            api_key=EXCHANGE_CONFIG['api_key'],
            api_secret=EXCHANGE_CONFIG['api_secret'],
            symbol='BTC/USDT',
            side='sell',
            order_type='limit',
            amount=0.001,
            price=50000.0,  # Sell at $50k
            passphrase=EXCHANGE_CONFIG.get('passphrase')
        )
        print(f"Sell order placed: {sell_order.id}")
        """
        
        print("Order placement examples completed (not executed)")
        
    except Exception as e:
        logger.error(f"Failed to place orders: {e}")

async def example_get_order_history():
    """Example: Get order and trade history"""
    print("\n=== Getting Order History ===")
    
    try:
        async with api_clients() as api:
            # Get open orders
            open_orders = await api.ccxt.get_open_orders(
                exchange=EXCHANGE_CONFIG['exchange'],
                api_key=EXCHANGE_CONFIG['api_key'],
                api_secret=EXCHANGE_CONFIG['api_secret'],
                passphrase=EXCHANGE_CONFIG.get('passphrase')
            )
            print(f"Open orders: {len(open_orders)}")
            
            # Get order history
            order_history = await api.ccxt.get_order_history(
                exchange=EXCHANGE_CONFIG['exchange'],
                api_key=EXCHANGE_CONFIG['api_key'],
                api_secret=EXCHANGE_CONFIG['api_secret'],
                limit=10,
                passphrase=EXCHANGE_CONFIG.get('passphrase')
            )
            print(f"Recent orders: {len(order_history)}")
            
            for order in order_history[:3]:  # Show last 3 orders
                print(f"  Order {order.id}: {order.side} {order.amount} {order.symbol} "
                      f"at {order.price} - Status: {order.status}")
            
            return open_orders, order_history
            
    except Exception as e:
        logger.error(f"Failed to get order history: {e}")
        return [], []

async def example_create_charts(market_data: List[MarketData]):
    """Example: Create price charts"""
    print("\n=== Creating Charts ===")
    
    if not market_data:
        print("No market data available for charting")
        return
    
    try:
        # Create sample trade markers
        trade_markers = [
            TradeMarker(
                x=market_data[10].timestamp,
                y=market_data[10].low * 0.999,  # Slightly below low
                type='buy',
                amount=0.01,
                price=market_data[10].low * 0.999
            ),
            TradeMarker(
                x=market_data[20].timestamp,
                y=market_data[20].high * 1.001,  # Slightly above high
                type='sell',
                amount=0.01,
                price=market_data[20].high * 1.001
            )
        ]
        
        # Create candlestick chart with trade markers
        chart_bytes = await create_price_chart(
            market_data=market_data,
            title='BTC/USDT Price Chart with Trades',
            trade_markers=trade_markers,
            width=1200,
            height=600,
            color_scheme='default'
        )
        
        # Save chart to file
        chart_filename = f"btc_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        with open(chart_filename, 'wb') as f:
            f.write(chart_bytes)
        
        print(f"Chart saved to: {chart_filename}")
        print(f"Chart size: {len(chart_bytes)} bytes")
        
        # Create performance chart example
        async with api_clients() as api:
            # Create sample portfolio performance data
            portfolio_values = []
            initial_value = 10000
            
            for i, candle in enumerate(market_data):
                # Simulate portfolio performance (example only)
                performance = 1 + (i * 0.001)  # Small upward trend
                portfolio_values.append({
                    'x': candle.timestamp,
                    'y': initial_value * performance
                })
            
            # Create performance chart
            performance_config = ChartConfig(
                chart_type='line',
                title='Portfolio Performance',
                width=1000,
                height=400
            )
            
            performance_chart = await api.charts.create_performance_chart(
                portfolio_values=portfolio_values,
                config=performance_config
            )
            
            performance_filename = f"performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            with open(performance_filename, 'wb') as f:
                f.write(performance_chart)
            
            print(f"Performance chart saved to: {performance_filename}")
        
    except ChartError as e:
        logger.error(f"Chart creation failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in chart creation: {e}")

async def example_health_checks():
    """Example: Check API service health"""
    print("\n=== Health Checks ===")
    
    try:
        async with api_clients() as api:
            health = await api.health_check()
            
            print("Service Health Status:")
            for service, is_healthy in health.items():
                status = "✅ Healthy" if is_healthy else "❌ Unhealthy"
                print(f"  {service}: {status}")
            
            return health
            
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {}

async def example_error_handling():
    """Example: Error handling scenarios"""
    print("\n=== Error Handling Examples ===")
    
    # Example 1: Invalid symbol
    try:
        await get_market_data('INVALID/SYMBOL')
    except TradingError as e:
        print(f"✅ Caught trading error: {e}")
    
    # Example 2: Invalid API credentials
    try:
        await get_account_balance(
            exchange='kucoin',
            api_key='invalid_key',
            api_secret='invalid_secret'
        )
    except TradingError as e:
        print(f"✅ Caught authentication error: {e}")
    
    # Example 3: Rate limiting simulation
    print("✅ Rate limiting is handled automatically by the client")
    
    # Example 4: Network timeout handling
    print("✅ Network timeouts are handled with retries")

async def run_all_examples():
    """Run all API client examples"""
    print("🚀 API Client Integration Examples")
    print("=" * 50)
    
    try:
        # Check service health first
        health = await example_health_checks()
        if not all(health.values()):
            print("⚠️  Some services are unhealthy. Examples may fail.")
        
        # Market data examples
        market_data = await example_get_market_data()
        await example_get_current_price()
        await example_get_rsi_indicator()
        
        # Account examples (requires valid API keys)
        if EXCHANGE_CONFIG['api_key'] != 'your_api_key_here':
            await example_get_account_info()
            await example_get_order_history()
        else:
            print("⚠️  Skipping account examples - configure API keys first")
        
        # Order placement examples (demo only)
        await example_place_orders()
        
        # Chart creation examples
        if market_data:
            await example_create_charts(market_data)
        
        # Error handling examples
        await example_error_handling()
        
        print("\n✅ All examples completed successfully!")
        
    except Exception as e:
        logger.error(f"Example execution failed: {e}")
        print(f"\n❌ Examples failed: {e}")

if __name__ == "__main__":
    # Run examples
    asyncio.run(run_all_examples())