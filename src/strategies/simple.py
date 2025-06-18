# src/strategies/simple.py

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

from .base import (
    BaseStrategy, Signal, SignalAction, SignalType, 
    MarketData, StrategyConfig, StrategyType
)

logger = logging.getLogger(__name__)

class BuyLowSellHighStrategy(BaseStrategy):
    """
    Simple buy low, sell high strategy based on price thresholds
    
    Configuration parameters:
    - buy_threshold_pct: Percentage below recent high to trigger buy (default: 5%)
    - sell_threshold_pct: Percentage above buy price to trigger sell (default: 10%)
    - lookback_hours: Hours to look back for high/low calculation (default: 24)
    - min_volume: Minimum volume required for signal (default: 1000)
    """
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.price_history = {}  # symbol -> list of prices
        
        # Default parameters
        self.buy_threshold_pct = config.parameters.get('buy_threshold_pct', 5.0)
        self.sell_threshold_pct = config.parameters.get('sell_threshold_pct', 10.0)
        self.lookback_hours = config.parameters.get('lookback_hours', 24)
        self.min_volume = config.parameters.get('min_volume', 1000.0)
        
        logger.info(f"BuyLowSellHigh strategy initialized: "
                   f"buy_threshold={self.buy_threshold_pct}%, "
                   f"sell_threshold={self.sell_threshold_pct}%, "
                   f"lookback={self.lookback_hours}h")
    
    async def analyze(self, market_data: MarketData) -> Optional[Signal]:
        """
        Analyze market data for buy low/sell high signals
        
        Args:
            market_data: Current market data
            
        Returns:
            Trading signal or None
        """
        symbol = market_data.symbol
        current_price = market_data.close
        volume = market_data.volume
        
        # Check minimum volume requirement
        if volume < self.min_volume:
            return None
        
        # Update price history
        self._update_price_history(symbol, current_price, market_data.timestamp)
        
        # Get price history for analysis
        prices = self.price_history.get(symbol, [])
        if len(prices) < 10:  # Need some history
            return None
        
        # Calculate recent high and low
        recent_high = max([p['price'] for p in prices])
        recent_low = min([p['price'] for p in prices])
        
        # Check for buy signal (price dropped significantly from recent high)
        if self.should_enter_position(symbol, current_price):
            buy_threshold_price = recent_high * (1 - self.buy_threshold_pct / 100)
            
            if current_price <= buy_threshold_price:
                confidence = min(1.0, (recent_high - current_price) / (recent_high - recent_low))
                
                return Signal(
                    action=SignalAction.BUY,
                    signal_type=SignalType.ENTRY,
                    symbol=symbol,
                    price=current_price,
                    confidence=confidence,
                    reason=f"Price {current_price:.2f} below threshold {buy_threshold_price:.2f} "
                           f"({self.buy_threshold_pct}% from recent high {recent_high:.2f})",
                    metadata={
                        'recent_high': recent_high,
                        'recent_low': recent_low,
                        'threshold_price': buy_threshold_price,
                        'volume': volume
                    }
                )
        
        # Check for sell signal (price increased from our entry)
        position = self.positions.get(symbol)
        if position and position.get('status') == 'open' and position.get('side') == 'buy':
            entry_price = position['entry_price']
            sell_threshold_price = entry_price * (1 + self.sell_threshold_pct / 100)
            
            if current_price >= sell_threshold_price:
                profit_pct = ((current_price - entry_price) / entry_price) * 100
                
                return Signal(
                    action=SignalAction.SELL,
                    signal_type=SignalType.EXIT,
                    symbol=symbol,
                    price=current_price,
                    confidence=1.0,
                    reason=f"Price {current_price:.2f} above sell threshold {sell_threshold_price:.2f} "
                           f"(+{profit_pct:.2f}% profit from entry {entry_price:.2f})",
                    metadata={
                        'entry_price': entry_price,
                        'profit_pct': profit_pct,
                        'threshold_price': sell_threshold_price
                    }
                )
        
        # Check for stop loss/take profit
        if self.should_exit_position(symbol, current_price):
            return Signal(
                action=SignalAction.SELL,
                signal_type=SignalType.STOP_LOSS,
                symbol=symbol,
                price=current_price,
                confidence=1.0,
                reason="Stop loss or take profit triggered"
            )
        
        return None
    
    def get_required_indicators(self) -> List[str]:
        """No indicators required for simple strategy"""
        return []
    
    def _update_price_history(self, symbol: str, price: float, timestamp: datetime):
        """
        Update price history for symbol
        
        Args:
            symbol: Trading symbol
            price: Current price
            timestamp: Price timestamp
        """
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        
        self.price_history[symbol].append({
            'price': price,
            'timestamp': timestamp
        })
        
        # Keep only recent history (lookback period)
        cutoff_time = timestamp - timedelta(hours=self.lookback_hours)
        self.price_history[symbol] = [
            p for p in self.price_history[symbol] 
            if p['timestamp'] >= cutoff_time
        ]
        
        # Limit history size
        if len(self.price_history[symbol]) > 1000:
            self.price_history[symbol] = self.price_history[symbol][-1000:]

class DCAStrategy(BaseStrategy):
    """
    Dollar Cost Averaging strategy - buy fixed amount at regular intervals
    
    Configuration parameters:
    - buy_amount: Fixed USD amount to buy each interval (default: 50)
    - buy_interval_minutes: Minutes between buys (default: 60)
    - sell_trigger_pct: Percentage gain to trigger sell (default: 20%)
    - max_positions: Maximum number of DCA positions (default: 5)
    """
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.last_buy_times = {}  # symbol -> last buy timestamp
        
        # Default parameters
        self.buy_amount = config.parameters.get('buy_amount', 50.0)
        self.buy_interval_minutes = config.parameters.get('buy_interval_minutes', 60)
        self.sell_trigger_pct = config.parameters.get('sell_trigger_pct', 20.0)
        self.max_positions = config.parameters.get('max_positions', 5)
        
        logger.info(f"DCA strategy initialized: "
                   f"amount=${self.buy_amount}, "
                   f"interval={self.buy_interval_minutes}min, "
                   f"sell_trigger={self.sell_trigger_pct}%")
    
    async def analyze(self, market_data: MarketData) -> Optional[Signal]:
        """
        Analyze for DCA buy signals and sell opportunities
        
        Args:
            market_data: Current market data
            
        Returns:
            Trading signal or None
        """
        symbol = market_data.symbol
        current_price = market_data.close
        current_time = market_data.timestamp
        
        # Check if it's time for next DCA buy
        last_buy = self.last_buy_times.get(symbol)
        if not last_buy or (current_time - last_buy).total_seconds() >= (self.buy_interval_minutes * 60):
            
            # Check if we can add more positions
            open_positions = len([p for p in self.positions.values() 
                                if p.get('symbol') == symbol and p.get('status') == 'open'])
            
            if open_positions < self.max_positions:
                # Calculate buy amount in crypto
                crypto_amount = self.buy_amount / current_price
                
                # Update last buy time
                self.last_buy_times[symbol] = current_time
                
                return Signal(
                    action=SignalAction.BUY,
                    signal_type=SignalType.ENTRY,
                    symbol=symbol,
                    price=current_price,
                    confidence=1.0,
                    reason=f"DCA buy: ${self.buy_amount} worth ({crypto_amount:.6f} {symbol.split('/')[0]})",
                    metadata={
                        'dca_amount_usd': self.buy_amount,
                        'crypto_amount': crypto_amount,
                        'position_count': open_positions + 1
                    }
                )
        
        # Check for sell opportunities on existing positions
        for pos_id, position in self.positions.items():
            if (position.get('symbol') == symbol and 
                position.get('status') == 'open' and 
                position.get('side') == 'buy'):
                
                entry_price = position['entry_price']
                profit_pct = ((current_price - entry_price) / entry_price) * 100
                
                if profit_pct >= self.sell_trigger_pct:
                    return Signal(
                        action=SignalAction.SELL,
                        signal_type=SignalType.TAKE_PROFIT,
                        symbol=symbol,
                        price=current_price,
                        confidence=1.0,
                        reason=f"DCA sell: +{profit_pct:.2f}% profit "
                               f"(entry: {entry_price:.2f}, current: {current_price:.2f})",
                        metadata={
                            'entry_price': entry_price,
                            'profit_pct': profit_pct,
                            'position_id': pos_id
                        }
                    )
        
        return None
    
    def get_required_indicators(self) -> List[str]:
        """No indicators required for DCA strategy"""
        return []

class VolatilityBreakoutStrategy(BaseStrategy):
    """
    Volatility breakout strategy - buy on high volume price movements
    
    Configuration parameters:
    - volume_multiplier: Volume must be X times average (default: 2.0)
    - price_change_pct: Minimum price change percentage (default: 3.0)
    - lookback_periods: Periods to calculate averages (default: 20)
    """
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.volume_history = {}  # symbol -> volume history
        self.price_change_history = {}  # symbol -> price change history
        
        # Default parameters
        self.volume_multiplier = config.parameters.get('volume_multiplier', 2.0)
        self.price_change_pct = config.parameters.get('price_change_pct', 3.0)
        self.lookback_periods = config.parameters.get('lookback_periods', 20)
        
        logger.info(f"Volatility breakout strategy initialized: "
                   f"volume_multiplier={self.volume_multiplier}x, "
                   f"price_change={self.price_change_pct}%, "
                   f"lookback={self.lookback_periods}")
    
    async def analyze(self, market_data: MarketData) -> Optional[Signal]:
        """
        Analyze for volatility breakout signals
        
        Args:
            market_data: Current market data
            
        Returns:
            Trading signal or None
        """
        symbol = market_data.symbol
        current_price = market_data.close
        current_volume = market_data.volume
        
        # Update history
        self._update_volume_history(symbol, current_volume)
        
        # Calculate price change from open
        price_change_pct = ((current_price - market_data.open) / market_data.open) * 100
        
        # Get volume and price change history
        volume_history = self.volume_history.get(symbol, [])
        if len(volume_history) < self.lookback_periods:
            return None
        
        # Calculate average volume
        avg_volume = sum(volume_history) / len(volume_history)
        
        # Check for breakout conditions
        volume_breakout = current_volume >= (avg_volume * self.volume_multiplier)
        price_breakout = abs(price_change_pct) >= self.price_change_pct
        
        if volume_breakout and price_breakout and self.should_enter_position(symbol, current_price):
            action = SignalAction.BUY if price_change_pct > 0 else SignalAction.SELL
            confidence = min(1.0, (current_volume / avg_volume) / self.volume_multiplier)
            
            return Signal(
                action=action,
                signal_type=SignalType.ENTRY,
                symbol=symbol,
                price=current_price,
                confidence=confidence,
                reason=f"Volatility breakout: {price_change_pct:+.2f}% price change, "
                       f"{current_volume:.0f} volume ({current_volume/avg_volume:.1f}x avg)",
                metadata={
                    'price_change_pct': price_change_pct,
                    'current_volume': current_volume,
                    'avg_volume': avg_volume,
                    'volume_ratio': current_volume / avg_volume
                }
            )
        
        # Check exit conditions
        if self.should_exit_position(symbol, current_price):
            return Signal(
                action=SignalAction.SELL,
                signal_type=SignalType.EXIT,
                symbol=symbol,
                price=current_price,
                confidence=1.0,
                reason="Exit volatility position"
            )
        
        return None
    
    def get_required_indicators(self) -> List[str]:
        """No indicators required"""
        return []
    
    def _update_volume_history(self, symbol: str, volume: float):
        """
        Update volume history for symbol
        
        Args:
            symbol: Trading symbol
            volume: Current volume
        """
        if symbol not in self.volume_history:
            self.volume_history[symbol] = []
        
        self.volume_history[symbol].append(volume)
        
        # Keep only recent history
        if len(self.volume_history[symbol]) > self.lookback_periods * 2:
            self.volume_history[symbol] = self.volume_history[symbol][-self.lookback_periods:]