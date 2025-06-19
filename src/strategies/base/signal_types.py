"""
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
