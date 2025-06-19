"""
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
