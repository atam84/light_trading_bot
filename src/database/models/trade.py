# src/database/models/trade.py

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import Field, validator
from enum import Enum
from decimal import Decimal
from src.database.models.base import (
    BaseDBModel, BaseRepository, TimestampMixin, 
    UserOwnershipMixin, PyObjectId
)

class TradeSide(str, Enum):
    """Trade side"""
    BUY = "buy"
    SELL = "sell"

class TradeType(str, Enum):
    """Trade type"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    STOP_LIMIT = "stop_limit"

class TradeStatus(str, Enum):
    """Trade status"""
    PENDING = "pending"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"

class TradingMode(str, Enum):
    """Trading mode"""
    LIVE = "live"
    PAPER = "paper"
    BACKTEST = "backtest"

class TradeSignalType(str, Enum):
    """Trade signal type"""
    ENTRY = "entry"
    EXIT = "exit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    MANUAL = "manual"

class Trade(BaseDBModel, TimestampMixin, UserOwnershipMixin):
    """Trade execution model"""
    
    # Strategy reference
    strategy_id: Optional[PyObjectId] = Field(None, description="Strategy that generated this trade")
    
    # Exchange and symbol
    exchange: str = Field(..., description="Exchange name")
    symbol: str = Field(..., description="Trading pair symbol")
    
    # Order details
    side: TradeSide = Field(..., description="Buy or sell")
    type: TradeType = Field(..., description="Order type")
    amount: float = Field(..., gt=0, description="Order amount")
    price: Optional[float] = Field(None, description="Order price (for limit orders)")
    
    # Execution details
    filled_amount: float = Field(default=0.0, ge=0, description="Filled amount")
    average_price: Optional[float] = Field(None, description="Average execution price")
    status: TradeStatus = Field(default=TradeStatus.PENDING, description="Order status")
    
    # External references
    order_id: Optional[str] = Field(None, description="Exchange order ID")
    client_order_id: Optional[str] = Field(None, description="Client-side order ID")
    
    # Trading mode and signal
    mode: TradingMode = Field(..., description="Trading mode")
    signal_type: TradeSignalType = Field(default=TradeSignalType.MANUAL, description="Signal type")
    
    # Fees and costs
    fee: float = Field(default=0.0, ge=0, description="Trading fee")
    fee_currency: Optional[str] = Field(None, description="Fee currency")
    commission: float = Field(default=0.0, ge=0, description="Commission")
    
    # Timestamps
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    execution_time: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    
    # Stop loss and take profit
    stop_loss_price: Optional[float] = Field(None, description="Stop loss price")
    take_profit_price: Optional[float] = Field(None, description="Take profit price")
    
    # Metadata
    notes: Optional[str] = Field(None, max_length=1000, description="Trade notes")
    metadata: Dict[str, Any] = Field(default={}, description="Additional metadata")
    
    # Error tracking
    error_message: Optional[str] = Field(None, description="Error message if trade failed")
    retry_count: int = Field(default=0, description="Number of retry attempts")
    
    @property
    def collection_name(self) -> str:
        return "trades"
    
    @validator('symbol')
    def validate_symbol(cls, v):
        return v.upper()
    
    @validator('exchange')
    def validate_exchange(cls, v):
        return v.lower()
    
    def get_total_value(self) -> float:
        """Get total trade value"""
        if self.average_price and self.filled_amount:
            return self.average_price * self.filled_amount
        elif self.price and self.amount:
            return self.price * self.amount
        return 0.0
    
    def get_fill_percentage(self) -> float:
        """Get fill percentage"""
        if self.amount == 0:
            return 0.0
        return (self.filled_amount / self.amount) * 100
    
    def is_filled(self) -> bool:
        """Check if trade is completely filled"""
        return self.status == TradeStatus.FILLED
    
    def is_active(self) -> bool:
        """Check if trade is still active"""
        return self.status in [TradeStatus.PENDING, TradeStatus.PARTIALLY_FILLED]
    
    def can_cancel(self) -> bool:
        """Check if trade can be cancelled"""
        return self.status in [TradeStatus.PENDING, TradeStatus.PARTIALLY_FILLED]
    
    def update_execution(self, filled_amount: float, average_price: float, 
                        fee: float = 0.0, status: TradeStatus = None):
        """Update trade execution details"""
        self.filled_amount = filled_amount
        self.average_price = average_price
        self.fee += fee
        
        if status:
            self.status = status
        elif filled_amount >= self.amount:
            self.status = TradeStatus.FILLED
        elif filled_amount > 0:
            self.status = TradeStatus.PARTIALLY_FILLED
        
        if self.status == TradeStatus.FILLED:
            self.execution_time = datetime.now(timezone.utc)
    
    def to_summary_dict(self) -> Dict[str, Any]:
        """Return trade summary"""
        return {
            "id": str(self.id),
            "symbol": self.symbol,
            "side": self.side,
            "type": self.type,
            "amount": self.amount,
            "filled_amount": self.filled_amount,
            "price": self.price,
            "average_price": self.average_price,
            "status": self.status,
            "mode": self.mode,
            "total_value": self.get_total_value(),
            "fill_percentage": self.get_fill_percentage(),
            "fee": self.fee,
            "submitted_at": self.submitted_at,
            "execution_time": self.execution_time
        }

class Position(BaseDBModel, TimestampMixin, UserOwnershipMixin):
    """Trading position model (aggregates related trades)"""
    
    # Position identification
    strategy_id: Optional[PyObjectId] = Field(None, description="Strategy ID")
    exchange: str = Field(..., description="Exchange name")
    symbol: str = Field(..., description="Trading pair symbol")
    
    # Position details
    side: TradeSide = Field(..., description="Position side")
    size: float = Field(default=0.0, description="Current position size")
    entry_price: Optional[float] = Field(None, description="Average entry price")
    current_price: Optional[float] = Field(None, description="Current market price")
    
    # PnL tracking
    unrealized_pnl: float = Field(default=0.0, description="Unrealized PnL")
    realized_pnl: float = Field(default=0.0, description="Realized PnL")
    total_pnl: float = Field(default=0.0, description="Total PnL")
    
    # Position metadata
    mode: TradingMode = Field(..., description="Trading mode")
    is_open: bool = Field(default=True, description="Position status")
    opened_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    closed_at: Optional[datetime] = None
    
    # Risk management
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    
    # Related trades
    entry_trades: List[PyObjectId] = Field(default=[], description="Entry trade IDs")
    exit_trades: List[PyObjectId] = Field(default=[], description="Exit trade IDs")
    
    @property
    def collection_name(self) -> str:
        return "positions"
    
    def update_pnl(self, current_price: float):
        """Update position PnL based on current price"""
        self.current_price = current_price
        
        if self.entry_price and self.size > 0:
            if self.side == TradeSide.BUY:
                self.unrealized_pnl = (current_price - self.entry_price) * self.size
            else:  # SELL
                self.unrealized_pnl = (self.entry_price - current_price) * self.size
            
            self.total_pnl = self.realized_pnl + self.unrealized_pnl
    
    def close_position(self, exit_price: float):
        """Close the position"""
        if self.entry_price and self.size > 0:
            if self.side == TradeSide.BUY:
                self.realized_pnl += (exit_price - self.entry_price) * self.size
            else:  # SELL
                self.realized_pnl += (self.entry_price - exit_price) * self.size
        
        self.size = 0.0
        self.unrealized_pnl = 0.0
        self.total_pnl = self.realized_pnl
        self.is_open = False
        self.closed_at = datetime.now(timezone.utc)

class TradeRepository(BaseRepository[Trade]):
    """Repository for Trade operations"""
    
    def __init__(self):
        super().__init__(Trade)
    
    async def get_user_trades(self, user_id: str, mode: TradingMode = None,
                            skip: int = 0, limit: int = 100) -> List[Trade]:
        """Get user trades"""
        filter_dict = {"user_id": PyObjectId(user_id)}
        if mode:
            filter_dict["mode"] = mode
        
        return await self.get_many(
            filter_dict=filter_dict,
            skip=skip,
            limit=limit,
            sort=[("submitted_at", -1)]
        )
    
    async def get_active_trades(self, user_id: str = None, strategy_id: str = None) -> List[Trade]:
        """Get active trades"""
        filter_dict = {"status": {"$in": [TradeStatus.PENDING, TradeStatus.PARTIALLY_FILLED]}}
        
        if user_id:
            filter_dict["user_id"] = PyObjectId(user_id)
        if strategy_id:
            filter_dict["strategy_id"] = PyObjectId(strategy_id)
        
        return await self.get_many(filter_dict, sort=[("submitted_at", -1)])
    
    async def get_symbol_trades(self, symbol: str, user_id: str = None,
                              days: int = 30) -> List[Trade]:
        """Get trades for specific symbol"""
        from_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        filter_dict = {
            "symbol": symbol.upper(),
            "submitted_at": {"$gte": from_date}
        }
        
        if user_id:
            filter_dict["user_id"] = PyObjectId(user_id)
        
        return await self.get_many(filter_dict, sort=[("submitted_at", -1)])
    
    async def create_trade(self, user_id: str, exchange: str, symbol: str,
                         side: str, trade_type: str, amount: float,
                         mode: str, **kwargs) -> Trade:
        """Create new trade"""
        trade_data = {
            "user_id": PyObjectId(user_id),
            "exchange": exchange.lower(),
            "symbol": symbol.upper(),
            "side": side,
            "type": trade_type,
            "amount": amount,
            "mode": mode,
            **kwargs
        }
        
        return await self.create(trade_data)
    
    async def update_execution(self, trade_id: str, filled_amount: float,
                             average_price: float, fee: float = 0.0,
                             status: TradeStatus = None) -> Optional[Trade]:
        """Update trade execution"""
        trade = await self.get_by_id(trade_id)
        if not trade:
            return None
        
        update_data = {
            "filled_amount": filled_amount,
            "average_price": average_price,
            "fee": trade.fee + fee
        }
        
        if status:
            update_data["status"] = status
        elif filled_amount >= trade.amount:
            update_data["status"] = TradeStatus.FILLED
            update_data["execution_time"] = datetime.now(timezone.utc)
        elif filled_amount > 0:
            update_data["status"] = TradeStatus.PARTIALLY_FILLED
        
        return await self.update(trade_id, update_data)
    
    async def cancel_trade(self, trade_id: str, reason: str = None) -> bool:
        """Cancel a trade"""
        update_data = {
            "status": TradeStatus.CANCELLED,
            "cancelled_at": datetime.now(timezone.utc)
        }
        
        if reason:
            update_data["notes"] = reason
        
        result = await self.update(trade_id, update_data)
        return result is not None
    
    async def get_trade_statistics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get trade statistics for user"""
        from_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        trades = await self.get_many({
            "user_id": PyObjectId(user_id),
            "submitted_at": {"$gte": from_date},
            "status": TradeStatus.FILLED
        })
        
        if not trades:
            return {
                "total_trades": 0,
                "total_volume": 0.0,
                "total_fees": 0.0,
                "symbols_traded": 0,
                "exchanges_used": 0
            }
        
        total_volume = sum(trade.get_total_value() for trade in trades)
        total_fees = sum(trade.fee for trade in trades)
        symbols = set(trade.symbol for trade in trades)
        exchanges = set(trade.exchange for trade in trades)
        
        return {
            "total_trades": len(trades),
            "total_volume": total_volume,
            "total_fees": total_fees,
            "symbols_traded": len(symbols),
            "exchanges_used": len(exchanges),
            "symbols": list(symbols),
            "exchanges": list(exchanges)
        }

class PositionRepository(BaseRepository[Position]):
    """Repository for Position operations"""
    
    def __init__(self):
        super().__init__(Position)
    
    async def get_user_positions(self, user_id: str, open_only: bool = True) -> List[Position]:
        """Get user positions"""
        filter_dict = {"user_id": PyObjectId(user_id)}
        if open_only:
            filter_dict["is_open"] = True
        
        return await self.get_many(filter_dict, sort=[("opened_at", -1)])
    
    async def get_symbol_position(self, user_id: str, symbol: str, 
                                strategy_id: str = None) -> Optional[Position]:
        """Get position for specific symbol"""
        filter_dict = {
            "user_id": PyObjectId(user_id),
            "symbol": symbol.upper(),
            "is_open": True
        }
        
        if strategy_id:
            filter_dict["strategy_id"] = PyObjectId(strategy_id)
        
        return await self.get_one(filter_dict)
    
    async def create_position(self, user_id: str, strategy_id: str, exchange: str,
                            symbol: str, side: str, mode: str, **kwargs) -> Position:
        """Create new position"""
        position_data = {
            "user_id": PyObjectId(user_id),
            "strategy_id": PyObjectId(strategy_id) if strategy_id else None,
            "exchange": exchange.lower(),
            "symbol": symbol.upper(),
            "side": side,
            "mode": mode,
            **kwargs
        }
        
        return await self.create(position_data)
    
    async def update_position_pnl(self, position_id: str, current_price: float) -> Optional[Position]:
        """Update position PnL"""
        position = await self.get_by_id(position_id)
        if not position:
            return None
        
        # Calculate PnL
        unrealized_pnl = 0.0
        if position.entry_price and position.size > 0:
            if position.side == TradeSide.BUY:
                unrealized_pnl = (current_price - position.entry_price) * position.size
            else:
                unrealized_pnl = (position.entry_price - current_price) * position.size
        
        total_pnl = position.realized_pnl + unrealized_pnl
        
        update_data = {
            "current_price": current_price,
            "unrealized_pnl": unrealized_pnl,
            "total_pnl": total_pnl
        }
        
        return await self.update(position_id, update_data)
    
    async def close_position(self, position_id: str, exit_price: float) -> Optional[Position]:
        """Close a position"""
        position = await self.get_by_id(position_id)
        if not position:
            return None
        
        # Calculate final realized PnL
        realized_pnl = position.realized_pnl
        if position.entry_price and position.size > 0:
            if position.side == TradeSide.BUY:
                realized_pnl += (exit_price - position.entry_price) * position.size
            else:
                realized_pnl += (position.entry_price - exit_price) * position.size
        
        update_data = {
            "size": 0.0,
            "unrealized_pnl": 0.0,
            "realized_pnl": realized_pnl,
            "total_pnl": realized_pnl,
            "is_open": False,
            "closed_at": datetime.now(timezone.utc),
            "current_price": exit_price
        }
        
        return await self.update(position_id, update_data)

# Repository instances
trade_repository = TradeRepository()
position_repository = PositionRepository()