#!/bin/bash
# scripts/fix_imports.sh - Fix import issues in trading bot

set -e

echo "🔍 Trading Bot Import Issues Diagnostic & Fix Script"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "src/main.py" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

print_status "Starting import diagnostics..."

# 1. Check strategy base __init__.py
print_status "Checking strategies/base/__init__.py..."
if [ ! -f "src/strategies/base/__init__.py" ]; then
    print_warning "strategies/base/__init__.py not found, creating..."
    mkdir -p src/strategies/base
    cat > src/strategies/base/__init__.py << 'EOF'
"""
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
EOF
    print_success "Created strategies/base/__init__.py"
else
    print_status "strategies/base/__init__.py exists, checking content..."
    if ! grep -q "BaseStrategy" src/strategies/base/__init__.py; then
        print_warning "BaseStrategy not exported, fixing..."
        cat > src/strategies/base/__init__.py << 'EOF'
"""
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
EOF
        print_success "Fixed strategies/base/__init__.py exports"
    fi
fi

# 2. Check if base_strategy.py exists
print_status "Checking strategies/base/base_strategy.py..."
if [ ! -f "src/strategies/base/base_strategy.py" ]; then
    print_error "base_strategy.py not found!"
    print_status "Creating minimal base_strategy.py..."
    cat > src/strategies/base/base_strategy.py << 'EOF'
"""
Base strategy class for trading bot.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class BaseStrategy(ABC):
    """Abstract base class for all trading strategies."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize strategy with configuration."""
        self.config = config
        self.name = config.get('name', self.__class__.__name__)
        self.is_active = False
        
    @abstractmethod
    async def should_buy(self, data: Dict[str, Any]) -> Tuple[bool, float]:
        """
        Determine if should buy based on market data.
        
        Returns:
            Tuple[bool, float]: (should_buy, confidence_score)
        """
        pass
        
    @abstractmethod
    async def should_sell(self, data: Dict[str, Any]) -> Tuple[bool, float]:
        """
        Determine if should sell based on market data.
        
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
EOF
    print_success "Created minimal base_strategy.py"
fi

# 3. Check strategies main __init__.py
print_status "Checking strategies/__init__.py..."
if [ ! -f "src/strategies/__init__.py" ]; then
    print_warning "strategies/__init__.py not found, creating..."
    mkdir -p src/strategies
    cat > src/strategies/__init__.py << 'EOF'
"""
Trading strategies module.
"""
from .base import BaseStrategy
from .simple import SimpleBuySellStrategy
from .grid import GridTradingStrategy
from .indicator import IndicatorBasedStrategy

__all__ = [
    'BaseStrategy',
    'SimpleBuySellStrategy',
    'GridTradingStrategy', 
    'IndicatorBasedStrategy'
]
EOF
    print_success "Created strategies/__init__.py"
fi

# 4. Create missing signal types if needed
print_status "Checking signal_types.py..."
if [ ! -f "src/strategies/base/signal_types.py" ]; then
    cat > src/strategies/base/signal_types.py << 'EOF'
"""
Signal types and definitions for trading strategies.
"""
from enum import Enum
from dataclasses import dataclass
from typing import Optional

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
EOF
    print_success "Created signal_types.py"
fi

# 5. Create strategy mixin if needed
print_status "Checking strategy_mixin.py..."
if [ ! -f "src/strategies/base/strategy_mixin.py" ]; then
    cat > src/strategies/base/strategy_mixin.py << 'EOF'
"""
Strategy mixin classes for common functionality.
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class StrategyMixin:
    """Mixin class providing common strategy functionality."""
    
    def log_signal(self, signal_type: str, confidence: float, reason: str) -> None:
        """Log trading signal."""
        logger.info(f"{self.name}: {signal_type} signal (confidence: {confidence:.2f}) - {reason}")
        
    def validate_config(self, required_keys: list) -> bool:
        """Validate strategy configuration."""
        missing_keys = [key for key in required_keys if key not in self.config]
        if missing_keys:
            logger.error(f"Missing configuration keys: {missing_keys}")
            return False
        return True
EOF
    print_success "Created strategy_mixin.py"
fi

# 6. Check core engine imports
print_status "Checking core engine imports..."
if [ -f "src/core/trading_engine.py" ]; then
    # Fix potential circular imports
    print_status "Checking for circular import issues..."
    
    # Check if trading_engine.py has proper imports
    if grep -q "from strategies import" src/core/trading_engine.py; then
        print_warning "Found direct strategies import in trading_engine.py"
        print_status "Consider using dynamic imports to avoid circular dependencies"
    fi
fi

# 7. Test imports
print_status "Testing Python imports..."
cd src

# Test base strategy import
echo "Testing BaseStrategy import..."
python3 -c "
try:
    from strategies.base import BaseStrategy
    print('✅ BaseStrategy import successful')
except ImportError as e:
    print(f'❌ BaseStrategy import failed: {e}')
    exit(1)
" || print_error "BaseStrategy import still failing"

# Test strategy module import
echo "Testing strategies module import..."
python3 -c "
try:
    import strategies
    print('✅ Strategies module import successful')
except ImportError as e:
    print(f'❌ Strategies module import failed: {e}')
" || print_warning "Strategies module import issue"

cd ..

# 8. Check for other potential issues
print_status "Checking for other potential import issues..."

# Check for missing __init__.py files
find src -type d -name "*.py" -prune -o -type d -print | while read dir; do
    if [ ! -f "$dir/__init__.py" ] && [ "$dir" != "src" ]; then
        print_warning "Missing __init__.py in: $dir"
        touch "$dir/__init__.py"
        print_success "Created __init__.py in: $dir"
    fi
done

# 9. Docker-specific fixes
print_status "Checking Docker configuration..."
if [ -f "Dockerfile" ]; then
    if ! grep -q "PYTHONPATH" Dockerfile; then
        print_warning "PYTHONPATH not set in Dockerfile"
        echo "Consider adding: ENV PYTHONPATH=/app/src"
    fi
fi

# 10. Restart recommendation
print_success "Import fix script completed!"
echo ""
echo "🚀 Next Steps:"
echo "1. Restart the Docker containers:"
echo "   docker-compose down && docker-compose up -d"
echo ""
echo "2. Test the bot startup:"
echo "   docker logs trading-bot -f"
echo ""
echo "3. Or test locally:"
echo "   cd src && python main.py start --mode paper"
echo ""
echo "If issues persist, check the container logs for specific import errors."
