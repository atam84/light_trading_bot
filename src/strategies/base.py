# src/strategies/base.py

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)

class SignalType(Enum):
    """Signal types for strategy decisions"""
    ENTRY = "entry"
    CONFIRMATION = "confirmation"
    EXIT = "exit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"

class SignalAction(Enum):
    """Signal actions"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"

class StrategyType(Enum):
    """Available strategy types"""
    SIMPLE = "simple"
    GRID = "grid"
    INDICATOR = "indicator"
    CUSTOM = "custom"

@dataclass
class Signal:
    """Trading signal with context"""
    action: SignalAction
    signal_type: SignalType
    symbol: str
    price: float
    confidence: float = 1.0
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MarketData:
    """Market data container"""
    symbol: str
    timeframe: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    indicators: Dict[str, float] = field(default_factory=dict)

@dataclass
class StrategyConfig:
    """Base strategy configuration"""
    name: str
    strategy_type: StrategyType
    timeframe: str = "1h"
    symbols: List[str] = field(default_factory=list)
    active: bool = True
    
    # Risk management
    max_position_size: float = 100.0  # USD
    stop_loss_pct: float = 0.05  # 5%
    take_profit_pct: float = 0.15  # 15%
    trailing_stop: bool = False
    
    # Strategy specific parameters
    parameters: Dict[str, Any] = field(default_factory=dict)

class BaseStrategy(ABC):
    """Abstract base class for all trading strategies"""
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.active = config.active
        self.positions = {}  # symbol -> position info
        self.signals_history = []
        self.performance_metrics = {}
        self.last_signals = {}  # symbol -> last signal
        
    @abstractmethod
    async def analyze(self, market_data: MarketData) -> Optional[Signal]:
        """
        Analyze market data and generate trading signals
        
        Args:
            market_data: Current market data with indicators
            
        Returns:
            Trading signal or None if no signal
        """
        pass
    
    @abstractmethod
    def get_required_indicators(self) -> List[str]:
        """
        Get list of required indicators for this strategy
        
        Returns:
            List of indicator names (e.g., ['rsi', 'ema12', 'ema26'])
        """
        pass
    
    def validate_config(self) -> bool:
        """
        Validate strategy configuration
        
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['name', 'strategy_type', 'timeframe']
        for field in required_fields:
            if not hasattr(self.config, field) or getattr(self.config, field) is None:
                logger.error(f"Missing required config field: {field}")
                return False
        return True
    
    def should_enter_position(self, symbol: str, current_price: float) -> bool:
        """
        Check if we should enter a new position
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            
        Returns:
            True if should enter position
        """
        # Check if already have maximum positions for this symbol
        current_positions = len([p for p in self.positions.values() 
                               if p.get('symbol') == symbol and p.get('status') == 'open'])
        
        max_per_symbol = self.config.parameters.get('max_positions_per_symbol', 2)
        return current_positions < max_per_symbol
    
    def should_exit_position(self, symbol: str, current_price: float) -> bool:
        """
        Check if we should exit existing position
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            
        Returns:
            True if should exit position
        """
        position = self.positions.get(symbol)
        if not position or position.get('status') != 'open':
            return False
        
        entry_price = position['entry_price']
        side = position['side']
        
        # Calculate profit/loss percentage
        if side == 'buy':
            pnl_pct = (current_price - entry_price) / entry_price
        else:
            pnl_pct = (entry_price - current_price) / entry_price
        
        # Check stop loss
        if pnl_pct <= -self.config.stop_loss_pct:
            return True
        
        # Check take profit
        if pnl_pct >= self.config.take_profit_pct:
            return True
        
        return False
    
    def update_position(self, symbol: str, side: str, price: float, amount: float):
        """
        Update position information
        
        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            price: Entry price
            amount: Position size
        """
        self.positions[symbol] = {
            'symbol': symbol,
            'side': side,
            'entry_price': price,
            'amount': amount,
            'timestamp': datetime.now(),
            'status': 'open'
        }
    
    def close_position(self, symbol: str, exit_price: float):
        """
        Close position and calculate PnL
        
        Args:
            symbol: Trading symbol
            exit_price: Exit price
        """
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        entry_price = position['entry_price']
        side = position['side']
        amount = position['amount']
        
        # Calculate PnL
        if side == 'buy':
            pnl = (exit_price - entry_price) * amount
        else:
            pnl = (entry_price - exit_price) * amount
        
        # Update position
        position.update({
            'status': 'closed',
            'exit_price': exit_price,
            'pnl': pnl,
            'exit_timestamp': datetime.now()
        })
        
        # Update performance metrics
        self.update_performance_metrics(pnl)
    
    def update_performance_metrics(self, pnl: float):
        """
        Update strategy performance metrics
        
        Args:
            pnl: Profit/Loss from closed trade
        """
        if 'total_trades' not in self.performance_metrics:
            self.performance_metrics = {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'total_pnl': 0.0,
                'best_trade': 0.0,
                'worst_trade': 0.0,
                'win_rate': 0.0
            }
        
        self.performance_metrics['total_trades'] += 1
        self.performance_metrics['total_pnl'] += pnl
        
        if pnl > 0:
            self.performance_metrics['winning_trades'] += 1
            self.performance_metrics['best_trade'] = max(
                self.performance_metrics['best_trade'], pnl
            )
        else:
            self.performance_metrics['losing_trades'] += 1
            self.performance_metrics['worst_trade'] = min(
                self.performance_metrics['worst_trade'], pnl
            )
        
        # Calculate win rate
        total = self.performance_metrics['total_trades']
        wins = self.performance_metrics['winning_trades']
        self.performance_metrics['win_rate'] = (wins / total) * 100 if total > 0 else 0
    
    def add_signal(self, signal: Signal):
        """
        Add signal to history
        
        Args:
            signal: Trading signal to add
        """
        self.signals_history.append(signal)
        self.last_signals[signal.symbol] = signal
        
        # Keep only last 1000 signals
        if len(self.signals_history) > 1000:
            self.signals_history = self.signals_history[-1000:]
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get strategy status information
        
        Returns:
            Dictionary with strategy status
        """
        open_positions = [p for p in self.positions.values() if p.get('status') == 'open']
        
        return {
            'name': self.config.name,
            'type': self.config.strategy_type.value,
            'active': self.active,
            'timeframe': self.config.timeframe,
            'symbols': self.config.symbols,
            'open_positions': len(open_positions),
            'total_signals': len(self.signals_history),
            'performance': self.performance_metrics,
            'last_analysis': self.last_signals
        }
    
    def reset(self):
        """Reset strategy state"""
        self.positions.clear()
        self.signals_history.clear()
        self.last_signals.clear()
        self.performance_metrics.clear()

class IndicatorMixin:
    """Mixin for strategies that use technical indicators"""
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """
        Calculate RSI indicator
        
        Args:
            prices: List of closing prices
            period: RSI period
            
        Returns:
            RSI value
        """
        if len(prices) < period + 1:
            return 50.0  # Neutral RSI
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_sma(self, prices: List[float], period: int) -> float:
        """
        Calculate Simple Moving Average
        
        Args:
            prices: List of closing prices
            period: SMA period
            
        Returns:
            SMA value
        """
        if len(prices) < period:
            return prices[-1] if prices else 0.0
        
        return sum(prices[-period:]) / period
    
    def calculate_ema(self, prices: List[float], period: int) -> float:
        """
        Calculate Exponential Moving Average
        
        Args:
            prices: List of closing prices
            period: EMA period
            
        Returns:
            EMA value
        """
        if len(prices) < period:
            return prices[-1] if prices else 0.0
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def detect_ma_cross(self, fast_ma: float, slow_ma: float, 
                       prev_fast_ma: float, prev_slow_ma: float) -> str:
        """
        Detect moving average crossover
        
        Args:
            fast_ma: Current fast MA value
            slow_ma: Current slow MA value
            prev_fast_ma: Previous fast MA value
            prev_slow_ma: Previous slow MA value
            
        Returns:
            'golden_cross', 'death_cross', or 'none'
        """
        current_above = fast_ma > slow_ma
        prev_above = prev_fast_ma > prev_slow_ma
        
        if not prev_above and current_above:
            return 'golden_cross'
        elif prev_above and not current_above:
            return 'death_cross'
        else:
            return 'none'