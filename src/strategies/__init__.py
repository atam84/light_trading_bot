"""
Trading strategies module.
"""
# Import base classes
from .base import BaseStrategy, StrategyMixin, SignalType, SignalStrength, TradingSignal

# Import strategy implementations (with error handling)
try:
    from .simple import SimpleBuySellStrategy
except ImportError:
    SimpleBuySellStrategy = None

try:
    from .grid import GridTradingStrategy
except ImportError:
    GridTradingStrategy = None
    
try:
    from .indicator import IndicatorBasedStrategy
except ImportError:
    IndicatorBasedStrategy = None

__all__ = [
    'BaseStrategy',
    'StrategyMixin',
    'SignalType',
    'SignalStrength', 
    'TradingSignal'
]

# Add available strategies to exports
if SimpleBuySellStrategy:
    __all__.append('SimpleBuySellStrategy')
if GridTradingStrategy:
    __all__.append('GridTradingStrategy')
if IndicatorBasedStrategy:
    __all__.append('IndicatorBasedStrategy')
