"""
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
