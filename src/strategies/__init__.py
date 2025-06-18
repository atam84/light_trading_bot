# src/strategies/__init__.py

"""
Trading Bot Strategy Framework

A comprehensive strategy framework for cryptocurrency trading that provides:
- Multiple strategy types (simple, grid, indicator-based)
- Strategy management and lifecycle control
- Performance analytics and backtesting
- Signal processing and filtering
- Real-time strategy execution
- Risk management integration

Usage:
    from strategies import StrategyFramework
    
    # Initialize framework
    framework = StrategyFramework()
    
    # Create a quick strategy
    strategy_id = framework.create_quick_strategy(
        profile="balanced",
        symbol="BTC/USDT",
        timeframe="4h"
    )
    
    # Start real-time processing
    await framework.start_real_time_processing(["BTC/USDT"], ["4h"])
"""

from typing import Dict, List, Optional, Any
import logging

# Import core components
from .base import (
    BaseStrategy, Signal, SignalAction, SignalType, 
    MarketData, StrategyConfig, StrategyType, IndicatorMixin
)

# Import strategy implementations
from .simple import BuyLowSellHighStrategy, DCAStrategy, VolatilityBreakoutStrategy
from .grid import GridTradingStrategy
from .indicators import RSIStrategy, MovingAverageCrossStrategy, MACDStrategy, ComboIndicatorStrategy

# Import management components
from .manager import StrategyManager, StrategyExecution
from .config import StrategyConfigManager, StrategyTemplate, ConfigValidationError
from .factory import StrategyFactory

# Import analytics and processing
from .analytics import PerformanceAnalyzer, PerformanceMetrics, TradeAnalysis
from .signals import SignalProcessor, ProcessedSignal, SignalStrength, SignalStatus

# Import integration
from .integration import StrategyIntegration, BacktestConfig, BacktestResult

logger = logging.getLogger(__name__)

# Framework version
__version__ = "1.0.0"

# Available strategy types
AVAILABLE_STRATEGIES = {
    'simple': {
        'buy_low_sell_high': BuyLowSellHighStrategy,
        'dca': DCAStrategy,
        'volatility_breakout': VolatilityBreakoutStrategy
    },
    'grid': {
        'grid_trading': GridTradingStrategy
    },
    'indicator': {
        'rsi': RSIStrategy,
        'ma_cross': MovingAverageCrossStrategy,
        'macd': MACDStrategy,
        'combo_indicator': ComboIndicatorStrategy
    }
}

# Quick access profiles
QUICK_PROFILES = ['conservative', 'balanced', 'aggressive', 'scalping', 'grid_stable']

class StrategyFramework:
    """
    Main strategy framework interface that provides unified access to all components
    """
    
    def __init__(self, data_dir: str = "data"):
        """
        Initialize the strategy framework
        
        Args:
            data_dir: Directory for data storage
        """
        self.integration = StrategyIntegration(data_dir)
        
        # Shortcuts to main components
        self.factory = self.integration.strategy_factory
        self.manager = self.integration.strategy_manager
        self.config_manager = self.integration.config_manager
        self.signal_processor = self.integration.signal_processor
        self.performance_analyzer = self.integration.performance_analyzer
        
        logger.info(f"Strategy Framework v{__version__} initialized")
    
    # Quick Strategy Creation
    def create_quick_strategy(self, profile: str, symbol: str, timeframe: str = "1h",
                             budget: float = 100.0) -> str:
        """Create strategy using predefined profile"""
        return self.factory.create_quick_strategy(profile, symbol, timeframe, budget)
    
    def create_custom_strategy(self, name: str, strategy_type: str, symbol: str,
                              **kwargs) -> str:
        """Create custom strategy with specific parameters"""
        return self.factory.create_custom_strategy(name, strategy_type, symbol, **kwargs)
    
    def create_from_template(self, template: str, name: str, symbol: str, **kwargs) -> str:
        """Create strategy from predefined template"""
        return self.factory.create_from_template(template, name, symbol, **kwargs)
    
    # Strategy Management
    def list_strategies(self) -> List[Dict[str, Any]]:
        """List all strategies"""
        return self.manager.list_strategies()
    
    def activate_strategy(self, strategy_id: str) -> bool:
        """Activate strategy"""
        return self.manager.activate_strategy(strategy_id)
    
    def deactivate_strategy(self, strategy_id: str) -> bool:
        """Deactivate strategy"""
        return self.manager.deactivate_strategy(strategy_id)
    
    def remove_strategy(self, strategy_id: str) -> bool:
        """Remove strategy"""
        return self.manager.remove_strategy(strategy_id)
    
    def get_strategy_status(self, strategy_id: str) -> Dict[str, Any]:
        """Get strategy status"""
        return self.manager.get_strategy_performance(strategy_id)
    
    # Backtesting
    async def run_backtest(self, strategy_id: str, days: int = 30, 
                          initial_balance: float = 10000.0) -> BacktestResult:
        """Run quick backtest"""
        from datetime import datetime, timedelta
        
        config = BacktestConfig(
            start_date=datetime.now() - timedelta(days=days),
            end_date=datetime.now(),
            initial_balance=initial_balance
        )
        return await self.integration.run_backtest(strategy_id, config)
    
    async def create_and_test_strategy(self, template: str, symbol: str, 
                                     test_days: int = 30, **kwargs) -> Dict[str, Any]:
        """Create strategy and run test"""
        return await self.integration.create_and_test_strategy(
            template, symbol, test_days=test_days, custom_params=kwargs
        )
    
    # Real-time Processing
    async def start_real_time(self, symbols: List[str], timeframes: List[str] = None):
        """Start real-time strategy processing"""
        if timeframes is None:
            timeframes = ["1h"]
        await self.integration.start_real_time_processing(symbols, timeframes)
    
    def stop_real_time(self):
        """Stop real-time processing"""
        self.integration.stop_real_time_processing()
    
    # Performance Analysis
    def get_performance_metrics(self, strategy_id: str) -> PerformanceMetrics:
        """Get strategy performance metrics"""
        return self.performance_analyzer.calculate_metrics(strategy_id)
    
    def compare_strategies(self, strategy_ids: List[str]) -> Dict[str, Any]:
        """Compare multiple strategies"""
        return self.performance_analyzer.compare_strategies(strategy_ids)
    
    def generate_report(self, strategy_id: str) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        return self.performance_analyzer.generate_performance_report(strategy_id)
    
    # Configuration Management
    def list_templates(self) -> List[Dict[str, Any]]:
        """List available strategy templates"""
        return self.config_manager.list_templates()
    
    def save_strategy_config(self, strategy_id: str, config_name: str = None) -> bool:
        """Save strategy configuration"""
        strategy = self.manager.get_strategy(strategy_id)
        if not strategy:
            return False
        
        name = config_name or f"{strategy.config.name}_saved"
        return self.config_manager.save_config(strategy.config)
    
    def load_strategy_config(self, config_name: str) -> Optional[str]:
        """Load strategy from saved configuration"""
        config = self.config_manager.load_config(config_name)
        if config:
            return self.manager.create_strategy(config)
        return None
    
    # Portfolio Management
    def create_portfolio(self, symbols: List[str], profile: str = "balanced",
                        total_budget: float = 1000.0) -> List[str]:
        """Create portfolio of strategies"""
        return self.factory.create_portfolio_strategies(symbols, profile, total_budget=total_budget)
    
    async def export_portfolio(self, strategy_ids: List[str], filename: str = None) -> bool:
        """Export strategy portfolio"""
        if filename is None:
            from datetime import datetime
            filename = f"portfolio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        return await self.integration.export_strategy_portfolio(strategy_ids, filename)
    
    async def import_portfolio(self, filename: str) -> Dict[str, Any]:
        """Import strategy portfolio"""
        return await self.integration.import_strategy_portfolio(filename)
    
    # Signal Management
    def get_pending_signals(self, symbol: str = None) -> List[ProcessedSignal]:
        """Get pending signals"""
        return self.signal_processor.get_pending_signals(symbol)
    
    def get_confirmed_signals(self, symbol: str = None) -> List[ProcessedSignal]:
        """Get confirmed signals"""
        return self.signal_processor.get_confirmed_signals(symbol)
    
    def add_signal_callback(self, callback):
        """Add callback for trading signals"""
        self.integration.add_trade_callback(callback)
    
    # System Status
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return self.integration.get_system_status()
    
    def get_recommendations(self, symbol: str, timeframe: str = "4h",
                           risk_tolerance: str = "medium") -> List[Dict[str, Any]]:
        """Get strategy recommendations"""
        return self.factory.get_strategy_recommendations(
            symbol, timeframe, risk_tolerance
        )
    
    # Utility Methods
    def get_available_strategies(self) -> Dict[str, List[str]]:
        """Get available strategy types"""
        return {category: list(strategies.keys()) for category, strategies in AVAILABLE_STRATEGIES.items()}
    
    def get_quick_profiles(self) -> List[str]:
        """Get available quick profiles"""
        return QUICK_PROFILES.copy()
    
    def validate_symbol(self, symbol: str) -> bool:
        """Validate trading symbol format"""
        return "/" in symbol and len(symbol.split("/")) == 2
    
    def validate_timeframe(self, timeframe: str) -> bool:
        """Validate timeframe format"""
        valid_timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '8h', '1d', '1w']
        return timeframe in valid_timeframes

# Convenience functions for quick access
def create_strategy(profile: str, symbol: str, timeframe: str = "1h", budget: float = 100.0) -> str:
    """Quick strategy creation function"""
    framework = StrategyFramework()
    return framework.create_quick_strategy(profile, symbol, timeframe, budget)

async def test_strategy(template: str, symbol: str, days: int = 30) -> Dict[str, Any]:
    """Quick strategy testing function"""
    framework = StrategyFramework()
    return await framework.create_and_test_strategy(template, symbol, days)

def get_strategy_recommendations(symbol: str, risk_level: str = "medium") -> List[Dict[str, Any]]:
    """Get strategy recommendations"""
    framework = StrategyFramework()
    return framework.get_recommendations(symbol, risk_tolerance=risk_level)

# Export main classes and functions
__all__ = [
    # Main framework
    'StrategyFramework',
    
    # Core components
    'BaseStrategy', 'Signal', 'SignalAction', 'SignalType', 'MarketData', 
    'StrategyConfig', 'StrategyType',
    
    # Strategy implementations
    'BuyLowSellHighStrategy', 'DCAStrategy', 'VolatilityBreakoutStrategy',
    'GridTradingStrategy', 'RSIStrategy', 'MovingAverageCrossStrategy', 
    'MACDStrategy', 'ComboIndicatorStrategy',
    
    # Management
    'StrategyManager', 'StrategyConfigManager', 'StrategyFactory',
    
    # Analytics
    'PerformanceAnalyzer', 'PerformanceMetrics', 'TradeAnalysis',
    
    # Signal processing
    'SignalProcessor', 'ProcessedSignal', 'SignalStrength', 'SignalStatus',
    
    # Integration
    'StrategyIntegration', 'BacktestConfig', 'BacktestResult',
    
    # Convenience functions
    'create_strategy', 'test_strategy', 'get_strategy_recommendations',
    
    # Constants
    'AVAILABLE_STRATEGIES', 'QUICK_PROFILES', '__version__'
]

# Framework information
def get_framework_info() -> Dict[str, Any]:
    """Get framework information"""
    return {
        'version': __version__,
        'available_strategies': AVAILABLE_STRATEGIES,
        'quick_profiles': QUICK_PROFILES,
        'components': [
            'Strategy Management',
            'Signal Processing', 
            'Performance Analytics',
            'Backtesting Engine',
            'Configuration Management',
            'Real-time Processing'
        ]
    }