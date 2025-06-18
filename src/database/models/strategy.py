# src/database/models/strategy.py

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Union
from pydantic import Field, validator
from enum import Enum
from src.database.models.base import (
    BaseDBModel, BaseRepository, TimestampMixin, 
    UserOwnershipMixin, ActiveMixin, PyObjectId
)

class StrategyType(str, Enum):
    """Strategy types"""
    SIMPLE = "simple"
    GRID = "grid"
    INDICATOR_BASED = "indicator_based"
    DCA = "dca"  # Dollar Cost Averaging
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    ARBITRAGE = "arbitrage"
    CUSTOM = "custom"

class IndicatorType(str, Enum):
    """Technical indicator types"""
    RSI = "rsi"
    MA = "ma"  # Moving Average
    EMA = "ema"  # Exponential Moving Average
    SMA = "sma"  # Simple Moving Average
    MACD = "macd"
    BOLLINGER_BANDS = "bollinger_bands"
    STOCHASTIC = "stochastic"
    ATR = "atr"  # Average True Range
    VOLUME = "volume"
    CUSTOM = "custom"

class TimeFrame(str, Enum):
    """Trading timeframes"""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    H8 = "8h"
    D1 = "1d"
    W1 = "1w"

class OrderType(str, Enum):
    """Order types"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    STOP_LIMIT = "stop_limit"

class SignalCondition(str, Enum):
    """Signal condition types"""
    ABOVE_THRESHOLD = "above_threshold"
    BELOW_THRESHOLD = "below_threshold"
    CROSSES_ABOVE = "crosses_above"
    CROSSES_BELOW = "crosses_below"
    GOLDEN_CROSS = "golden_cross"
    DEATH_CROSS = "death_cross"
    DIVERGENCE = "divergence"
    CUSTOM = "custom"

class IndicatorConfig(BaseDBModel):
    """Indicator configuration"""
    type: IndicatorType = Field(..., description="Indicator type")
    params: Dict[str, Any] = Field(default={}, description="Indicator parameters")
    condition: SignalCondition = Field(..., description="Signal condition")
    threshold: Optional[float] = Field(None, description="Threshold value")
    weight: float = Field(default=1.0, ge=0, le=1, description="Signal weight")
    
    @property
    def collection_name(self) -> str:
        return "indicator_configs"

class RiskManagement(BaseDBModel):
    """Risk management configuration"""
    # Position sizing
    position_size_type: str = Field(default="fixed", description="fixed, percentage, risk_based")
    position_size_value: float = Field(default=100.0, description="Position size value")
    max_position_size: Optional[float] = Field(None, description="Maximum position size")
    
    # Risk limits
    stop_loss_percentage: Optional[float] = Field(None, ge=0, le=1, description="Stop loss %")
    take_profit_percentage: Optional[float] = Field(None, ge=0, description="Take profit %")
    trailing_stop: bool = Field(default=False, description="Enable trailing stop")
    trailing_stop_percentage: Optional[float] = Field(None, ge=0, le=1, description="Trailing stop %")
    
    # Budget management
    max_concurrent_trades: int = Field(default=10, ge=1, description="Max concurrent trades")
    max_trades_per_symbol: int = Field(default=2, ge=1, description="Max trades per symbol")
    daily_loss_limit: Optional[float] = Field(None, ge=0, description="Daily loss limit")
    max_balance_usage: float = Field(default=0.5, ge=0, le=1, description="Max balance usage %")
    
    # Emergency controls
    emergency_stop: bool = Field(default=False, description="Emergency stop activated")
    max_drawdown_limit: Optional[float] = Field(None, ge=0, le=1, description="Max drawdown limit")
    
    @property
    def collection_name(self) -> str:
        return "risk_management"
    
    @validator('stop_loss_percentage', 'take_profit_percentage', 'trailing_stop_percentage')
    def validate_percentages(cls, v):
        if v is not None and (v < 0 or v > 1):
            raise ValueError('Percentages must be between 0 and 1')
        return v

class StrategyConfig(BaseDBModel, TimestampMixin, UserOwnershipMixin, ActiveMixin):
    """Trading strategy configuration"""
    
    name: str = Field(..., min_length=1, max_length=100, description="Strategy name")
    description: str = Field(default="", max_length=1000, description="Strategy description")
    strategy_type: StrategyType = Field(..., description="Strategy type")
    
    # Trading configuration
    timeframe: TimeFrame = Field(default=TimeFrame.H1, description="Primary timeframe")
    symbols: List[str] = Field(default=[], description="Trading symbols")
    exchange: Optional[str] = Field(None, description="Preferred exchange")
    
    # Strategy-specific configuration
    config: Dict[str, Any] = Field(default={}, description="Strategy-specific config")
    
    # Indicator chain (for indicator-based strategies)
    entry_indicators: List[IndicatorConfig] = Field(default=[], description="Entry indicators")
    exit_indicators: List[IndicatorConfig] = Field(default=[], description="Exit indicators")
    confirmation_indicators: List[IndicatorConfig] = Field(default=[], description="Confirmation indicators")
    
    # Risk management
    risk_management: RiskManagement = Field(default_factory=RiskManagement)
    
    # Order configuration
    default_order_type: OrderType = Field(default=OrderType.MARKET, description="Default order type")
    slippage_tolerance: float = Field(default=0.001, ge=0, le=0.1, description="Slippage tolerance")
    
    # Performance tracking
    total_trades: int = Field(default=0, description="Total trades executed")
    winning_trades: int = Field(default=0, description="Winning trades")
    losing_trades: int = Field(default=0, description="Losing trades")
    total_profit: float = Field(default=0.0, description="Total profit/loss")
    max_drawdown: float = Field(default=0.0, description="Maximum drawdown")
    
    # Marketplace (for sharing strategies)
    public: bool = Field(default=False, description="Available in marketplace")
    marketplace_title: Optional[str] = Field(None, max_length=200)
    marketplace_description: Optional[str] = Field(None, max_length=2000)
    tags: List[str] = Field(default=[], description="Strategy tags")
    rating: float = Field(default=0.0, ge=0, le=5, description="Average rating")
    downloads: int = Field(default=0, description="Download count")
    
    # Status tracking
    last_signal_time: Optional[datetime] = None
    last_trade_time: Optional[datetime] = None
    is_running: bool = Field(default=False, description="Currently running")
    
    @property
    def collection_name(self) -> str:
        return "strategies"
    
    @validator('name')
    def validate_name(cls, v):
        return v.strip()
    
    @validator('symbols')
    def validate_symbols(cls, v):
        return [symbol.upper() for symbol in v]
    
    def get_win_rate(self) -> float:
        """Calculate win rate percentage"""
        total = self.winning_trades + self.losing_trades
        if total == 0:
            return 0.0
        return (self.winning_trades / total) * 100
    
    def get_profit_factor(self) -> float:
        """Calculate profit factor"""
        if self.losing_trades == 0 or self.total_profit <= 0:
            return 0.0
        
        # Simplified calculation - would need actual trade data for accurate calculation
        avg_win = self.total_profit / self.winning_trades if self.winning_trades > 0 else 0
        avg_loss = abs(self.total_profit) / self.losing_trades if self.losing_trades > 0 else 1
        
        return avg_win / avg_loss if avg_loss > 0 else 0.0
    
    def update_performance(self, profit: float, is_winning_trade: bool):
        """Update strategy performance metrics"""
        self.total_trades += 1
        self.total_profit += profit
        
        if is_winning_trade:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        
        # Update drawdown (simplified)
        if profit < 0:
            current_drawdown = abs(profit)
            if current_drawdown > self.max_drawdown:
                self.max_drawdown = current_drawdown
        
        self.last_trade_time = datetime.now(timezone.utc)
    
    def can_place_trade(self, symbol: str) -> bool:
        """Check if strategy can place a new trade"""
        if not self.active or not self.is_running:
            return False
        
        if self.risk_management.emergency_stop:
            return False
        
        # Additional checks would be implemented based on current open trades
        return True
    
    def to_marketplace_dict(self) -> Dict[str, Any]:
        """Convert to marketplace format"""
        return {
            "id": str(self.id),
            "title": self.marketplace_title or self.name,
            "description": self.marketplace_description or self.description,
            "strategy_type": self.strategy_type,
            "timeframe": self.timeframe,
            "tags": self.tags,
            "rating": self.rating,
            "downloads": self.downloads,
            "total_trades": self.total_trades,
            "win_rate": self.get_win_rate(),
            "total_profit": self.total_profit,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "config": self.config,
            "entry_indicators": [ind.dict() for ind in self.entry_indicators],
            "exit_indicators": [ind.dict() for ind in self.exit_indicators],
            "risk_management": self.risk_management.dict()
        }

class StrategyTemplate(BaseDBModel, TimestampMixin):
    """Predefined strategy templates"""
    
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    strategy_type: StrategyType = Field(..., description="Strategy type")
    category: str = Field(..., description="Strategy category")
    difficulty_level: str = Field(default="beginner", description="beginner, intermediate, advanced")
    
    # Template configuration
    template_config: Dict[str, Any] = Field(..., description="Template configuration")
    default_risk_management: RiskManagement = Field(default_factory=RiskManagement)
    
    # Marketplace info
    tags: List[str] = Field(default=[], description="Template tags")
    is_official: bool = Field(default=False, description="Official template")
    usage_count: int = Field(default=0, description="How many times used")
    
    @property
    def collection_name(self) -> str:
        return "strategy_templates"

class StrategyRepository(BaseRepository[StrategyConfig]):
    """Repository for StrategyConfig operations"""
    
    def __init__(self):
        super().__init__(StrategyConfig)
    
    async def get_user_strategies(self, user_id: str, active_only: bool = True) -> List[StrategyConfig]:
        """Get all strategies for a user"""
        filter_dict = {"user_id": PyObjectId(user_id)}
        if active_only:
            filter_dict["active"] = True
        
        return await self.get_many(
            filter_dict=filter_dict,
            sort=[("created_at", -1)]
        )
    
    async def get_by_name_and_user(self, user_id: str, name: str) -> Optional[StrategyConfig]:
        """Get strategy by name and user"""
        return await self.get_one({
            "user_id": PyObjectId(user_id),
            "name": name
        })
    
    async def get_running_strategies(self, user_id: str = None) -> List[StrategyConfig]:
        """Get currently running strategies"""
        filter_dict = {"is_running": True, "active": True}
        if user_id:
            filter_dict["user_id"] = PyObjectId(user_id)
        
        return await self.get_many(filter_dict)
    
    async def get_marketplace_strategies(self, category: str = None, 
                                       tags: List[str] = None,
                                       min_rating: float = 0.0,
                                       skip: int = 0, limit: int = 20) -> List[StrategyConfig]:
        """Get public marketplace strategies"""
        filter_dict = {"public": True, "active": True}
        
        if category:
            filter_dict["tags"] = category
        
        if tags:
            filter_dict["tags"] = {"$in": tags}
        
        if min_rating > 0:
            filter_dict["rating"] = {"$gte": min_rating}
        
        return await self.get_many(
            filter_dict=filter_dict,
            skip=skip,
            limit=limit,
            sort=[("rating", -1), ("downloads", -1)]
        )
    
    async def create_strategy(self, user_id: str, name: str, strategy_type: str, **kwargs) -> StrategyConfig:
        """Create new strategy"""
        
        # Check if strategy name already exists for user
        existing = await self.get_by_name_and_user(user_id, name)
        if existing:
            raise ValueError(f"Strategy '{name}' already exists for user")
        
        strategy_data = {
            "user_id": PyObjectId(user_id),
            "name": name,
            "strategy_type": strategy_type,
            **kwargs
        }
        
        return await self.create(strategy_data)
    
    async def update_performance(self, strategy_id: str, profit: float, 
                               is_winning_trade: bool) -> Optional[StrategyConfig]:
        """Update strategy performance metrics"""
        strategy = await self.get_by_id(strategy_id)
        if not strategy:
            return None
        
        update_data = {
            "total_trades": strategy.total_trades + 1,
            "total_profit": strategy.total_profit + profit,
            "last_trade_time": datetime.now(timezone.utc)
        }
        
        if is_winning_trade:
            update_data["winning_trades"] = strategy.winning_trades + 1
        else:
            update_data["losing_trades"] = strategy.losing_trades + 1
        
        # Update max drawdown if applicable
        if profit < 0:
            current_drawdown = abs(profit)
            if current_drawdown > strategy.max_drawdown:
                update_data["max_drawdown"] = current_drawdown
        
        return await self.update(strategy_id, update_data)
    
    async def start_strategy(self, strategy_id: str) -> bool:
        """Start a strategy"""
        result = await self.update(strategy_id, {
            "is_running": True,
            "updated_at": datetime.now(timezone.utc)
        })
        return result is not None
    
    async def stop_strategy(self, strategy_id: str) -> bool:
        """Stop a strategy"""
        result = await self.update(strategy_id, {
            "is_running": False,
            "updated_at": datetime.now(timezone.utc)
        })
        return result is not None
    
    async def increment_downloads(self, strategy_id: str) -> bool:
        """Increment download count for marketplace strategy"""
        strategy = await self.get_by_id(strategy_id)
        if not strategy:
            return False
        
        result = await self.update(strategy_id, {
            "downloads": strategy.downloads + 1
        })
        return result is not None
    
    async def search_strategies(self, query: str, user_id: str = None, 
                              skip: int = 0, limit: int = 20) -> List[StrategyConfig]:
        """Search strategies by name, description, or tags"""
        filter_dict = {
            "$or": [
                {"name": {"$regex": query, "$options": "i"}},
                {"description": {"$regex": query, "$options": "i"}},
                {"tags": {"$regex": query, "$options": "i"}}
            ]
        }
        
        if user_id:
            filter_dict["user_id"] = PyObjectId(user_id)
        else:
            filter_dict["public"] = True
        
        return await self.get_many(filter_dict, skip=skip, limit=limit)

class StrategyTemplateRepository(BaseRepository[StrategyTemplate]):
    """Repository for StrategyTemplate operations"""
    
    def __init__(self):
        super().__init__(StrategyTemplate)
    
    async def get_by_category(self, category: str) -> List[StrategyTemplate]:
        """Get templates by category"""
        return await self.get_many(
            filter_dict={"category": category},
            sort=[("usage_count", -1)]
        )
    
    async def get_official_templates(self) -> List[StrategyTemplate]:
        """Get official strategy templates"""
        return await self.get_many(
            filter_dict={"is_official": True},
            sort=[("name", 1)]
        )
    
    async def increment_usage(self, template_id: str) -> bool:
        """Increment template usage count"""
        template = await self.get_by_id(template_id)
        if not template:
            return False
        
        result = await self.update(template_id, {
            "usage_count": template.usage_count + 1
        })
        return result is not None

# Repository instances
strategy_repository = StrategyRepository()
strategy_template_repository = StrategyTemplateRepository()