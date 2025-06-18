# src/database/models/cache.py

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from pydantic import Field, validator
from enum import Enum
from src.database.models.base import BaseDBModel, BaseRepository, PyObjectId

class CacheType(str, Enum):
    """Cache data types"""
    CHART_DATA = "chart_data"
    TICKER_DATA = "ticker_data"
    BALANCE_DATA = "balance_data"
    INDICATOR_DATA = "indicator_data"
    MARKET_DATA = "market_data"
    API_RESPONSE = "api_response"

class ChartDataCache(BaseDBModel):
    """Chart data cache with TTL support"""
    
    # Cache identification
    symbol: str = Field(..., description="Trading pair symbol")
    interval: str = Field(..., description="Chart interval (1h, 4h, 1d, etc.)")
    exchange: str = Field(..., description="Exchange name")
    
    # Cache data
    data: List[Dict[str, Any]] = Field(..., description="OHLCV data with indicators")
    data_points: int = Field(..., description="Number of data points")
    
    # Metadata
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(..., description="Cache expiration time")
    data_source: str = Field(default="ccxt-gateway", description="Data source")
    
    # Quality metrics
    data_quality_score: float = Field(default=1.0, ge=0, le=1, description="Data quality score")
    missing_points: int = Field(default=0, description="Number of missing data points")
    
    @property
    def collection_name(self) -> str:
        return "chart_cache"
    
    @validator('symbol')
    def validate_symbol(cls, v):
        return v.upper()
    
    @validator('exchange')
    def validate_exchange(cls, v):
        return v.lower()
    
    @classmethod
    def create_cache_key(cls, symbol: str, interval: str, exchange: str) -> str:
        """Create unique cache key"""
        return f"{exchange.lower()}:{symbol.upper()}:{interval}"
    
    def is_expired(self) -> bool:
        """Check if cache is expired"""
        return datetime.now(timezone.utc) > self.expires_at
    
    def is_fresh(self, max_age_minutes: int = 5) -> bool:
        """Check if cache is fresh (not older than max_age_minutes)"""
        max_age = datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)
        return self.last_updated > max_age
    
    def get_cache_age_seconds(self) -> int:
        """Get cache age in seconds"""
        return int((datetime.now(timezone.utc) - self.last_updated).total_seconds())
    
    def extend_expiry(self, minutes: int = 5):
        """Extend cache expiry time"""
        self.expires_at = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    
    def get_latest_price(self) -> Optional[float]:
        """Get latest close price from cached data"""
        if not self.data:
            return None
        return self.data[-1].get('close')
    
    def get_price_range(self) -> Dict[str, float]:
        """Get price range from cached data"""
        if not self.data:
            return {"min": 0.0, "max": 0.0}
        
        prices = [point.get('close', 0) for point in self.data if point.get('close')]
        if not prices:
            return {"min": 0.0, "max": 0.0}
        
        return {"min": min(prices), "max": max(prices)}

class TickerCache(BaseDBModel):
    """Real-time ticker data cache"""
    
    symbol: str = Field(..., description="Trading pair symbol")
    exchange: str = Field(..., description="Exchange name")
    
    # Ticker data
    bid: Optional[float] = None
    ask: Optional[float] = None
    last: Optional[float] = None
    volume: Optional[float] = None
    volume_quote: Optional[float] = None
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None
    change_24h: Optional[float] = None
    change_24h_pct: Optional[float] = None
    
    # Timestamps
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(..., description="Cache expiration time")
    
    @property
    def collection_name(self) -> str:
        return "ticker_cache"
    
    @validator('symbol')
    def validate_symbol(cls, v):
        return v.upper()
    
    @validator('exchange')
    def validate_exchange(cls, v):
        return v.lower()
    
    def get_spread(self) -> Optional[float]:
        """Calculate bid-ask spread"""
        if self.bid and self.ask:
            return self.ask - self.bid
        return None
    
    def get_spread_pct(self) -> Optional[float]:
        """Calculate bid-ask spread percentage"""
        if self.bid and self.ask and self.bid > 0:
            return ((self.ask - self.bid) / self.bid) * 100
        return None

class BalanceCache(BaseDBModel):
    """Account balance cache"""
    
    user_id: PyObjectId = Field(..., description="User ID")
    exchange: str = Field(..., description="Exchange name")
    
    # Balance data
    balances: Dict[str, Dict[str, float]] = Field(default={}, description="Asset balances")
    total_balance_usd: float = Field(default=0.0, description="Total balance in USD")
    
    # Cache metadata
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(..., description="Cache expiration time")
    sync_status: str = Field(default="synced", description="Sync status with exchange")
    
    @property
    def collection_name(self) -> str:
        return "balance_cache"
    
    def get_asset_balance(self, asset: str) -> Dict[str, float]:
        """Get balance for specific asset"""
        return self.balances.get(asset.upper(), {'free': 0.0, 'used': 0.0, 'total': 0.0})
    
    def has_sufficient_balance(self, asset: str, amount: float) -> bool:
        """Check if there's sufficient free balance"""
        balance = self.get_asset_balance(asset)
        return balance.get('free', 0.0) >= amount

class IndicatorCache(BaseDBModel):
    """Technical indicator cache"""
    
    symbol: str = Field(..., description="Trading pair symbol")
    exchange: str = Field(..., description="Exchange name")
    timeframe: str = Field(..., description="Timeframe")
    indicator_type: str = Field(..., description="Indicator type (RSI, MACD, etc.)")
    
    # Indicator configuration
    params: Dict[str, Any] = Field(default={}, description="Indicator parameters")
    
    # Indicator values
    values: List[Dict[str, Any]] = Field(..., description="Indicator values with timestamps")
    latest_value: Optional[float] = Field(None, description="Latest indicator value")
    
    # Cache metadata
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(..., description="Cache expiration time")
    calculation_time: Optional[float] = Field(None, description="Calculation time in seconds")
    
    @property
    def collection_name(self) -> str:
        return "indicator_cache"
    
    @validator('symbol')
    def validate_symbol(cls, v):
        return v.upper()
    
    @validator('exchange')
    def validate_exchange(cls, v):
        return v.lower()
    
    def get_latest_values(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get latest N indicator values"""
        return self.values[-count:] if len(self.values) >= count else self.values

class APIResponseCache(BaseDBModel):
    """Generic API response cache"""
    
    cache_key: str = Field(..., description="Unique cache key")
    cache_type: CacheType = Field(..., description="Type of cached data")
    
    # Request details
    endpoint: str = Field(..., description="API endpoint")
    method: str = Field(default="GET", description="HTTP method")
    params: Dict[str, Any] = Field(default={}, description="Request parameters")
    headers: Dict[str, str] = Field(default={}, description="Request headers")
    
    # Response data
    response_data: Dict[str, Any] = Field(..., description="Cached response data")
    status_code: int = Field(..., description="HTTP status code")
    response_size: int = Field(..., description="Response size in bytes")
    
    # Cache metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(..., description="Cache expiration time")
    hit_count: int = Field(default=0, description="Number of cache hits")
    last_accessed: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def collection_name(self) -> str:
        return "api_response_cache"
    
    def increment_hit_count(self):
        """Increment cache hit count"""
        self.hit_count += 1
        self.last_accessed = datetime.now(timezone.utc)
    
    def is_expired(self) -> bool:
        """Check if cache is expired"""
        return datetime.now(timezone.utc) > self.expires_at

class ChartCacheRepository(BaseRepository[ChartDataCache]):
    """Repository for ChartDataCache operations"""
    
    def __init__(self):
        super().__init__(ChartDataCache)
    
    async def get_cached_data(self, symbol: str, interval: str, 
                            exchange: str = "kucoin") -> Optional[ChartDataCache]:
        """Get cached chart data"""
        return await self.get_one({
            "symbol": symbol.upper(),
            "interval": interval,
            "exchange": exchange.lower()
        })
    
    async def set_cached_data(self, symbol: str, interval: str, exchange: str,
                            data: List[Dict[str, Any]], ttl_minutes: int = 5) -> ChartDataCache:
        """Set cached chart data"""
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
        
        # Check for existing cache
        existing = await self.get_cached_data(symbol, interval, exchange)
        
        cache_data = {
            "symbol": symbol.upper(),
            "interval": interval,
            "exchange": exchange.lower(),
            "data": data,
            "data_points": len(data),
            "expires_at": expires_at,
            "last_updated": datetime.now(timezone.utc)
        }
        
        if existing:
            return await self.update(str(existing.id), cache_data)
        else:
            return await self.create(cache_data)
    
    async def get_fresh_data(self, symbol: str, interval: str, exchange: str,
                           max_age_minutes: int = 5) -> Optional[ChartDataCache]:
        """Get fresh cached data (not older than max_age_minutes)"""
        cached = await self.get_cached_data(symbol, interval, exchange)
        
        if cached and cached.is_fresh(max_age_minutes) and not cached.is_expired():
            return cached
        
        return None
    
    async def cleanup_expired(self) -> int:
        """Remove expired cache entries"""
        collection = await self.get_collection()
        result = await collection.delete_many({
            "expires_at": {"$lt": datetime.now(timezone.utc)}
        })
        return result.deleted_count
    
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache statistics"""
        collection = await self.get_collection()
        
        total_entries = await collection.count_documents({})
        expired_entries = await collection.count_documents({
            "expires_at": {"$lt": datetime.now(timezone.utc)}
        })
        
        # Get cache size distribution
        pipeline = [
            {"$group": {
                "_id": {"exchange": "$exchange", "interval": "$interval"},
                "count": {"$sum": 1},
                "avg_data_points": {"$avg": "$data_points"}
            }}
        ]
        
        distribution = await collection.aggregate(pipeline).to_list(length=100)
        
        return {
            "total_entries": total_entries,
            "expired_entries": expired_entries,
            "active_entries": total_entries - expired_entries,
            "distribution": distribution
        }

class TickerCacheRepository(BaseRepository[TickerCache]):
    """Repository for TickerCache operations"""
    
    def __init__(self):
        super().__init__(TickerCache)
    
    async def get_ticker(self, symbol: str, exchange: str = "kucoin") -> Optional[TickerCache]:
        """Get cached ticker data"""
        return await self.get_one({
            "symbol": symbol.upper(),
            "exchange": exchange.lower()
        })
    
    async def update_ticker(self, symbol: str, exchange: str, ticker_data: Dict[str, Any],
                          ttl_seconds: int = 30) -> TickerCache:
        """Update ticker cache"""
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        
        existing = await self.get_ticker(symbol, exchange)
        
        cache_data = {
            "symbol": symbol.upper(),
            "exchange": exchange.lower(),
            "expires_at": expires_at,
            "last_updated": datetime.now(timezone.utc),
            **ticker_data
        }
        
        if existing and not existing.is_expired():
            return await self.update(str(existing.id), cache_data)
        else:
            return await self.create(cache_data)

class BalanceCacheRepository(BaseRepository[BalanceCache]):
    """Repository for BalanceCache operations"""
    
    def __init__(self):
        super().__init__(BalanceCache)
    
    async def get_user_balance(self, user_id: str, exchange: str) -> Optional[BalanceCache]:
        """Get cached balance for user and exchange"""
        return await self.get_one({
            "user_id": PyObjectId(user_id),
            "exchange": exchange.lower()
        })
    
    async def update_balance(self, user_id: str, exchange: str, 
                           balances: Dict[str, Dict[str, float]],
                           total_balance_usd: float = 0.0,
                           ttl_minutes: int = 1) -> BalanceCache:
        """Update balance cache"""
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
        
        existing = await self.get_user_balance(user_id, exchange)
        
        cache_data = {
            "user_id": PyObjectId(user_id),
            "exchange": exchange.lower(),
            "balances": balances,
            "total_balance_usd": total_balance_usd,
            "expires_at": expires_at,
            "last_updated": datetime.now(timezone.utc),
            "sync_status": "synced"
        }
        
        if existing:
            return await self.update(str(existing.id), cache_data)
        else:
            return await self.create(cache_data)

class APIResponseCacheRepository(BaseRepository[APIResponseCache]):
    """Repository for APIResponseCache operations"""
    
    def __init__(self):
        super().__init__(APIResponseCache)
    
    async def get_cached_response(self, cache_key: str) -> Optional[APIResponseCache]:
        """Get cached API response"""
        cached = await self.get_one({"cache_key": cache_key})
        
        if cached and not cached.is_expired():
            # Increment hit count
            await self.update(str(cached.id), {
                "hit_count": cached.hit_count + 1,
                "last_accessed": datetime.now(timezone.utc)
            })
            return cached
        
        return None
    
    async def set_cached_response(self, cache_key: str, cache_type: CacheType,
                                endpoint: str, response_data: Dict[str, Any],
                                status_code: int, ttl_seconds: int = 300,
                                **kwargs) -> APIResponseCache:
        """Set cached API response"""
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        
        cache_data = {
            "cache_key": cache_key,
            "cache_type": cache_type,
            "endpoint": endpoint,
            "response_data": response_data,
            "status_code": status_code,
            "response_size": len(str(response_data).encode('utf-8')),
            "expires_at": expires_at,
            **kwargs
        }
        
        # Remove existing cache with same key
        existing = await self.get_one({"cache_key": cache_key})
        if existing:
            await self.delete(str(existing.id))
        
        return await self.create(cache_data)
    
    async def cleanup_expired(self) -> int:
        """Remove expired cache entries"""
        collection = await self.get_collection()
        result = await collection.delete_many({
            "expires_at": {"$lt": datetime.now(timezone.utc)}
        })
        return result.deleted_count

# Repository instances
chart_cache_repository = ChartCacheRepository()
ticker_cache_repository = TickerCacheRepository()
balance_cache_repository = BalanceCacheRepository()
api_response_cache_repository = APIResponseCacheRepository()