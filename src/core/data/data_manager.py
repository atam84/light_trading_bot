# src/core/data/data_manager.py

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import time
from collections import defaultdict, deque

class DataSourceType(Enum):
    """Data source types"""
    REAL_TIME = "real_time"
    HISTORICAL = "historical"
    CACHED = "cached"

class DataQuality(Enum):
    """Data quality levels"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"

@dataclass
class MarketDataPoint:
    """Single market data point"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    timeframe: str
    source: DataSourceType = DataSourceType.REAL_TIME
    quality: DataQuality = DataQuality.UNKNOWN
    
    # Technical indicators (populated by indicator calculator)
    indicators: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'timeframe': self.timeframe,
            'source': self.source.value,
            'quality': self.quality.value,
            'indicators': self.indicators
        }

@dataclass
class DataFeed:
    """Data feed configuration"""
    feed_id: str
    symbol: str
    timeframe: str
    source_url: str
    update_interval: int  # seconds
    enabled: bool = True
    last_update: Optional[datetime] = None
    error_count: int = 0
    max_errors: int = 5

@dataclass
class CacheEntry:
    """Cache entry for market data"""
    key: str
    data: List[MarketDataPoint]
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    ttl_seconds: int = 300  # 5 minutes default
    
    def is_expired(self) -> bool:
        return (datetime.utcnow() - self.created_at).total_seconds() > self.ttl_seconds
    
    def touch(self):
        self.last_accessed = datetime.utcnow()
        self.access_count += 1

class DataManager:
    """Comprehensive data management system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # API Configuration
        self.ccxt_gateway_url = config.get('ccxt_gateway_url', 'http://ccxt-bridge:3000')
        self.default_exchange = config.get('default_exchange', 'kucoin')
        self.request_timeout = config.get('request_timeout', 30)
        self.max_retries = config.get('max_retries', 3)
        
        # Cache configuration
        self.cache_enabled = config.get('cache_enabled', True)
        self.max_cache_size = config.get('max_cache_size', 1000)
        self.default_cache_ttl = config.get('default_cache_ttl', 300)  # 5 minutes
        
        # Data storage
        self._cache: Dict[str, CacheEntry] = {}
        self._data_feeds: Dict[str, DataFeed] = {}
        self._real_time_data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # HTTP session
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Background tasks
        self._feed_tasks: List[asyncio.Task] = []
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Statistics
        self._stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'api_errors': 0,
            'last_update': datetime.utcnow()
        }
        
        self.logger.info("Data manager initialized")
    
    async def initialize(self) -> bool:
        """Initialize data manager"""
        try:
            # Create HTTP session
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=20,
                ttl_dns_cache=300,
                use_dns_cache=True
            )
            
            timeout = aiohttp.ClientTimeout(total=self.request_timeout)
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={'Content-Type': 'application/json'}
            )
            
            # Test API connection
            if not await self._test_api_connection():
                raise Exception("Failed to connect to ccxt-gateway")
            
            # Start background tasks
            await self._start_background_tasks()
            
            self._running = True
            self.logger.info("Data manager initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize data manager: {e}")
            return False
    
    async def _test_api_connection(self) -> bool:
        """Test API connection"""
        try:
            url = f"{self.ccxt_gateway_url}/ticker"
            params = {'symbol': 'BTC/USDT'}
            
            async with self._session.get(url, params=params) as response:
                if response.status == 200:
                    self.logger.info("API connection test successful")
                    return True
                else:
                    self.logger.error(f"API connection test failed: {response.status}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"API connection test error: {e}")
            return False
    
    async def _start_background_tasks(self):
        """Start background tasks"""
        # Cache cleanup task
        self._cleanup_task = asyncio.create_task(self._cache_cleanup_loop())
        
        self.logger.info("Background tasks started")
    
    async def _cache_cleanup_loop(self):
        """Cache cleanup background loop"""
        while self._running:
            try:
                await self._cleanup_cache()
                await asyncio.sleep(300)  # Clean every 5 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cache cleanup: {e}")
                await asyncio.sleep(60)
    
    # Market Data API Methods
    async def get_historical_data(self, symbol: str, timeframe: str, 
                                limit: int = 150, 
                                exchange: Optional[str] = None) -> List[MarketDataPoint]:
        """Get historical market data"""
        try:
            # Check cache first
            cache_key = f"hist_{symbol}_{timeframe}_{limit}"
            
            if self.cache_enabled:
                cached_data = self._get_from_cache(cache_key)
                if cached_data:
                    self._stats['cache_hits'] += 1
                    return cached_data
                self._stats['cache_misses'] += 1
            
            # Fetch from API
            url = f"{self.ccxt_gateway_url}/marketdata"
            params = {
                'symbol': symbol,
                'interval': timeframe,
                'limit': limit
            }
            
            headers = {}
            if exchange:
                headers['X-EXCHANGE'] = exchange
            else:
                headers['X-EXCHANGE'] = self.default_exchange
            
            self._stats['total_requests'] += 1
            
            async with self._session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Process response
                    market_data = self._process_historical_response(data, symbol, timeframe)
                    
                    # Cache the data
                    if self.cache_enabled and market_data:
                        self._add_to_cache(cache_key, market_data, ttl_seconds=300)
                    
                    self.logger.debug(f"Retrieved {len(market_data)} historical data points for {symbol}")
                    return market_data
                    
                else:
                    self._stats['api_errors'] += 1
                    error_text = await response.text()
                    raise Exception(f"API request failed: {response.status} - {error_text}")
                    
        except Exception as e:
            self.logger.error(f"Failed to get historical data for {symbol}: {e}")
            return []
    
    def _process_historical_response(self, data: Any, symbol: str, timeframe: str) -> List[MarketDataPoint]:
        """Process historical data response from API"""
        try:
            market_data = []
            
            # Handle different response formats
            if isinstance(data, list) and len(data) > 0:
                # Handle list response (ccxt-gateway format)
                raw_data = data
            elif isinstance(data, dict):
                # Handle dictionary response with data array
                raw_data = data.get('data', [])
                if not raw_data and 'candles' in data:
                    raw_data = data['candles']
            else:
                self.logger.warning(f"Unexpected response format: {type(data)}")
                return []
            
            for item in raw_data:
                try:
                    # Handle different data formats
                    if isinstance(item, dict):
                        # Dictionary format
                        point = MarketDataPoint(
                            symbol=symbol,
                            timestamp=self._parse_timestamp(item.get('timestamp', item.get('datetime'))),
                            open=float(item.get('open', 0)),
                            high=float(item.get('high', 0)),
                            low=float(item.get('low', 0)),
                            close=float(item.get('close', 0)),
                            volume=float(item.get('volume', 0)),
                            timeframe=timeframe,
                            source=DataSourceType.HISTORICAL,
                            quality=DataQuality.HIGH
                        )
                        
                        # Add indicators if available
                        if 'indicators' in item:
                            point.indicators = item['indicators']
                        
                        # Add individual indicators
                        for indicator in ['rsi6', 'rsi14', 'rsi24', 'ema12', 'ema26', 'macd', 'macdSignal', 'macdHist']:
                            if indicator in item:
                                point.indicators[indicator] = float(item[indicator])
                        
                    elif isinstance(item, list) and len(item) >= 6:
                        # Array format [timestamp, open, high, low, close, volume]
                        point = MarketDataPoint(
                            symbol=symbol,
                            timestamp=self._parse_timestamp(item[0]),
                            open=float(item[1]),
                            high=float(item[2]),
                            low=float(item[3]),
                            close=float(item[4]),
                            volume=float(item[5]),
                            timeframe=timeframe,
                            source=DataSourceType.HISTORICAL,
                            quality=DataQuality.HIGH
                        )
                    else:
                        continue
                    
                    market_data.append(point)
                    
                except (ValueError, KeyError, TypeError) as e:
                    self.logger.warning(f"Error processing data point: {e}")
                    continue
            
            return sorted(market_data, key=lambda x: x.timestamp)
            
        except Exception as e:
            self.logger.error(f"Error processing historical response: {e}")
            return []
    
    def _parse_timestamp(self, timestamp_value: Any) -> datetime:
        """Parse timestamp from various formats"""
        try:
            if isinstance(timestamp_value, (int, float)):
                # Unix timestamp (milliseconds or seconds)
                if timestamp_value > 1e12:  # Milliseconds
                    return datetime.fromtimestamp(timestamp_value / 1000)
                else:  # Seconds
                    return datetime.fromtimestamp(timestamp_value)
            elif isinstance(timestamp_value, str):
                # ISO format string
                return datetime.fromisoformat(timestamp_value.replace('Z', '+00:00'))
            else:
                # Default to current time
                return datetime.utcnow()
        except Exception:
            return datetime.utcnow()
    
    async def get_ticker(self, symbol: str, exchange: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get current ticker data"""
        try:
            url = f"{self.ccxt_gateway_url}/ticker"
            params = {'symbol': symbol}
            
            headers = {}
            if exchange:
                headers['X-EXCHANGE'] = exchange
            else:
                headers['X-EXCHANGE'] = self.default_exchange
            
            self._stats['total_requests'] += 1
            
            async with self._session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    self._stats['api_errors'] += 1
                    return None
                    
        except Exception as e:
            self.logger.error(f"Failed to get ticker for {symbol}: {e}")
            return None
    
    async def get_indicators(self, symbol: str, indicator: str, 
                           period: int = 14, timeframe: str = "1h") -> Optional[float]:
        """Get technical indicator value"""
        try:
            url = f"{self.ccxt_gateway_url}/indicators/{indicator}"
            params = {
                'symbol': symbol,
                'period': period,
                'timeframe': timeframe
            }
            
            headers = {'X-EXCHANGE': self.default_exchange}
            
            self._stats['total_requests'] += 1
            
            async with self._session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('value')
                else:
                    self._stats['api_errors'] += 1
                    return None
                    
        except Exception as e:
            self.logger.error(f"Failed to get {indicator} for {symbol}: {e}")
            return None
    
    # Data Feed Management
    def add_data_feed(self, symbol: str, timeframe: str, update_interval: int = 60) -> str:
        """Add real-time data feed"""
        feed_id = f"{symbol}_{timeframe}"
        
        feed = DataFeed(
            feed_id=feed_id,
            symbol=symbol,
            timeframe=timeframe,
            source_url=f"{self.ccxt_gateway_url}/marketdata",
            update_interval=update_interval
        )
        
        self._data_feeds[feed_id] = feed
        
        # Start feed task
        if self._running:
            task = asyncio.create_task(self._feed_loop(feed))
            self._feed_tasks.append(task)
        
        self.logger.info(f"Added data feed: {feed_id}")
        return feed_id
    
    def remove_data_feed(self, feed_id: str) -> bool:
        """Remove data feed"""
        if feed_id in self._data_feeds:
            self._data_feeds[feed_id].enabled = False
            del self._data_feeds[feed_id]
            
            # Stop related tasks
            for i, task in enumerate(self._feed_tasks):
                if not task.done() and hasattr(task, 'feed_id') and task.feed_id == feed_id:
                    task.cancel()
                    self._feed_tasks.pop(i)
                    break
            
            self.logger.info(f"Removed data feed: {feed_id}")
            return True
        
        return False
    
    async def _feed_loop(self, feed: DataFeed):
        """Real-time data feed loop"""
        while self._running and feed.enabled:
            try:
                # Get latest data
                data = await self.get_historical_data(
                    symbol=feed.symbol,
                    timeframe=feed.timeframe,
                    limit=1
                )
                
                if data:
                    # Update real-time data
                    self._real_time_data[feed.feed_id].append(data[0])
                    feed.last_update = datetime.utcnow()
                    feed.error_count = 0
                else:
                    feed.error_count += 1
                
                # Check error threshold
                if feed.error_count >= feed.max_errors:
                    self.logger.error(f"Data feed {feed.feed_id} exceeded error threshold, disabling")
                    feed.enabled = False
                    break
                
                await asyncio.sleep(feed.update_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in data feed {feed.feed_id}: {e}")
                feed.error_count += 1
                await asyncio.sleep(60)  # Wait before retry
    
    def get_real_time_data(self, symbol: str, timeframe: str, limit: int = 100) -> List[MarketDataPoint]:
        """Get real-time data from feed"""
        feed_id = f"{symbol}_{timeframe}"
        
        if feed_id in self._real_time_data:
            data = list(self._real_time_data[feed_id])
            return data[-limit:] if limit > 0 else data
        
        return []
    
    # Cache Management
    def _get_cache_key(self, *args) -> str:
        """Generate cache key from arguments"""
        return "_".join(str(arg) for arg in args)
    
    def _get_from_cache(self, key: str) -> Optional[List[MarketDataPoint]]:
        """Get data from cache"""
        if key in self._cache:
            entry = self._cache[key]
            
            if not entry.is_expired():
                entry.touch()
                return entry.data.copy()
            else:
                # Remove expired entry
                del self._cache[key]
        
        return None
    
    def _add_to_cache(self, key: str, data: List[MarketDataPoint], ttl_seconds: Optional[int] = None):
        """Add data to cache"""
        if not self.cache_enabled:
            return
        
        # Check cache size limit
        if len(self._cache) >= self.max_cache_size:
            self._evict_cache_entries()
        
        ttl = ttl_seconds or self.default_cache_ttl
        
        entry = CacheEntry(
            key=key,
            data=data.copy(),
            created_at=datetime.utcnow(),
            last_accessed=datetime.utcnow(),
            ttl_seconds=ttl
        )
        
        self._cache[key] = entry
    
    def _evict_cache_entries(self):
        """Evict least recently used cache entries"""
        if not self._cache:
            return
        
        # Sort by last accessed time
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda x: x[1].last_accessed
        )
        
        # Remove oldest 25% of entries
        entries_to_remove = len(sorted_entries) // 4
        
        for i in range(entries_to_remove):
            key = sorted_entries[i][0]
            del self._cache[key]
        
        self.logger.debug(f"Evicted {entries_to_remove} cache entries")
    
    async def _cleanup_cache(self):
        """Clean up expired cache entries"""
        expired_keys = []
        
        for key, entry in self._cache.items():
            if entry.is_expired():
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            self.logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    # Data Validation and Quality
    def validate_data_point(self, data_point: MarketDataPoint) -> bool:
        """Validate market data point"""
        try:
            # Basic validation
            if data_point.high < data_point.low:
                return False
            
            if data_point.close < 0 or data_point.volume < 0:
                return False
            
            if not (data_point.low <= data_point.open <= data_point.high):
                return False
            
            if not (data_point.low <= data_point.close <= data_point.high):
                return False
            
            return True
            
        except Exception:
            return False
    
    def assess_data_quality(self, data_points: List[MarketDataPoint]) -> DataQuality:
        """Assess data quality of a dataset"""
        if not data_points:
            return DataQuality.UNKNOWN
        
        valid_points = sum(1 for point in data_points if self.validate_data_point(point))
        quality_ratio = valid_points / len(data_points)
        
        if quality_ratio >= 0.95:
            return DataQuality.HIGH
        elif quality_ratio >= 0.85:
            return DataQuality.MEDIUM
        else:
            return DataQuality.LOW
    
    # Statistics and Monitoring
    def get_statistics(self) -> Dict[str, Any]:
        """Get data manager statistics"""
        cache_size = len(self._cache)
        active_feeds = sum(1 for feed in self._data_feeds.values() if feed.enabled)
        
        self._stats['last_update'] = datetime.utcnow()
        
        return {
            'api_stats': self._stats.copy(),
            'cache_stats': {
                'size': cache_size,
                'max_size': self.max_cache_size,
                'hit_rate': (self._stats['cache_hits'] / 
                           (self._stats['cache_hits'] + self._stats['cache_misses']) * 100)
                           if (self._stats['cache_hits'] + self._stats['cache_misses']) > 0 else 0
            },
            'feed_stats': {
                'total_feeds': len(self._data_feeds),
                'active_feeds': active_feeds,
                'feed_tasks': len(self._feed_tasks)
            },
            'real_time_data_points': sum(len(data) for data in self._real_time_data.values())
        }
    
    def get_data_feeds_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all data feeds"""
        status = {}
        
        for feed_id, feed in self._data_feeds.items():
            status[feed_id] = {
                'symbol': feed.symbol,
                'timeframe': feed.timeframe,
                'enabled': feed.enabled,
                'last_update': feed.last_update.isoformat() if feed.last_update else None,
                'error_count': feed.error_count,
                'update_interval': feed.update_interval,
                'data_points': len(self._real_time_data.get(feed_id, []))
            }
        
        return status
    
    def is_healthy(self) -> bool:
        """Check if data manager is healthy"""
        return (
            self._running and
            self._session and not self._session.closed and
            self._stats['api_errors'] < 10  # Less than 10 errors since last reset
        )
    
    # Lifecycle
    async def process_cycle(self):
        """Process data manager cycle"""
        try:
            # Update statistics
            self._stats['last_update'] = datetime.utcnow()
            
            # Check feed health
            for feed in self._data_feeds.values():
                if feed.enabled and feed.last_update:
                    time_since_update = (datetime.utcnow() - feed.last_update).total_seconds()
                    if time_since_update > feed.update_interval * 3:  # 3x interval threshold
                        self.logger.warning(f"Data feed {feed.feed_id} appears stale")
            
        except Exception as e:
            self.logger.error(f"Error in data manager cycle: {e}")
    
    async def cleanup(self):
        """Cleanup data manager"""
        self._running = False
        
        # Cancel all feed tasks
        for task in self._feed_tasks:
            task.cancel()
        
        if self._feed_tasks:
            await asyncio.gather(*self._feed_tasks, return_exceptions=True)
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close HTTP session
        if self._session:
            await self._session.close()
        
        # Clear data structures
        self._cache.clear()
        self._data_feeds.clear()
        self._real_time_data.clear()
        self._feed_tasks.clear()
        
        self.logger.info("Data manager cleaned up")