# src/strategies/signals.py

from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import logging
from collections import defaultdict, deque

from .base import Signal, SignalAction, SignalType, MarketData

logger = logging.getLogger(__name__)

class SignalStrength(Enum):
    """Signal strength levels"""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"

class SignalStatus(Enum):
    """Signal processing status"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    EXECUTED = "executed"

@dataclass
class ProcessedSignal:
    """Enhanced signal with processing information"""
    original_signal: Signal
    strength: SignalStrength
    status: SignalStatus
    confirmation_count: int = 0
    required_confirmations: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    rejection_reasons: List[str] = field(default_factory=list)
    
    @property
    def is_confirmed(self) -> bool:
        return self.confirmation_count >= self.required_confirmations
    
    @property
    def is_expired(self) -> bool:
        return self.expires_at and datetime.now() > self.expires_at
    
    @property
    def age_seconds(self) -> float:
        return (datetime.now() - self.created_at).total_seconds()

class SignalFilter:
    """Base class for signal filters"""
    
    def __init__(self, name: str):
        self.name = name
        self.enabled = True
    
    async def filter(self, signal: Signal, context: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Filter signal based on criteria
        
        Args:
            signal: Signal to filter
            context: Additional context information
            
        Returns:
            Tuple of (should_pass, rejection_reason)
        """
        return True, None

class VolumeFilter(SignalFilter):
    """Filter signals based on volume requirements"""
    
    def __init__(self, min_volume: float = 1000.0, volume_ratio: float = 1.5):
        super().__init__("volume_filter")
        self.min_volume = min_volume
        self.volume_ratio = volume_ratio
    
    async def filter(self, signal: Signal, context: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        current_volume = context.get('current_volume', 0)
        avg_volume = context.get('avg_volume', 0)
        
        if current_volume < self.min_volume:
            return False, f"Volume {current_volume} below minimum {self.min_volume}"
        
        if avg_volume > 0 and current_volume < avg_volume * self.volume_ratio:
            return False, f"Volume ratio {current_volume/avg_volume:.2f} below required {self.volume_ratio}"
        
        return True, None

class PriceFilter(SignalFilter):
    """Filter signals based on price criteria"""
    
    def __init__(self, min_price: float = 0.0001, max_price_change: float = 0.10):
        super().__init__("price_filter")
        self.min_price = min_price
        self.max_price_change = max_price_change
    
    async def filter(self, signal: Signal, context: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        if signal.price < self.min_price:
            return False, f"Price {signal.price} below minimum {self.min_price}"
        
        previous_price = context.get('previous_price')
        if previous_price:
            price_change = abs(signal.price - previous_price) / previous_price
            if price_change > self.max_price_change:
                return False, f"Price change {price_change:.2%} exceeds maximum {self.max_price_change:.2%}"
        
        return True, None

class TimeFilter(SignalFilter):
    """Filter signals based on time criteria"""
    
    def __init__(self, min_interval_seconds: int = 60, trading_hours: Optional[tuple] = None):
        super().__init__("time_filter")
        self.min_interval_seconds = min_interval_seconds
        self.trading_hours = trading_hours  # (start_hour, end_hour) in UTC
        self.last_signal_times = {}
    
    async def filter(self, signal: Signal, context: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        now = datetime.now()
        
        # Check trading hours
        if self.trading_hours:
            current_hour = now.hour
            start_hour, end_hour = self.trading_hours
            if not (start_hour <= current_hour < end_hour):
                return False, f"Outside trading hours ({start_hour}-{end_hour})"
        
        # Check minimum interval
        symbol = signal.symbol
        last_time = self.last_signal_times.get(symbol)
        if last_time:
            time_diff = (now - last_time).total_seconds()
            if time_diff < self.min_interval_seconds:
                return False, f"Signal too soon, wait {self.min_interval_seconds - time_diff:.0f}s"
        
        self.last_signal_times[symbol] = now
        return True, None

class ConfidenceFilter(SignalFilter):
    """Filter signals based on confidence threshold"""
    
    def __init__(self, min_confidence: float = 0.5):
        super().__init__("confidence_filter")
        self.min_confidence = min_confidence
    
    async def filter(self, signal: Signal, context: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        if signal.confidence < self.min_confidence:
            return False, f"Confidence {signal.confidence:.2f} below minimum {self.min_confidence:.2f}"
        
        return True, None

class SignalAggregator:
    """Aggregates signals from multiple sources for confirmation"""
    
    def __init__(self, confirmation_window_seconds: int = 300):
        self.confirmation_window_seconds = confirmation_window_seconds
        self.pending_signals: Dict[str, List[Signal]] = defaultdict(list)
        self.confirmed_signals: List[Signal] = []
    
    def add_signal(self, signal: Signal) -> Optional[Signal]:
        """
        Add signal to aggregation
        
        Args:
            signal: Signal to add
            
        Returns:
            Confirmed signal if consensus reached
        """
        key = f"{signal.symbol}_{signal.action.value}"
        self.pending_signals[key].append(signal)
        
        # Clean expired signals
        cutoff_time = datetime.now() - timedelta(seconds=self.confirmation_window_seconds)
        self.pending_signals[key] = [
            s for s in self.pending_signals[key] 
            if s.timestamp > cutoff_time
        ]
        
        # Check for confirmation (multiple signals for same action)
        if len(self.pending_signals[key]) >= 2:
            # Create aggregated signal
            signals = self.pending_signals[key]
            avg_confidence = sum(s.confidence for s in signals) / len(signals)
            
            aggregated_signal = Signal(
                action=signal.action,
                signal_type=SignalType.CONFIRMATION,
                symbol=signal.symbol,
                price=signal.price,
                confidence=min(1.0, avg_confidence * 1.2),  # Boost confidence
                reason=f"Aggregated from {len(signals)} signals: " + "; ".join(s.reason for s in signals[-3:]),
                metadata={
                    'aggregated_from': len(signals),
                    'source_signals': [s.reason for s in signals],
                    'confidence_boost': True
                }
            )
            
            # Clear pending signals for this key
            self.pending_signals[key].clear()
            
            return aggregated_signal
        
        return None

class SignalProcessor:
    """
    Main signal processing engine that handles filtering, aggregation, and routing
    """
    
    def __init__(self):
        self.filters: List[SignalFilter] = []
        self.aggregator = SignalAggregator()
        self.processed_signals: deque = deque(maxlen=1000)
        self.signal_callbacks: List[Callable] = []
        self.signal_history: Dict[str, List[ProcessedSignal]] = defaultdict(list)
        
        # Performance tracking
        self.stats = {
            'total_signals': 0,
            'filtered_signals': 0,
            'confirmed_signals': 0,
            'executed_signals': 0
        }
        
        # Default filters
        self._setup_default_filters()
        
        logger.info("Signal processor initialized")
    
    def _setup_default_filters(self):
        """Setup default signal filters"""
        self.add_filter(VolumeFilter(min_volume=100.0))
        self.add_filter(PriceFilter(min_price=0.0001))
        self.add_filter(TimeFilter(min_interval_seconds=30))
        self.add_filter(ConfidenceFilter(min_confidence=0.3))
    
    def add_filter(self, signal_filter: SignalFilter):
        """Add signal filter"""
        self.filters.append(signal_filter)
        logger.info(f"Added signal filter: {signal_filter.name}")
    
    def remove_filter(self, filter_name: str) -> bool:
        """Remove signal filter by name"""
        for i, f in enumerate(self.filters):
            if f.name == filter_name:
                del self.filters[i]
                logger.info(f"Removed signal filter: {filter_name}")
                return True
        return False
    
    def add_callback(self, callback: Callable[[ProcessedSignal], None]):
        """Add callback for processed signals"""
        self.signal_callbacks.append(callback)
    
    async def process_signal(self, signal: Signal, context: Optional[Dict[str, Any]] = None) -> Optional[ProcessedSignal]:
        """
        Process a signal through the complete pipeline
        
        Args:
            signal: Raw signal to process
            context: Additional context for filtering
            
        Returns:
            Processed signal if it passes all filters
        """
        self.stats['total_signals'] += 1
        
        if context is None:
            context = {}
        
        # Apply filters
        for signal_filter in self.filters:
            if not signal_filter.enabled:
                continue
            
            try:
                should_pass, rejection_reason = await signal_filter.filter(signal, context)
                if not should_pass:
                    logger.debug(f"Signal filtered by {signal_filter.name}: {rejection_reason}")
                    self.stats['filtered_signals'] += 1
                    return None
            except Exception as e:
                logger.error(f"Filter {signal_filter.name} error: {e}")
                continue
        
        # Determine signal strength
        strength = self._calculate_signal_strength(signal, context)
        
        # Create processed signal
        processed = ProcessedSignal(
            original_signal=signal,
            strength=strength,
            status=SignalStatus.PENDING,
            required_confirmations=self._get_required_confirmations(signal, strength),
            expires_at=datetime.now() + timedelta(minutes=15)  # 15 minute expiry
        )
        
        # Try aggregation for confirmation
        aggregated_signal = self.aggregator.add_signal(signal)
        if aggregated_signal:
            processed.confirmation_count = processed.required_confirmations
            processed.status = SignalStatus.CONFIRMED
            processed.confirmed_at = datetime.now()
            self.stats['confirmed_signals'] += 1
        
        # Store processed signal
        self.processed_signals.append(processed)
        self.signal_history[signal.symbol].append(processed)
        
        # Notify callbacks
        for callback in self.signal_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(processed)
                else:
                    callback(processed)
            except Exception as e:
                logger.error(f"Signal callback error: {e}")
        
        logger.info(f"Signal processed: {signal.symbol} {signal.action.value} "
                   f"(strength: {strength.value}, status: {processed.status.value})")
        
        return processed
    
    def _calculate_signal_strength(self, signal: Signal, context: Dict[str, Any]) -> SignalStrength:
        """Calculate signal strength based on various factors"""
        score = signal.confidence
        
        # Boost score based on volume
        current_volume = context.get('current_volume', 0)
        avg_volume = context.get('avg_volume', 1)
        if avg_volume > 0:
            volume_ratio = current_volume / avg_volume
            if volume_ratio > 3.0:
                score += 0.2
            elif volume_ratio > 2.0:
                score += 0.1
        
        # Boost score for certain signal types
        if signal.signal_type in [SignalType.CONFIRMATION, SignalType.TAKE_PROFIT]:
            score += 0.1
        
        # Penalize for frequent signals
        recent_signals = len([
            s for s in self.signal_history[signal.symbol][-10:]
            if (datetime.now() - s.created_at).total_seconds() < 3600
        ])
        if recent_signals > 5:
            score -= 0.1
        
        # Determine strength category
        if score >= 0.8:
            return SignalStrength.VERY_STRONG
        elif score >= 0.6:
            return SignalStrength.STRONG
        elif score >= 0.4:
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK
    
    def _get_required_confirmations(self, signal: Signal, strength: SignalStrength) -> int:
        """Get required confirmations based on signal properties"""
        base_confirmations = {
            SignalStrength.VERY_STRONG: 1,
            SignalStrength.STRONG: 1,
            SignalStrength.MODERATE: 2,
            SignalStrength.WEAK: 3
        }
        
        confirmations = base_confirmations.get(strength, 2)
        
        # Reduce confirmations for exit signals
        if signal.signal_type in [SignalType.EXIT, SignalType.STOP_LOSS, SignalType.TAKE_PROFIT]:
            confirmations = max(1, confirmations - 1)
        
        return confirmations
    
    def get_pending_signals(self, symbol: Optional[str] = None) -> List[ProcessedSignal]:
        """Get pending signals"""
        pending = [s for s in self.processed_signals if s.status == SignalStatus.PENDING and not s.is_expired]
        
        if symbol:
            pending = [s for s in pending if s.original_signal.symbol == symbol]
        
        return pending
    
    def get_confirmed_signals(self, symbol: Optional[str] = None, 
                            max_age_minutes: int = 60) -> List[ProcessedSignal]:
        """Get confirmed signals"""
        cutoff_time = datetime.now() - timedelta(minutes=max_age_minutes)
        confirmed = [
            s for s in self.processed_signals 
            if s.status == SignalStatus.CONFIRMED and s.created_at > cutoff_time
        ]
        
        if symbol:
            confirmed = [s for s in confirmed if s.original_signal.symbol == symbol]
        
        return confirmed
    
    def mark_signal_executed(self, processed_signal: ProcessedSignal):
        """Mark signal as executed"""
        processed_signal.status = SignalStatus.EXECUTED
        processed_signal.executed_at = datetime.now()
        self.stats['executed_signals'] += 1
        
        logger.info(f"Signal marked as executed: {processed_signal.original_signal.symbol}")
    
    def cleanup_expired_signals(self):
        """Clean up expired signals"""
        now = datetime.now()
        expired_count = 0
        
        for signal in self.processed_signals:
            if signal.status == SignalStatus.PENDING and signal.is_expired:
                signal.status = SignalStatus.EXPIRED
                expired_count += 1
        
        if expired_count > 0:
            logger.info(f"Expired {expired_count} signals")
    
    def get_signal_statistics(self) -> Dict[str, Any]:
        """Get signal processing statistics"""
        # Calculate efficiency metrics
        efficiency = {
            'filter_rate': (self.stats['filtered_signals'] / max(self.stats['total_signals'], 1)) * 100,
            'confirmation_rate': (self.stats['confirmed_signals'] / max(self.stats['total_signals'] - self.stats['filtered_signals'], 1)) * 100,
            'execution_rate': (self.stats['executed_signals'] / max(self.stats['confirmed_signals'], 1)) * 100
        }
        
        # Recent signal distribution
        recent_signals = [s for s in self.processed_signals if (datetime.now() - s.created_at).total_seconds() < 3600]
        strength_distribution = defaultdict(int)
        for signal in recent_signals:
            strength_distribution[signal.strength.value] += 1
        
        return {
            'processing_stats': self.stats,
            'efficiency_metrics': efficiency,
            'active_filters': len([f for f in self.filters if f.enabled]),
            'pending_signals': len(self.get_pending_signals()),
            'recent_hour_signals': len(recent_signals),
            'strength_distribution': dict(strength_distribution),
            'symbols_active': len(set(s.original_signal.symbol for s in recent_signals))
        }
    
    def reset_statistics(self):
        """Reset processing statistics"""
        self.stats = {
            'total_signals': 0,
            'filtered_signals': 0,
            'confirmed_signals': 0,
            'executed_signals': 0
        }
        logger.info("Signal processing statistics reset")