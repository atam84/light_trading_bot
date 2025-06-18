# src/core/strategies/base_strategy.py

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid

class SignalType(Enum):
    """Trading signal types"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"

class SignalStrength(Enum):
    """Signal strength levels"""
    WEAK = 1
    MODERATE = 2
    STRONG = 3
    VERY_STRONG = 4

class StrategyState(Enum):
    """Strategy states"""
    INACTIVE = "inactive"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"

@dataclass
class TradingSignal:
    """Trading signal data structure"""
    signal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    strategy_name: str = ""
    symbol: str = ""
    signal_type: SignalType = SignalType.HOLD
    strength: SignalStrength = SignalStrength.MODERATE
    price: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    timeframe: str = "1h"
    confidence: float = 0.5  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Trade parameters
    suggested_amount: Optional[float] = None
    suggested_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'signal_id': self.signal_id,
            'strategy_name': self.strategy_name,
            'symbol': self.symbol,
            'signal_type': self.signal_type.value,
            'strength': self.strength.value,
            'price': self.price,
            'timestamp': self.timestamp.isoformat(),
            'timeframe': self.timeframe,
            'confidence': self.confidence,
            'metadata': self.metadata,
            'suggested_amount': self.suggested_amount,
            'suggested_price': self.suggested_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit
        }

@dataclass
class MarketData:
    """Market data structure for strategies"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    timeframe: str
    
    # Technical indicators (will be populated by data manager)
    indicators: Dict[str, float] = field(default_factory=dict)

@dataclass
class StrategyPerformance:
    """Strategy performance metrics"""
    total_signals: int = 0
    successful_trades: int = 0
    failed_trades: int = 0
    total_return: float = 0.0
    total_return_pct: float = 0.0
    win_rate: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    avg_trade_return: float = 0.0
    last_updated: datetime = field(default_factory=datetime.utcnow)

class BaseStrategy(ABC):
    """Abstract base class for trading strategies"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = config.get('name', self.__class__.__name__)
        self.logger = logging.getLogger(f"{__name__}.{self.name}")
        
        # Strategy state
        self._state = StrategyState.INACTIVE
        self._is_active = False
        self._last_update = datetime.utcnow()
        
        # Strategy parameters
        self.symbols = config.get('symbols', ['BTC/USDT'])
        self.timeframe = config.get('timeframe', '1h')
        self.lookback_period = config.get('lookback_period', 20)
        
        # Performance tracking
        self._performance = StrategyPerformance()
        self._signal_history: List[TradingSignal] = []
        
        # Market data cache
        self._market_data_cache: Dict[str, List[MarketData]] = {}
        
        # Strategy specific parameters (to be defined in subclasses)
        self.strategy_params = config.get('params', {})
        
        self.logger.info(f"Strategy {self.name} created with config: {config}")
    
    # Abstract methods that must be implemented by subclasses
    @abstractmethod
    async def analyze_market(self, symbol: str, market_data: List[MarketData]) -> TradingSignal:
        """Analyze market data and generate trading signal"""
        pass
    
    @abstractmethod
    def validate_parameters(self) -> bool:
        """Validate strategy parameters"""
        pass
    
    @abstractmethod
    def get_required_indicators(self) -> List[str]:
        """Get list of required technical indicators"""
        pass
    
    # Strategy lifecycle methods
    async def initialize(self) -> bool:
        """Initialize the strategy"""
        try:
            self._state = StrategyState.INITIALIZING
            
            # Validate parameters
            if not self.validate_parameters():
                raise ValueError("Strategy parameter validation failed")
            
            # Initialize strategy-specific components
            await self._initialize_strategy()
            
            # Set up market data cache
            for symbol in self.symbols:
                self._market_data_cache[symbol] = []
            
            self._state = StrategyState.ACTIVE
            self._is_active = True
            self.logger.info(f"Strategy {self.name} initialized successfully")
            return True
            
        except Exception as e:
            self._state = StrategyState.ERROR
            self.logger.error(f"Failed to initialize strategy {self.name}: {e}")
            return False
    
    async def _initialize_strategy(self):
        """Strategy-specific initialization (override in subclasses)"""
        pass
    
    async def start(self) -> bool:
        """Start the strategy"""
        if self._state != StrategyState.ACTIVE:
            await self.initialize()
        
        self._is_active = True
        self.logger.info(f"Strategy {self.name} started")
        return True
    
    async def stop(self) -> bool:
        """Stop the strategy"""
        self._is_active = False
        self._state = StrategyState.INACTIVE
        self.logger.info(f"Strategy {self.name} stopped")
        return True
    
    async def pause(self) -> bool:
        """Pause the strategy"""
        if self._state == StrategyState.ACTIVE:
            self._state = StrategyState.PAUSED
            self.logger.info(f"Strategy {self.name} paused")
            return True
        return False
    
    async def resume(self) -> bool:
        """Resume the strategy"""
        if self._state == StrategyState.PAUSED:
            self._state = StrategyState.ACTIVE
            self.logger.info(f"Strategy {self.name} resumed")
            return True
        return False
    
    # Main processing method
    async def process_cycle(self, market_data_update: Dict[str, List[MarketData]]) -> List[TradingSignal]:
        """Process one strategy cycle and generate signals"""
        if not self._is_active or self._state != StrategyState.ACTIVE:
            return []
        
        signals = []
        
        try:
            # Update market data cache
            self._update_market_data_cache(market_data_update)
            
            # Process each symbol
            for symbol in self.symbols:
                if symbol in self._market_data_cache:
                    market_data = self._market_data_cache[symbol]
                    
                    # Skip if insufficient data
                    if len(market_data) < self.lookback_period:
                        continue
                    
                    # Analyze market and generate signal
                    signal = await self.analyze_market(symbol, market_data)
                    
                    if signal and signal.signal_type != SignalType.HOLD:
                        signal.strategy_name = self.name
                        signals.append(signal)
                        self._signal_history.append(signal)
                        
                        self.logger.info(
                            f"Signal generated: {signal.signal_type.value} "
                            f"{signal.symbol} at {signal.price}"
                        )
            
            # Update performance metrics
            self._performance.total_signals += len(signals)
            self._last_update = datetime.utcnow()
            
        except Exception as e:
            self.logger.error(f"Error in strategy cycle: {e}")
            self._state = StrategyState.ERROR
        
        return signals
    
    def _update_market_data_cache(self, market_data_update: Dict[str, List[MarketData]]):
        """Update market data cache with new data"""
        for symbol, new_data in market_data_update.items():
            if symbol not in self._market_data_cache:
                self._market_data_cache[symbol] = []
            
            # Add new data and maintain cache size
            self._market_data_cache[symbol].extend(new_data)
            
            # Keep only required lookback period + buffer
            max_cache_size = self.lookback_period * 2
            if len(self._market_data_cache[symbol]) > max_cache_size:
                self._market_data_cache[symbol] = self._market_data_cache[symbol][-max_cache_size:]
    
    # Signal generation helpers
    def create_signal(self, symbol: str, signal_type: SignalType, 
                     current_price: float, **kwargs) -> TradingSignal:
        """Create a trading signal with default values"""
        return TradingSignal(
            strategy_name=self.name,
            symbol=symbol,
            signal_type=signal_type,
            price=current_price,
            timeframe=self.timeframe,
            **kwargs
        )
    
    def calculate_position_size(self, symbol: str, signal: TradingSignal, 
                              available_balance: float) -> float:
        """Calculate position size based on risk management"""
        # Default position sizing (can be overridden)
        risk_per_trade = self.config.get('risk_per_trade', 0.02)  # 2%
        position_size = available_balance * risk_per_trade / signal.price
        return position_size
    
    # Technical analysis helpers
    def calculate_sma(self, prices: List[float], period: int) -> Optional[float]:
        """Calculate Simple Moving Average"""
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period
    
    def calculate_ema(self, prices: List[float], period: int) -> Optional[float]:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return None
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return None
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        if len(gains) < period:
            return None
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    # Performance and status methods
    def get_performance(self) -> StrategyPerformance:
        """Get strategy performance metrics"""
        return self._performance
    
    def update_performance(self, trade_result: Dict[str, Any]):
        """Update performance metrics with trade result"""
        if trade_result.get('status') == 'filled':
            self._performance.successful_trades += 1
            pnl = trade_result.get('pnl', 0.0)
            self._performance.total_return += pnl
        else:
            self._performance.failed_trades += 1
        
        # Calculate win rate
        total_trades = self._performance.successful_trades + self._performance.failed_trades
        if total_trades > 0:
            self._performance.win_rate = self._performance.successful_trades / total_trades
        
        self._performance.last_updated = datetime.utcnow()
    
    def get_status(self) -> Dict[str, Any]:
        """Get strategy status"""
        return {
            'name': self.name,
            'state': self._state.value,
            'is_active': self._is_active,
            'symbols': self.symbols,
            'timeframe': self.timeframe,
            'last_update': self._last_update.isoformat(),
            'performance': self._performance.__dict__,
            'total_signals': len(self._signal_history)
        }
    
    def is_healthy(self) -> bool:
        """Check if strategy is healthy"""
        return (
            self._state == StrategyState.ACTIVE and
            self._is_active and
            (datetime.utcnow() - self._last_update).total_seconds() < 3600  # 1 hour
        )
    
    def get_recent_signals(self, limit: int = 10) -> List[TradingSignal]:
        """Get recent signals"""
        return self._signal_history[-limit:] if self._signal_history else []
    
    async def cleanup(self):
        """Cleanup strategy resources"""
        self._is_active = False
        self._state = StrategyState.INACTIVE
        self._market_data_cache.clear()
        self.logger.info(f"Strategy {self.name} cleaned up")


# Strategy Manager for handling multiple strategies
class StrategyManager:
    """Manager for multiple trading strategies"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        self._strategies: Dict[str, BaseStrategy] = {}
        self._active_strategies: List[str] = []
        self._strategy_signals: List[TradingSignal] = []
    
    def add_strategy(self, strategy: BaseStrategy) -> bool:
        """Add a strategy to the manager"""
        try:
            strategy_name = strategy.name
            
            if strategy_name in self._strategies:
                self.logger.warning(f"Strategy {strategy_name} already exists, replacing")
            
            self._strategies[strategy_name] = strategy
            self.logger.info(f"Strategy {strategy_name} added to manager")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add strategy: {e}")
            return False
    
    def remove_strategy(self, strategy_name: str) -> bool:
        """Remove a strategy from the manager"""
        try:
            if strategy_name in self._strategies:
                # Stop strategy if active
                if strategy_name in self._active_strategies:
                    asyncio.create_task(self._strategies[strategy_name].stop())
                    self._active_strategies.remove(strategy_name)
                
                del self._strategies[strategy_name]
                self.logger.info(f"Strategy {strategy_name} removed from manager")
                return True
            else:
                self.logger.warning(f"Strategy {strategy_name} not found")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to remove strategy {strategy_name}: {e}")
            return False
    
    async def activate_strategy(self, strategy_name: str) -> bool:
        """Activate a strategy"""
        try:
            if strategy_name not in self._strategies:
                raise ValueError(f"Strategy {strategy_name} not found")
            
            strategy = self._strategies[strategy_name]
            
            if await strategy.start():
                if strategy_name not in self._active_strategies:
                    self._active_strategies.append(strategy_name)
                self.logger.info(f"Strategy {strategy_name} activated")
                return True
            else:
                self.logger.error(f"Failed to start strategy {strategy_name}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to activate strategy {strategy_name}: {e}")
            return False
    
    async def deactivate_strategy(self, strategy_name: str) -> bool:
        """Deactivate a strategy"""
        try:
            if strategy_name not in self._strategies:
                return False
            
            strategy = self._strategies[strategy_name]
            
            if await strategy.stop():
                if strategy_name in self._active_strategies:
                    self._active_strategies.remove(strategy_name)
                self.logger.info(f"Strategy {strategy_name} deactivated")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to deactivate strategy {strategy_name}: {e}")
            return False
    
    async def process_cycle(self, market_data_update: Dict[str, List[MarketData]]) -> List[TradingSignal]:
        """Process cycle for all active strategies"""
        all_signals = []
        
        for strategy_name in self._active_strategies:
            try:
                strategy = self._strategies[strategy_name]
                signals = await strategy.process_cycle(market_data_update)
                all_signals.extend(signals)
                
            except Exception as e:
                self.logger.error(f"Error processing strategy {strategy_name}: {e}")
        
        # Store signals for history
        self._strategy_signals.extend(all_signals)
        
        # Keep only recent signals (last 1000)
        if len(self._strategy_signals) > 1000:
            self._strategy_signals = self._strategy_signals[-1000:]
        
        return all_signals
    
    def get_strategies(self) -> Dict[str, BaseStrategy]:
        """Get all strategies"""
        return self._strategies.copy()
    
    def get_active_strategies(self) -> List[str]:
        """Get list of active strategy names"""
        return self._active_strategies.copy()
    
    def get_strategy_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all strategies"""
        status = {}
        for name, strategy in self._strategies.items():
            status[name] = strategy.get_status()
            status[name]['is_active'] = name in self._active_strategies
        return status
    
    def get_recent_signals(self, limit: int = 50) -> List[TradingSignal]:
        """Get recent signals from all strategies"""
        return self._strategy_signals[-limit:] if self._strategy_signals else []
    
    def is_healthy(self) -> bool:
        """Check if strategy manager is healthy"""
        if not self._active_strategies:
            return True  # No strategies is considered healthy
        
        healthy_strategies = 0
        for strategy_name in self._active_strategies:
            if strategy_name in self._strategies:
                if self._strategies[strategy_name].is_healthy():
                    healthy_strategies += 1
        
        # Consider healthy if at least 80% of strategies are healthy
        return healthy_strategies >= len(self._active_strategies) * 0.8
    
    async def cleanup(self):
        """Cleanup all strategies"""
        for strategy in self._strategies.values():
            await strategy.cleanup()
        
        self._strategies.clear()
        self._active_strategies.clear()
        self._strategy_signals.clear()
        
        self.logger.info("Strategy manager cleaned up")