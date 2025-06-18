# src/strategies/manager.py

from typing import Dict, List, Optional, Any, Type, Callable
from datetime import datetime
import asyncio
import logging
from dataclasses import dataclass

from .base import BaseStrategy, Signal, MarketData, StrategyConfig, StrategyType
from .simple import BuyLowSellHighStrategy, DCAStrategy, VolatilityBreakoutStrategy
from .grid import GridTradingStrategy
from .indicators import RSIStrategy, MovingAverageCrossStrategy, MACDStrategy, ComboIndicatorStrategy

logger = logging.getLogger(__name__)

@dataclass
class StrategyExecution:
    """Strategy execution context"""
    strategy: BaseStrategy
    last_execution: Optional[datetime] = None
    execution_count: int = 0
    last_signal: Optional[Signal] = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []

class StrategyManager:
    """
    Manages strategy lifecycle, execution, and coordination
    """
    
    def __init__(self):
        self.strategies: Dict[str, StrategyExecution] = {}
        self.strategy_registry: Dict[StrategyType, Type[BaseStrategy]] = {}
        self.signal_callbacks: List[Callable[[Signal], None]] = []
        self.running = False
        
        # Register available strategies
        self._register_strategies()
        
        logger.info("Strategy manager initialized")
    
    def _register_strategies(self):
        """Register available strategy classes"""
        self.strategy_registry = {
            StrategyType.SIMPLE: BuyLowSellHighStrategy,
            StrategyType.GRID: GridTradingStrategy,
            StrategyType.INDICATOR: ComboIndicatorStrategy,
            StrategyType.CUSTOM: BaseStrategy
        }
        
        # Register named strategies
        self.named_strategies = {
            'buy_low_sell_high': BuyLowSellHighStrategy,
            'dca': DCAStrategy,
            'volatility_breakout': VolatilityBreakoutStrategy,
            'grid_trading': GridTradingStrategy,
            'rsi': RSIStrategy,
            'ma_cross': MovingAverageCrossStrategy,
            'macd': MACDStrategy,
            'combo_indicator': ComboIndicatorStrategy
        }
    
    def create_strategy(self, config: StrategyConfig) -> str:
        """
        Create and register a new strategy
        
        Args:
            config: Strategy configuration
            
        Returns:
            Strategy ID
        """
        # Validate configuration
        if not config.name:
            raise ValueError("Strategy name is required")
        
        if config.name in self.strategies:
            raise ValueError(f"Strategy '{config.name}' already exists")
        
        # Determine strategy class
        strategy_class = None
        
        # Check by strategy type
        if config.strategy_type in self.strategy_registry:
            strategy_class = self.strategy_registry[config.strategy_type]
        
        # Check by name if specified in parameters
        strategy_name = config.parameters.get('strategy_class')
        if strategy_name and strategy_name in self.named_strategies:
            strategy_class = self.named_strategies[strategy_name]
        
        if not strategy_class:
            raise ValueError(f"Unknown strategy type: {config.strategy_type}")
        
        # Create strategy instance
        try:
            strategy = strategy_class(config)
            
            # Validate strategy
            if not strategy.validate_config():
                raise ValueError(f"Invalid strategy configuration for {config.name}")
            
            # Register strategy
            self.strategies[config.name] = StrategyExecution(strategy=strategy)
            
            logger.info(f"Strategy '{config.name}' created successfully")
            return config.name
            
        except Exception as e:
            logger.error(f"Failed to create strategy '{config.name}': {e}")
            raise
    
    def remove_strategy(self, strategy_id: str) -> bool:
        """
        Remove a strategy
        
        Args:
            strategy_id: Strategy identifier
            
        Returns:
            True if removed successfully
        """
        if strategy_id not in self.strategies:
            logger.warning(f"Strategy '{strategy_id}' not found")
            return False
        
        # Stop strategy if running
        self.strategies[strategy_id].strategy.active = False
        
        # Remove from registry
        del self.strategies[strategy_id]
        
        logger.info(f"Strategy '{strategy_id}' removed")
        return True
    
    def get_strategy(self, strategy_id: str) -> Optional[BaseStrategy]:
        """
        Get strategy by ID
        
        Args:
            strategy_id: Strategy identifier
            
        Returns:
            Strategy instance or None
        """
        execution = self.strategies.get(strategy_id)
        return execution.strategy if execution else None
    
    def list_strategies(self) -> List[Dict[str, Any]]:
        """
        List all registered strategies
        
        Returns:
            List of strategy information
        """
        strategies = []
        
        for strategy_id, execution in self.strategies.items():
            strategy = execution.strategy
            status = strategy.get_status()
            
            strategies.append({
                'id': strategy_id,
                'name': strategy.config.name,
                'type': strategy.config.strategy_type.value,
                'active': strategy.active,
                'timeframe': strategy.config.timeframe,
                'symbols': strategy.config.symbols,
                'last_execution': execution.last_execution.isoformat() if execution.last_execution else None,
                'execution_count': execution.execution_count,
                'last_signal': execution.last_signal.action.value if execution.last_signal else None,
                'performance': status.get('performance', {}),
                'errors': execution.errors[-5:]  # Last 5 errors
            })
        
        return strategies
    
    def activate_strategy(self, strategy_id: str) -> bool:
        """
        Activate a strategy
        
        Args:
            strategy_id: Strategy identifier
            
        Returns:
            True if activated successfully
        """
        strategy = self.get_strategy(strategy_id)
        if not strategy:
            return False
        
        strategy.active = True
        logger.info(f"Strategy '{strategy_id}' activated")
        return True
    
    def deactivate_strategy(self, strategy_id: str) -> bool:
        """
        Deactivate a strategy
        
        Args:
            strategy_id: Strategy identifier
            
        Returns:
            True if deactivated successfully
        """
        strategy = self.get_strategy(strategy_id)
        if not strategy:
            return False
        
        strategy.active = False
        logger.info(f"Strategy '{strategy_id}' deactivated")
        return True
    
    async def execute_strategies(self, market_data: MarketData) -> List[Signal]:
        """
        Execute all active strategies with market data
        
        Args:
            market_data: Current market data
            
        Returns:
            List of generated signals
        """
        signals = []
        
        for strategy_id, execution in self.strategies.items():
            strategy = execution.strategy
            
            # Skip inactive strategies
            if not strategy.active:
                continue
            
            # Skip if symbol not in strategy's symbol list (if specified)
            if strategy.config.symbols and market_data.symbol not in strategy.config.symbols:
                continue
            
            # Skip if timeframe doesn't match
            if strategy.config.timeframe != market_data.timeframe:
                continue
            
            try:
                # Execute strategy analysis
                signal = await strategy.analyze(market_data)
                
                if signal:
                    # Add signal to strategy
                    strategy.add_signal(signal)
                    signals.append(signal)
                    
                    # Update execution context
                    execution.last_signal = signal
                    
                    # Notify callbacks
                    for callback in self.signal_callbacks:
                        try:
                            await callback(signal) if asyncio.iscoroutinefunction(callback) else callback(signal)
                        except Exception as e:
                            logger.error(f"Signal callback error: {e}")
                
                # Update execution stats
                execution.last_execution = datetime.now()
                execution.execution_count += 1
                
            except Exception as e:
                error_msg = f"Strategy '{strategy_id}' execution error: {e}"
                logger.error(error_msg)
                execution.errors.append(error_msg)
                
                # Keep only last 10 errors
                if len(execution.errors) > 10:
                    execution.errors = execution.errors[-10:]
        
        return signals
    
    def add_signal_callback(self, callback: Callable[[Signal], None]):
        """
        Add callback for signal notifications
        
        Args:
            callback: Function to call when signal is generated
        """
        self.signal_callbacks.append(callback)
    
    def remove_signal_callback(self, callback: Callable[[Signal], None]):
        """
        Remove signal callback
        
        Args:
            callback: Callback function to remove
        """
        if callback in self.signal_callbacks:
            self.signal_callbacks.remove(callback)
    
    def get_required_indicators(self, symbols: List[str], timeframes: List[str]) -> Dict[str, List[str]]:
        """
        Get all required indicators for active strategies
        
        Args:
            symbols: List of symbols to check
            timeframes: List of timeframes to check
            
        Returns:
            Dictionary mapping (symbol, timeframe) to required indicators
        """
        required_indicators = {}
        
        for strategy_id, execution in self.strategies.items():
            strategy = execution.strategy
            
            if not strategy.active:
                continue
            
            # Get strategy's required indicators
            indicators = strategy.get_required_indicators()
            if not indicators:
                continue
            
            # Check for matching symbols and timeframes
            strategy_symbols = strategy.config.symbols if strategy.config.symbols else symbols
            strategy_timeframe = strategy.config.timeframe
            
            for symbol in strategy_symbols:
                if symbol in symbols and strategy_timeframe in timeframes:
                    key = f"{symbol}_{strategy_timeframe}"
                    if key not in required_indicators:
                        required_indicators[key] = set()
                    required_indicators[key].update(indicators)
        
        # Convert sets to lists
        return {k: list(v) for k, v in required_indicators.items()}
    
    def update_position(self, strategy_id: str, symbol: str, side: str, price: float, amount: float):
        """
        Update position information for a strategy
        
        Args:
            strategy_id: Strategy identifier
            symbol: Trading symbol
            side: 'buy' or 'sell'
            price: Entry price
            amount: Position size
        """
        strategy = self.get_strategy(strategy_id)
        if strategy:
            strategy.update_position(symbol, side, price, amount)
    
    def close_position(self, strategy_id: str, symbol: str, exit_price: float):
        """
        Close position for a strategy
        
        Args:
            strategy_id: Strategy identifier
            symbol: Trading symbol
            exit_price: Exit price
        """
        strategy = self.get_strategy(strategy_id)
        if strategy:
            strategy.close_position(symbol, exit_price)
    
    def get_strategy_performance(self, strategy_id: str) -> Dict[str, Any]:
        """
        Get strategy performance metrics
        
        Args:
            strategy_id: Strategy identifier
            
        Returns:
            Performance metrics dictionary
        """
        strategy = self.get_strategy(strategy_id)
        if not strategy:
            return {}
        
        return strategy.get_status()
    
    def reset_strategy(self, strategy_id: str) -> bool:
        """
        Reset strategy state
        
        Args:
            strategy_id: Strategy identifier
            
        Returns:
            True if reset successfully
        """
        strategy = self.get_strategy(strategy_id)
        if not strategy:
            return False
        
        strategy.reset()
        
        # Reset execution context
        execution = self.strategies[strategy_id]
        execution.last_execution = None
        execution.execution_count = 0
        execution.last_signal = None
        execution.errors.clear()
        
        logger.info(f"Strategy '{strategy_id}' reset")
        return True
    
    def stop_all_strategies(self):
        """Stop all strategies"""
        for strategy_id in list(self.strategies.keys()):
            self.deactivate_strategy(strategy_id)
        
        self.running = False
        logger.info("All strategies stopped")
    
    def get_manager_status(self) -> Dict[str, Any]:
        """
        Get strategy manager status
        
        Returns:
            Manager status information
        """
        active_strategies = sum(1 for execution in self.strategies.values() 
                              if execution.strategy.active)
        
        total_signals = sum(len(execution.strategy.signals_history) 
                          for execution in self.strategies.values())
        
        total_positions = sum(len([p for p in execution.strategy.positions.values() 
                                 if p.get('status') == 'open'])
                            for execution in self.strategies.values())
        
        return {
            'total_strategies': len(self.strategies),
            'active_strategies': active_strategies,
            'total_signals_generated': total_signals,
            'total_open_positions': total_positions,
            'available_strategy_types': list(self.named_strategies.keys()),
            'running': self.running
        }