# scripts/quick_fix.sh - One-liner fix for critical import issue

#!/bin/bash
# Quick fix for BaseStrategy import issue
# Usage: ./scripts/quick_fix.sh (run from project root)

echo "🚀 Quick Fix: Creating missing BaseStrategy files..."

# Ensure we're in the project root
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

# Create the missing BaseStrategy class
mkdir -p src/strategies/base
cat > src/strategies/base/base_strategy.py << 'EOF'
"""Base strategy class for trading bot."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

class BaseStrategy(ABC):
    """Abstract base class for all trading strategies."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = config.get('name', self.__class__.__name__)
        self.is_active = False
        
    @abstractmethod
    async def should_buy(self, data: Dict[str, Any]) -> Tuple[bool, float]:
        """Determine if should buy. Returns (should_buy, confidence)."""
        pass
        
    @abstractmethod
    async def should_sell(self, data: Dict[str, Any]) -> Tuple[bool, float]:
        """Determine if should sell. Returns (should_sell, confidence)."""
        pass
        
    async def initialize(self) -> None:
        """Initialize strategy."""
        self.is_active = True
        logger.info(f"Strategy {self.name} initialized")
        
    async def cleanup(self) -> None:
        """Cleanup strategy."""
        self.is_active = False
EOF

# Create the missing __init__.py that exports BaseStrategy
cat > src/strategies/base/__init__.py << 'EOF'
"""Base strategy framework exports."""
from .base_strategy import BaseStrategy

__all__ = ['BaseStrategy']
EOF

# Create main strategies __init__.py  
cat > src/strategies/__init__.py << 'EOF'
"""Trading strategies module."""
from .base import BaseStrategy

__all__ = ['BaseStrategy']
EOF

# Ensure all directories have __init__.py
touch src/strategies/simple/__init__.py
touch src/strategies/grid/__init__.py
touch src/strategies/indicator/__init__.py
touch src/core/__init__.py
touch src/interfaces/__init__.py

echo "✅ Quick fix applied! Restart the bot:"
echo "docker-compose down && docker-compose up -d"
