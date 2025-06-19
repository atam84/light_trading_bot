#!/usr/bin/env python3
# scripts/fix_imports.py - Python import diagnostic and fix tool

import os
import sys
import importlib.util
from pathlib import Path
import traceback

class ImportFixer:
    """Diagnose and fix import issues in the trading bot."""
    
    def __init__(self, src_path="src"):
        self.src_path = Path(src_path)
        self.issues = []
        self.fixes = []
        
    def log_issue(self, issue):
        """Log an import issue."""
        self.issues.append(issue)
        print(f"❌ ISSUE: {issue}")
        
    def log_fix(self, fix):
        """Log a fix applied."""
        self.fixes.append(fix)
        print(f"✅ FIX: {fix}")
        
    def check_file_exists(self, filepath):
        """Check if a file exists."""
        path = self.src_path / filepath
        return path.exists()
        
    def create_file(self, filepath, content):
        """Create a file with content."""
        path = self.src_path / filepath
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            f.write(content)
        self.log_fix(f"Created {filepath}")
        
    def read_file(self, filepath):
        """Read file content."""
        path = self.src_path / filepath
        if path.exists():
            with open(path, 'r') as f:
                return f.read()
        return ""
        
    def write_file(self, filepath, content):
        """Write content to file."""
        path = self.src_path / filepath
        with open(path, 'w') as f:
            f.write(content)
        self.log_fix(f"Updated {filepath}")
        
    def test_import(self, module_path):
        """Test if a module can be imported."""
        try:
            # Add src to Python path temporarily
            original_path = sys.path.copy()
            sys.path.insert(0, str(self.src_path.absolute()))
            
            spec = importlib.util.spec_from_file_location(
                module_path, 
                self.src_path / module_path.replace('.', '/') / '__init__.py'
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return True, None
        except Exception as e:
            return False, str(e)
        finally:
            sys.path = original_path
            
        return False, "Module not found"
        
    def fix_strategies_base_init(self):
        """Fix strategies/base/__init__.py"""
        init_path = "strategies/base/__init__.py"
        
        if not self.check_file_exists(init_path):
            self.log_issue(f"Missing {init_path}")
            
        content = '''"""
Base strategy framework exports.
"""
from .base_strategy import BaseStrategy
from .strategy_mixin import StrategyMixin
from .signal_types import SignalType, SignalStrength, TradingSignal

__all__ = [
    'BaseStrategy',
    'StrategyMixin', 
    'SignalType',
    'SignalStrength',
    'TradingSignal'
]
'''
        self.create_file(init_path, content)
        
    def fix_base_strategy(self):
        """Fix strategies/base/base_strategy.py"""
        strategy_path = "strategies/base/base_strategy.py"
        
        if not self.check_file_exists(strategy_path):
            self.log_issue(f"Missing {strategy_path}")
            
        content = '''"""
Base strategy class for trading bot.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class BaseStrategy(ABC):
    """Abstract base class for all trading strategies."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize strategy with configuration."""
        self.config = config
        self.name = config.get('name', self.__class__.__name__)
        self.is_active = False
        self.symbol = config.get('symbol', 'BTC/USDT')
        self.timeframe = config.get('timeframe', '1h')
        
    @abstractmethod
    async def should_buy(self, data: Dict[str, Any]) -> Tuple[bool, float]:
        """
        Determine if should buy based on market data.
        
        Args:
            data: Market data including OHLCV and indicators
            
        Returns:
            Tuple[bool, float]: (should_buy, confidence_score)
        """
        pass
        
    @abstractmethod
    async def should_sell(self, data: Dict[str, Any]) -> Tuple[bool, float]:
        """
        Determine if should sell based on market data.
        
        Args:
            data: Market data including OHLCV and indicators
            
        Returns:
            Tuple[bool, float]: (should_sell, confidence_score)
        """
        pass
        
    async def initialize(self) -> None:
        """Initialize strategy resources."""
        self.is_active = True
        logger.info(f"Strategy {self.name} initialized")
        
    async def cleanup(self) -> None:
        """Cleanup strategy resources."""
        self.is_active = False
        logger.info(f"Strategy {self.name} cleaned up")
        
    def get_config(self) -> Dict[str, Any]:
        """Get strategy configuration."""
        return self.config.copy()
        
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """Update strategy configuration."""
        self.config.update(new_config)
        logger.info(f"Strategy {self.name} configuration updated")
'''
        self.create_file(strategy_path, content)
        
    def fix_signal_types(self):
        """Fix strategies/base/signal_types.py"""
        signal_path = "strategies/base/signal_types.py"
        
        content = '''"""
Signal types and definitions for trading strategies.
"""
from enum import Enum
from dataclasses import dataclass
from typing import Optional
import time

class SignalType(Enum):
    """Types of trading signals."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    
class SignalStrength(Enum):
    """Signal strength levels."""
    WEAK = "weak"
    MEDIUM = "medium"
    STRONG = "strong"

@dataclass
class TradingSignal:
    """Trading signal data structure."""
    signal_type: SignalType
    strength: SignalStrength
    confidence: float
    reason: str
    timestamp: Optional[float] = None
    metadata: Optional[dict] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
'''
        self.create_file(signal_path, content)
        
    def fix_strategy_mixin(self):
        """Fix strategies/base/strategy_mixin.py"""
        mixin_path = "strategies/base/strategy_mixin.py"
        
        content = '''"""
Strategy mixin classes for common functionality.
"""
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class StrategyMixin:
    """Mixin class providing common strategy functionality."""
    
    def log_signal(self, signal_type: str, confidence: float, reason: str) -> None:
        """Log trading signal."""
        logger.info(f"{self.name}: {signal_type} signal (confidence: {confidence:.2f}) - {reason}")
        
    def validate_config(self, required_keys: List[str]) -> bool:
        """Validate strategy configuration."""
        missing_keys = [key for key in required_keys if key not in self.config]
        if missing_keys:
            logger.error(f"Missing configuration keys: {missing_keys}")
            return False
        return True
        
    def get_indicator_value(self, data: Dict[str, Any], indicator: str, default: float = 0.0) -> float:
        """Get indicator value from market data."""
        return data.get('indicators', {}).get(indicator, default)
'''
        self.create_file(mixin_path, content)
        
    def fix_strategies_init(self):
        """Fix strategies/__init__.py"""
        init_path = "strategies/__init__.py"
        
        content = '''"""
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
'''
        self.create_file(init_path, content)
        
    def ensure_init_files(self):
        """Ensure all directories have __init__.py files."""
        directories = [
            "strategies",
            "strategies/base",
            "strategies/simple", 
            "strategies/grid",
            "strategies/indicator",
            "core",
            "api_clients",
            "database",
            "interfaces",
            "interfaces/cli",
            "interfaces/web", 
            "interfaces/telegram",
            "utils"
        ]
        
        for directory in directories:
            init_path = f"{directory}/__init__.py"
            if not self.check_file_exists(init_path):
                self.create_file(init_path, f'"""{directory} module."""\n')
                
    def test_critical_imports(self):
        """Test critical imports."""
        critical_imports = [
            ("BaseStrategy", "from strategies.base import BaseStrategy"),
            ("strategies module", "import strategies"),
            ("TradingEngine", "from core.trading_engine import TradingEngine"),
        ]
        
        print("\\n🧪 Testing critical imports...")
        
        # Add src to Python path
        original_path = sys.path.copy()
        sys.path.insert(0, str(self.src_path.absolute()))
        
        try:
            for name, import_statement in critical_imports:
                try:
                    exec(import_statement)
                    print(f"✅ {name}: OK")
                except Exception as e:
                    print(f"❌ {name}: {e}")
                    self.log_issue(f"Import failed: {import_statement} - {e}")
        finally:
            sys.path = original_path
            
    def run_diagnostics(self):
        """Run complete import diagnostics and fixes."""
        print("🔍 Starting Trading Bot Import Diagnostics...")
        print("=" * 50)
        
        # Check if we're in the right place
        if not self.src_path.exists():
            print(f"❌ Source directory '{self.src_path}' not found!")
            print("Please run this script from the project root directory.")
            return False
            
        # Apply fixes
        print("\\n🛠️ Applying fixes...")
        self.ensure_init_files()
        self.fix_strategies_base_init()
        self.fix_base_strategy()
        self.fix_signal_types()
        self.fix_strategy_mixin()
        self.fix_strategies_init()
        
        # Test imports
        self.test_critical_imports()
        
        # Summary
        print("\\n📊 Summary:")
        print(f"Issues found: {len(self.issues)}")
        print(f"Fixes applied: {len(self.fixes)}")
        
        if self.issues:
            print("\\n❌ Remaining issues:")
            for issue in self.issues:
                print(f"  - {issue}")
        else:
            print("\\n✅ All import issues resolved!")
            
        print("\\n🚀 Next steps:")
        print("1. Restart the application:")
        print("   docker-compose down && docker-compose up -d")
        print("2. Check logs:")
        print("   docker logs trading-bot -f")
        
        return len(self.issues) == 0

if __name__ == "__main__":
    fixer = ImportFixer()
    success = fixer.run_diagnostics()
    sys.exit(0 if success else 1)

