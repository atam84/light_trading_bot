# src/api_clients/__init__.py

"""
API Clients Module

This module provides clients for external API services:
- ccxt-gateway: Trading operations and market data
- quickchart: Chart generation and visualization
"""

from typing import Optional, Dict, Any
import logging
import asyncio
from contextlib import asynccontextmanager

from .base_client import BaseHTTPClient, APIResponse, HTTPMethod
from .ccxt_gateway import (
    CCXTGatewayClient, 
    MarketData, 
    TickerData, 
    BalanceInfo, 
    OrderInfo, 
    TradeInfo
)
from .quickchart import (
    QuickChartClient, 
    ChartConfig, 
    CandlestickPoint, 
    LinePoint, 
    TradeMarker
)
from ..config.settings import get_config
from ..utils.exceptions import APIError, TradingError, ChartError

logger = logging.getLogger(__name__)

class APIClientManager:
    """
    Centralized manager for all API clients
    
    Provides unified access to ccxt-gateway and quickchart clients
    with connection management and error handling.
    """
    
    def __init__(self):
        self._ccxt_client: Optional[CCXTGatewayClient] = None
        self._chart_client: Optional[QuickChartClient] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize all API clients"""
        if self._initialized:
            return
        
        try:
            config = get_config()
            
            # Initialize ccxt-gateway client
            self._ccxt_client = CCXTGatewayClient(
                base_url=config.get('api.ccxt_gateway_url')
            )
            
            # Initialize quickchart client
            self._chart_client = QuickChartClient(
                base_url=config.get('api.quickchart_url')
            )
            
            self._initialized = True
            logger.info("API clients initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize API clients: {str(e)}")
            raise APIError(f"API client initialization failed: {str(e)}")
    
    async def close(self) -> None:
        """Close all API client connections"""
        if self._ccxt_client:
            await self._ccxt_client.close()
            self._ccxt_client = None
        
        if self._chart_client:
            await self._chart_client.close()
            self._chart_client = None
        
        self._initialized = False
        logger.info("API clients closed")
    
    @property
    def ccxt(self) -> CCXTGatewayClient:
        """Get ccxt-gateway client"""
        if not self._initialized or not self._ccxt_client:
            raise RuntimeError("API clients not initialized. Call initialize() first.")
        return self._ccxt_client
    
    @property
    def charts(self) -> QuickChartClient:
        """Get quickchart client"""
        if not self._initialized or not self._chart_client:
            raise RuntimeError("API clients not initialized. Call initialize() first.")
        return self._chart_client
    
    async def health_check(self) -> Dict[str, bool]:
        """
        Check health of all API services
        
        Returns:
            Dictionary with service name -> health status
        """
        if not self._initialized:
            await self.initialize()
        
        results = {}
        
        # Check ccxt-gateway health
        try:
            results['ccxt_gateway'] = await self._ccxt_client.health_check()
        except Exception as e:
            logger.error(f"ccxt-gateway health check failed: {str(e)}")
            results['ccxt_gateway'] = False
        
        # Check quickchart health
        try:
            results['quickchart'] = await self._chart_client.health_check()
        except Exception as e:
            logger.error(f"quickchart health check failed: {str(e)}")
            results['quickchart'] = False
        
        return results
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

# Global API client manager instance
_api_manager: Optional[APIClientManager] = None

def get_api_manager() -> APIClientManager:
    """Get global API client manager instance"""
    global _api_manager
    if _api_manager is None:
        _api_manager = APIClientManager()
    return _api_manager

@asynccontextmanager
async def api_clients():
    """
    Async context manager for API clients
    
    Usage:
        async with api_clients() as api:
            market_data = await api.ccxt.get_market_data('BTC/USDT')
            chart = await api.charts.create_candlestick_chart(market_data)
    """
    manager = get_api_manager()
    async with manager:
        yield manager

# Convenience functions for common operations
async def get_market_data(
    symbol: str,
    interval: str = '1h',
    limit: int = 150,
    exchange: Optional[str] = None
) -> List[MarketData]:
    """
    Convenience function to get market data
    
    Args:
        symbol: Trading pair symbol (e.g., 'BTC/USDT')
        interval: Timeframe (1m, 5m, 15m, 30m, 1h, 4h, 8h, 1d, 1w)
        limit: Number of candles to retrieve
        exchange: Exchange name (optional)
    
    Returns:
        List of MarketData objects
    """
    async with api_clients() as api:
        return await api.ccxt.get_market_data(symbol, interval, limit, exchange)

async def get_account_balance(
    exchange: str,
    api_key: str,
    api_secret: str,
    passphrase: Optional[str] = None
) -> Dict[str, BalanceInfo]:
    """
    Convenience function to get account balance
    
    Args:
        exchange: Exchange name
        api_key: Exchange API key
        api_secret: Exchange API secret
        passphrase: Exchange passphrase (optional)
    
    Returns:
        Dictionary of currency -> BalanceInfo
    """
    async with api_clients() as api:
        return await api.ccxt.get_balance(exchange, api_key, api_secret, passphrase)

async def place_trade_order(
    exchange: str,
    api_key: str,
    api_secret: str,
    symbol: str,
    side: str,
    order_type: str,
    amount: float,
    price: Optional[float] = None,
    passphrase: Optional[str] = None
) -> OrderInfo:
    """
    Convenience function to place a trade order
    
    Args:
        exchange: Exchange name
        api_key: Exchange API key
        api_secret: Exchange API secret
        symbol: Trading pair symbol
        side: Order side ('buy' or 'sell')
        order_type: Order type ('market', 'limit')
        amount: Order amount
        price: Order price (required for limit orders)
        passphrase: Exchange passphrase (optional)
    
    Returns:
        OrderInfo object
    """
    async with api_clients() as api:
        return await api.ccxt.place_order(
            exchange, api_key, api_secret, symbol, side, order_type, amount, price, passphrase
        )

async def create_price_chart(
    market_data: List[MarketData],
    title: Optional[str] = None,
    trade_markers: Optional[List[TradeMarker]] = None,
    width: int = 800,
    height: int = 400,
    color_scheme: str = 'default'
) -> bytes:
    """
    Convenience function to create a price chart
    
    Args:
        market_data: List of MarketData objects
        title: Chart title (optional)
        trade_markers: Trade markers to overlay (optional)
        width: Chart width in pixels
        height: Chart height in pixels
        color_scheme: Color scheme ('default' or 'dark')
    
    Returns:
        Chart image as bytes
    """
    async with api_clients() as api:
        config = ChartConfig(
            chart_type='candlestick',
            width=width,
            height=height,
            title=title
        )
        return await api.charts.create_candlestick_chart(
            market_data, config, trade_markers, color_scheme
        )

# Export all important classes and functions
__all__ = [
    # Base classes
    'BaseHTTPClient',
    'APIResponse',
    'HTTPMethod',
    
    # ccxt-gateway client
    'CCXTGatewayClient',
    'MarketData',
    'TickerData',
    'BalanceInfo',
    'OrderInfo',
    'TradeInfo',
    
    # quickchart client
    'QuickChartClient',
    'ChartConfig',
    'CandlestickPoint',
    'LinePoint',
    'TradeMarker',
    
    # Manager and utilities
    'APIClientManager',
    'get_api_manager',
    'api_clients',
    
    # Convenience functions
    'get_market_data',
    'get_account_balance',
    'place_trade_order',
    'create_price_chart',
    
    # Exceptions
    'APIError',
    'TradingError',
    'ChartError'
]