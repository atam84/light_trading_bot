# src/api_clients/ccxt_gateway.py

from typing import Dict, Any, Optional, List, Union
import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from .base_client import BaseHTTPClient, APIResponse
from ..utils.exceptions import TradingError, APIError
from ..config.settings import get_config

logger = logging.getLogger(__name__)

@dataclass
class MarketData:
    """Market data container"""
    symbol: str
    interval: str
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    datetime_str: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MarketData':
        return cls(
            symbol=data.get('symbol', ''),
            interval=data.get('interval', ''),
            timestamp=data.get('timestamp', 0),
            open=float(data.get('open', 0)),
            high=float(data.get('high', 0)),
            low=float(data.get('low', 0)),
            close=float(data.get('close', 0)),
            volume=float(data.get('volume', 0)),
            datetime_str=data.get('datetime')
        )

@dataclass
class TickerData:
    """Ticker data container"""
    symbol: str
    bid: float
    ask: float
    last: float
    volume: float
    timestamp: int
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TickerData':
        return cls(
            symbol=data.get('symbol', ''),
            bid=float(data.get('bid', 0)),
            ask=float(data.get('ask', 0)),
            last=float(data.get('last', 0)),
            volume=float(data.get('volume', 0)),
            timestamp=data.get('timestamp', 0)
        )

@dataclass
class BalanceInfo:
    """Balance information container"""
    currency: str
    free: float
    used: float
    total: float
    
    @classmethod
    def from_dict(cls, currency: str, data: Dict[str, Any]) -> 'BalanceInfo':
        return cls(
            currency=currency,
            free=float(data.get('free', 0)),
            used=float(data.get('used', 0)),
            total=float(data.get('total', 0))
        )

@dataclass
class OrderInfo:
    """Order information container"""
    id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    type: str  # 'market', 'limit', etc.
    amount: float
    price: Optional[float]
    filled: float
    remaining: float
    status: str  # 'open', 'closed', 'canceled', etc.
    timestamp: int
    fee: Optional[float] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OrderInfo':
        return cls(
            id=str(data.get('id', '')),
            symbol=data.get('symbol', ''),
            side=data.get('side', ''),
            type=data.get('type', ''),
            amount=float(data.get('amount', 0)),
            price=float(data['price']) if data.get('price') is not None else None,
            filled=float(data.get('filled', 0)),
            remaining=float(data.get('remaining', 0)),
            status=data.get('status', ''),
            timestamp=data.get('timestamp', 0),
            fee=float(data['fee']['cost']) if data.get('fee') and data['fee'].get('cost') else None
        )

@dataclass
class TradeInfo:
    """Trade information container"""
    id: str
    order_id: str
    symbol: str
    side: str
    amount: float
    price: float
    cost: float
    fee: Optional[float]
    timestamp: int
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradeInfo':
        return cls(
            id=str(data.get('id', '')),
            order_id=str(data.get('order', '')),
            symbol=data.get('symbol', ''),
            side=data.get('side', ''),
            amount=float(data.get('amount', 0)),
            price=float(data.get('price', 0)),
            cost=float(data.get('cost', 0)),
            fee=float(data['fee']['cost']) if data.get('fee') and data['fee'].get('cost') else None,
            timestamp=data.get('timestamp', 0)
        )

class CCXTGatewayClient(BaseHTTPClient):
    """Client for ccxt-gateway API integration"""
    
    def __init__(self, base_url: Optional[str] = None, **kwargs):
        config = get_config()
        if base_url is None:
            base_url = config.get('api.ccxt_gateway_url', 'http://ccxt-bridge:3000')
        
        super().__init__(
            base_url=base_url,
            timeout=config.get('api.timeout', 30),
            max_retries=config.get('api.max_retries', 3),
            rate_limit_requests=config.get('api.rate_limit_requests', 60),
            rate_limit_window=config.get('api.rate_limit_window', 60),
            **kwargs
        )
        
        self.supported_intervals = ['1m', '5m', '15m', '30m', '1h', '4h', '8h', '1d', '1w']
    
    def _get_auth_headers(
        self, 
        exchange: str, 
        api_key: Optional[str] = None, 
        api_secret: Optional[str] = None,
        passphrase: Optional[str] = None
    ) -> Dict[str, str]:
        """Get authentication headers for exchange API calls"""
        headers = {'X-EXCHANGE': exchange}
        
        if api_key:
            headers['X-API-KEY'] = api_key
        if api_secret:
            headers['X-API-SECRET'] = api_secret
        if passphrase:
            headers['X-API-PASSPHRASE'] = passphrase
        
        return headers
    
    # Market Data Methods
    async def get_market_data(
        self,
        symbol: str,
        interval: str = '1h',
        limit: int = 150,
        exchange: Optional[str] = None
    ) -> List[MarketData]:
        """
        Get historical market data (candlestick/OHLCV data)
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            interval: Timeframe (1m, 5m, 15m, 30m, 1h, 4h, 8h, 1d, 1w)
            limit: Number of candles to retrieve (max 150)
            exchange: Exchange name (optional for market data)
        
        Returns:
            List of MarketData objects
        """
        if interval not in self.supported_intervals:
            raise ValueError(f"Unsupported interval: {interval}. Supported: {self.supported_intervals}")
        
        if limit > 150:
            logger.warning(f"Limit {limit} exceeds maximum 150, using 150")
            limit = 150
        
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit,
            '_id': f"{symbol}-{interval}"
        }
        
        headers = {}
        if exchange:
            headers.update(self._get_auth_headers(exchange))
        
        try:
            response = await self.get('/marketdata', params=params, headers=headers, cache_ttl=60)
            
            if not response.is_success:
                raise APIError(f"Failed to get market data: {response.error_message}")
            
            # Handle different response formats
            data = response.data
            if isinstance(data, list):
                # Direct array of OHLCV data
                market_data = []
                for item in data:
                    if isinstance(item, dict):
                        market_data.append(MarketData.from_dict(item))
                return market_data
            elif isinstance(data, dict):
                # Response wrapped in object
                if 'data' in data:
                    candles = data['data']
                else:
                    # Assume the dict contains market data directly
                    candles = [data]
                
                market_data = []
                for candle in candles:
                    if isinstance(candle, dict):
                        market_data.append(MarketData.from_dict(candle))
                return market_data
            else:
                raise APIError(f"Unexpected market data format: {type(data)}")
                
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {str(e)}")
            raise TradingError(f"Failed to get market data: {str(e)}")
    
    async def get_ticker(self, symbol: str, exchange: Optional[str] = None) -> TickerData:
        """
        Get current ticker information
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            exchange: Exchange name (optional)
        
        Returns:
            TickerData object
        """
        params = {'symbol': symbol}
        headers = {}
        if exchange:
            headers.update(self._get_auth_headers(exchange))
        
        try:
            response = await self.get('/ticker', params=params, headers=headers, cache_ttl=10)
            
            if not response.is_success:
                raise APIError(f"Failed to get ticker: {response.error_message}")
            
            return TickerData.from_dict(response.data)
            
        except Exception as e:
            logger.error(f"Error getting ticker for {symbol}: {str(e)}")
            raise TradingError(f"Failed to get ticker: {str(e)}")
    
    async def get_rsi(
        self,
        symbol: str,
        period: int = 14,
        interval: str = '1h',
        exchange: Optional[str] = None
    ) -> float:
        """
        Get RSI (Relative Strength Index) indicator
        
        Args:
            symbol: Trading pair symbol
            period: RSI period (default 14)
            interval: Timeframe
            exchange: Exchange name (optional)
        
        Returns:
            Current RSI value
        """
        params = {
            'symbol': symbol,
            'period': period,
            'interval': interval
        }
        
        headers = {}
        if exchange:
            headers.update(self._get_auth_headers(exchange))
        
        try:
            response = await self.get('/indicators/rsi', params=params, headers=headers, cache_ttl=60)
            
            if not response.is_success:
                raise APIError(f"Failed to get RSI: {response.error_message}")
            
            # Handle different response formats
            data = response.data
            if isinstance(data, dict):
                return float(data.get('rsi', data.get('value', 0)))
            elif isinstance(data, (int, float)):
                return float(data)
            else:
                raise APIError(f"Unexpected RSI response format: {type(data)}")
                
        except Exception as e:
            logger.error(f"Error getting RSI for {symbol}: {str(e)}")
            raise TradingError(f"Failed to get RSI: {str(e)}")
    
    # Account Management Methods
    async def get_balance(
        self,
        exchange: str,
        api_key: str,
        api_secret: str,
        passphrase: Optional[str] = None
    ) -> Dict[str, BalanceInfo]:
        """
        Get account balance information
        
        Args:
            exchange: Exchange name (e.g., 'kucoin', 'binance')
            api_key: Exchange API key
            api_secret: Exchange API secret
            passphrase: Exchange passphrase (for some exchanges)
        
        Returns:
            Dictionary of currency -> BalanceInfo
        """
        headers = self._get_auth_headers(exchange, api_key, api_secret, passphrase)
        
        try:
            response = await self.get('/balance', headers=headers, use_cache=False)
            
            if not response.is_success:
                raise APIError(f"Failed to get balance: {response.error_message}")
            
            balances = {}
            for currency, balance_data in response.data.items():
                if isinstance(balance_data, dict):
                    balances[currency] = BalanceInfo.from_dict(currency, balance_data)
            
            return balances
            
        except Exception as e:
            logger.error(f"Error getting balance for {exchange}: {str(e)}")
            raise TradingError(f"Failed to get balance: {str(e)}")
    
    async def get_assets(
        self,
        exchange: str,
        api_key: str,
        api_secret: str,
        passphrase: Optional[str] = None
    ) -> List[str]:
        """
        Get available trading assets
        
        Args:
            exchange: Exchange name
            api_key: Exchange API key
            api_secret: Exchange API secret
            passphrase: Exchange passphrase (optional)
        
        Returns:
            List of available asset symbols
        """
        headers = self._get_auth_headers(exchange, api_key, api_secret, passphrase)
        
        try:
            response = await self.get('/assets', headers=headers, cache_ttl=300)
            
            if not response.is_success:
                raise APIError(f"Failed to get assets: {response.error_message}")
            
            if isinstance(response.data, list):
                return response.data
            elif isinstance(response.data, dict):
                return list(response.data.keys())
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error getting assets for {exchange}: {str(e)}")
            raise TradingError(f"Failed to get assets: {str(e)}")
    
    # Trading Methods
    async def place_order(
        self,
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
        Place a trading order
        
        Args:
            exchange: Exchange name
            api_key: Exchange API key
            api_secret: Exchange API secret
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            side: Order side ('buy' or 'sell')
            order_type: Order type ('market', 'limit')
            amount: Order amount
            price: Order price (required for limit orders)
            passphrase: Exchange passphrase (optional)
        
        Returns:
            OrderInfo object with order details
        """
        if side not in ['buy', 'sell']:
            raise ValueError(f"Invalid side: {side}. Must be 'buy' or 'sell'")
        
        if order_type not in ['market', 'limit']:
            raise ValueError(f"Invalid order type: {order_type}. Must be 'market' or 'limit'")
        
        if order_type == 'limit' and price is None:
            raise ValueError("Price is required for limit orders")
        
        headers = self._get_auth_headers(exchange, api_key, api_secret, passphrase)
        
        order_data = {
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'amount': amount
        }
        
        if price is not None:
            order_data['price'] = price
        
        try:
            response = await self.post('/trade', data=order_data, headers=headers)
            
            if not response.is_success:
                raise APIError(f"Failed to place order: {response.error_message}")
            
            return OrderInfo.from_dict(response.data)
            
        except Exception as e:
            logger.error(f"Error placing order: {str(e)}")
            raise TradingError(f"Failed to place order: {str(e)}")
    
    async def get_open_orders(
        self,
        exchange: str,
        api_key: str,
        api_secret: str,
        symbol: Optional[str] = None,
        passphrase: Optional[str] = None
    ) -> List[OrderInfo]:
        """
        Get open orders
        
        Args:
            exchange: Exchange name
            api_key: Exchange API key
            api_secret: Exchange API secret
            symbol: Trading pair symbol (optional, get all if None)
            passphrase: Exchange passphrase (optional)
        
        Returns:
            List of OrderInfo objects
        """
        headers = self._get_auth_headers(exchange, api_key, api_secret, passphrase)
        params = {}
        if symbol:
            params['symbol'] = symbol
        
        try:
            response = await self.get('/orders', params=params, headers=headers, use_cache=False)
            
            if not response.is_success:
                raise APIError(f"Failed to get open orders: {response.error_message}")
            
            orders = []
            for order_data in response.data:
                orders.append(OrderInfo.from_dict(order_data))
            
            return orders
            
        except Exception as e:
            logger.error(f"Error getting open orders: {str(e)}")
            raise TradingError(f"Failed to get open orders: {str(e)}")
    
    async def get_order_history(
        self,
        exchange: str,
        api_key: str,
        api_secret: str,
        symbol: Optional[str] = None,
        limit: int = 100,
        passphrase: Optional[str] = None
    ) -> List[OrderInfo]:
        """
        Get order history
        
        Args:
            exchange: Exchange name
            api_key: Exchange API key
            api_secret: Exchange API secret
            symbol: Trading pair symbol (optional)
            limit: Maximum number of orders to retrieve
            passphrase: Exchange passphrase (optional)
        
        Returns:
            List of OrderInfo objects
        """
        headers = self._get_auth_headers(exchange, api_key, api_secret, passphrase)
        params = {'limit': limit}
        if symbol:
            params['symbol'] = symbol
        
        try:
            response = await self.get('/orders/history', params=params, headers=headers, cache_ttl=60)
            
            if not response.is_success:
                raise APIError(f"Failed to get order history: {response.error_message}")
            
            orders = []
            for order_data in response.data:
                orders.append(OrderInfo.from_dict(order_data))
            
            return orders
            
        except Exception as e:
            logger.error(f"Error getting order history: {str(e)}")
            raise TradingError(f"Failed to get order history: {str(e)}")
    
    async def get_trade_history(
        self,
        exchange: str,
        api_key: str,
        api_secret: str,
        symbol: Optional[str] = None,
        limit: int = 100,
        passphrase: Optional[str] = None
    ) -> List[TradeInfo]:
        """
        Get trade history
        
        Args:
            exchange: Exchange name
            api_key: Exchange API key
            api_secret: Exchange API secret
            symbol: Trading pair symbol (optional)
            limit: Maximum number of trades to retrieve
            passphrase: Exchange passphrase (optional)
        
        Returns:
            List of TradeInfo objects
        """
        headers = self._get_auth_headers(exchange, api_key, api_secret, passphrase)
        params = {'limit': limit}
        if symbol:
            params['symbol'] = symbol
        
        try:
            response = await self.get('/trades/history', params=params, headers=headers, cache_ttl=60)
            
            if not response.is_success:
                raise APIError(f"Failed to get trade history: {response.error_message}")
            
            trades = []
            for trade_data in response.data:
                trades.append(TradeInfo.from_dict(trade_data))
            
            return trades
            
        except Exception as e:
            logger.error(f"Error getting trade history: {str(e)}")
            raise TradingError(f"Failed to get trade history: {str(e)}")
    
    # Utility Methods
    async def get_logs(
        self,
        exchange: str,
        api_key: str,
        api_secret: str,
        limit: int = 100,
        passphrase: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get exchange API logs
        
        Args:
            exchange: Exchange name
            api_key: Exchange API key
            api_secret: Exchange API secret
            limit: Maximum number of log entries
            passphrase: Exchange passphrase (optional)
        
        Returns:
            List of log entries
        """
        headers = self._get_auth_headers(exchange, api_key, api_secret, passphrase)
        params = {'limit': limit}
        
        try:
            response = await self.get('/logs', params=params, headers=headers, use_cache=False)
            
            if not response.is_success:
                raise APIError(f"Failed to get logs: {response.error_message}")
            
            return response.data if isinstance(response.data, list) else []
            
        except Exception as e:
            logger.error(f"Error getting logs: {str(e)}")
            raise TradingError(f"Failed to get logs: {str(e)}")
    
    def validate_symbol_format(self, symbol: str) -> str:
        """
        Validate and normalize symbol format
        
        Args:
            symbol: Trading pair symbol
        
        Returns:
            Normalized symbol
        """
        # Convert common formats to standard format
        symbol = symbol.upper().replace('-', '/').replace('_', '/')
        
        # Basic validation
        if '/' not in symbol:
            raise ValueError(f"Invalid symbol format: {symbol}. Expected format: BASE/QUOTE")
        
        parts = symbol.split('/')
        if len(parts) != 2:
            raise ValueError(f"Invalid symbol format: {symbol}. Expected format: BASE/QUOTE")
        
        base, quote = parts
        if not base or not quote:
            raise ValueError(f"Invalid symbol format: {symbol}. Base and quote cannot be empty")
        
        return f"{base}/{quote}"
    
    async def health_check(self) -> bool:
        """
        Check if ccxt-gateway is healthy and responding
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try to get market data without authentication as a health check
            response = await self.get('/marketdata', params={
                'symbol': 'BTC/USDT',
                'interval': '1h',
                'limit': 1
            }, use_cache=False)
            
            return response.is_success
            
        except Exception as e:
            logger.error(f"ccxt-gateway health check failed: {str(e)}")
            return False