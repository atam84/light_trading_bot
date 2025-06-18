# src/strategies/indicators.py

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from .base import (
    BaseStrategy, Signal, SignalAction, SignalType, 
    MarketData, StrategyConfig, StrategyType, IndicatorMixin
)

logger = logging.getLogger(__name__)

class RSIStrategy(BaseStrategy, IndicatorMixin):
    """
    RSI-based trading strategy
    
    Configuration parameters:
    - rsi_period: RSI calculation period (default: 14)
    - oversold_threshold: RSI oversold level (default: 30)
    - overbought_threshold: RSI overbought level (default: 70)
    - exit_rsi_middle: Exit when RSI returns to middle range (default: 50)
    """
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        
        # Default parameters
        self.rsi_period = config.parameters.get('rsi_period', 14)
        self.oversold_threshold = config.parameters.get('oversold_threshold', 30)
        self.overbought_threshold = config.parameters.get('overbought_threshold', 70)
        self.exit_rsi_middle = config.parameters.get('exit_rsi_middle', 50)
        
        logger.info(f"RSI strategy initialized: period={self.rsi_period}, "
                   f"oversold={self.oversold_threshold}, overbought={self.overbought_threshold}")
    
    async def analyze(self, market_data: MarketData) -> Optional[Signal]:
        """
        Analyze market data using RSI indicator
        
        Args:
            market_data: Current market data with indicators
            
        Returns:
            Trading signal or None
        """
        symbol = market_data.symbol
        current_price = market_data.close
        
        # Get RSI from indicators
        rsi = market_data.indicators.get('rsi', market_data.indicators.get(f'rsi_{self.rsi_period}'))
        if rsi is None:
            logger.warning(f"RSI indicator not available for {symbol}")
            return None
        
        # Check for buy signal (oversold)
        if (rsi <= self.oversold_threshold and 
            self.should_enter_position(symbol, current_price)):
            
            confidence = min(1.0, (self.oversold_threshold - rsi) / self.oversold_threshold)
            
            return Signal(
                action=SignalAction.BUY,
                signal_type=SignalType.ENTRY,
                symbol=symbol,
                price=current_price,
                confidence=confidence,
                reason=f"RSI oversold signal: RSI={rsi:.2f} <= {self.oversold_threshold}",
                metadata={
                    'rsi': rsi,
                    'threshold': self.oversold_threshold,
                    'indicator': 'rsi_oversold'
                }
            )
        
        # Check for sell signal (overbought)
        if rsi >= self.overbought_threshold:
            # If we have a long position, sell it
            position = self.positions.get(symbol)
            if position and position.get('status') == 'open' and position.get('side') == 'buy':
                
                confidence = min(1.0, (rsi - self.overbought_threshold) / (100 - self.overbought_threshold))
                
                return Signal(
                    action=SignalAction.SELL,
                    signal_type=SignalType.EXIT,
                    symbol=symbol,
                    price=current_price,
                    confidence=confidence,
                    reason=f"RSI overbought signal: RSI={rsi:.2f} >= {self.overbought_threshold}",
                    metadata={
                        'rsi': rsi,
                        'threshold': self.overbought_threshold,
                        'indicator': 'rsi_overbought'
                    }
                )
        
        # Check for middle exit
        position = self.positions.get(symbol)
        if (position and position.get('status') == 'open' and 
            abs(rsi - self.exit_rsi_middle) <= 5):  # Within 5 points of middle
            
            entry_price = position['entry_price']
            profit_pct = ((current_price - entry_price) / entry_price) * 100
            
            if profit_pct > 1:  # Only exit if profitable
                return Signal(
                    action=SignalAction.SELL,
                    signal_type=SignalType.EXIT,
                    symbol=symbol,
                    price=current_price,
                    confidence=0.7,
                    reason=f"RSI middle exit: RSI={rsi:.2f} near {self.exit_rsi_middle}, "
                           f"profit={profit_pct:.2f}%",
                    metadata={
                        'rsi': rsi,
                        'profit_pct': profit_pct,
                        'indicator': 'rsi_middle'
                    }
                )
        
        # Check standard exit conditions
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
        """Required indicators for RSI strategy"""
        return [f'rsi_{self.rsi_period}', 'rsi']

class MovingAverageCrossStrategy(BaseStrategy, IndicatorMixin):
    """
    Moving Average crossover strategy
    
    Configuration parameters:
    - fast_period: Fast MA period (default: 12)
    - slow_period: Slow MA period (default: 26)
    - ma_type: Moving average type - 'sma' or 'ema' (default: 'ema')
    - confirm_periods: Periods to confirm crossover (default: 2)
    """
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.cross_history = {}  # symbol -> crossover history
        
        # Default parameters
        self.fast_period = config.parameters.get('fast_period', 12)
        self.slow_period = config.parameters.get('slow_period', 26)
        self.ma_type = config.parameters.get('ma_type', 'ema').lower()
        self.confirm_periods = config.parameters.get('confirm_periods', 2)
        
        logger.info(f"MA Cross strategy initialized: {self.ma_type.upper()}"
                   f"({self.fast_period},{self.slow_period}), confirm={self.confirm_periods}")
    
    async def analyze(self, market_data: MarketData) -> Optional[Signal]:
        """
        Analyze market data using moving average crossover
        
        Args:
            market_data: Current market data with indicators
            
        Returns:
            Trading signal or None
        """
        symbol = market_data.symbol
        current_price = market_data.close
        
        # Get moving averages from indicators
        fast_ma_key = f'{self.ma_type}{self.fast_period}'
        slow_ma_key = f'{self.ma_type}{self.slow_period}'
        
        fast_ma = market_data.indicators.get(fast_ma_key)
        slow_ma = market_data.indicators.get(slow_ma_key)
        
        if fast_ma is None or slow_ma is None:
            logger.warning(f"MA indicators not available for {symbol}: {fast_ma_key}, {slow_ma_key}")
            return None
        
        # Initialize cross history if needed
        if symbol not in self.cross_history:
            self.cross_history[symbol] = []
        
        # Determine current crossover state
        current_cross = 'golden' if fast_ma > slow_ma else 'death'
        
        # Update history
        self.cross_history[symbol].append({
            'timestamp': market_data.timestamp,
            'cross_type': current_cross,
            'fast_ma': fast_ma,
            'slow_ma': slow_ma,
            'price': current_price
        })
        
        # Keep only recent history
        if len(self.cross_history[symbol]) > 100:
            self.cross_history[symbol] = self.cross_history[symbol][-100:]
        
        # Check for crossover signals
        if len(self.cross_history[symbol]) >= self.confirm_periods + 1:
            recent_crosses = self.cross_history[symbol][-self.confirm_periods-1:]
            
            # Check for golden cross (fast above slow)
            if (recent_crosses[-1]['cross_type'] == 'golden' and
                recent_crosses[-2]['cross_type'] == 'death' and
                self.should_enter_position(symbol, current_price)):
                
                # Confirm the crossover for specified periods
                if all(c['cross_type'] == 'golden' for c in recent_crosses[-self.confirm_periods:]):
                    
                    confidence = min(1.0, (fast_ma - slow_ma) / slow_ma * 100)
                    
                    return Signal(
                        action=SignalAction.BUY,
                        signal_type=SignalType.ENTRY,
                        symbol=symbol,
                        price=current_price,
                        confidence=confidence,
                        reason=f"Golden cross: {self.ma_type.upper()}{self.fast_period}({fast_ma:.2f}) > "
                               f"{self.ma_type.upper()}{self.slow_period}({slow_ma:.2f})",
                        metadata={
                            'fast_ma': fast_ma,
                            'slow_ma': slow_ma,
                            'cross_type': 'golden',
                            'ma_type': self.ma_type
                        }
                    )
            
            # Check for death cross (fast below slow)
            if (recent_crosses[-1]['cross_type'] == 'death' and
                recent_crosses[-2]['cross_type'] == 'golden'):
                
                # If we have a position, close it
                position = self.positions.get(symbol)
                if position and position.get('status') == 'open' and position.get('side') == 'buy':
                    
                    # Confirm the crossover
                    if all(c['cross_type'] == 'death' for c in recent_crosses[-self.confirm_periods:]):
                        
                        return Signal(
                            action=SignalAction.SELL,
                            signal_type=SignalType.EXIT,
                            symbol=symbol,
                            price=current_price,
                            confidence=1.0,
                            reason=f"Death cross: {self.ma_type.upper()}{self.fast_period}({fast_ma:.2f}) < "
                                   f"{self.ma_type.upper()}{self.slow_period}({slow_ma:.2f})",
                            metadata={
                                'fast_ma': fast_ma,
                                'slow_ma': slow_ma,
                                'cross_type': 'death',
                                'ma_type': self.ma_type
                            }
                        )
        
        # Check standard exit conditions
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
        """Required indicators for MA cross strategy"""
        return [
            f'{self.ma_type}{self.fast_period}',
            f'{self.ma_type}{self.slow_period}'
        ]

class MACDStrategy(BaseStrategy, IndicatorMixin):
    """
    MACD-based trading strategy
    
    Configuration parameters:
    - fast_period: MACD fast EMA period (default: 12)
    - slow_period: MACD slow EMA period (default: 26)
    - signal_period: MACD signal line period (default: 9)
    - histogram_threshold: Minimum histogram value for signal (default: 0.1)
    """
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        
        # Default parameters
        self.fast_period = config.parameters.get('fast_period', 12)
        self.slow_period = config.parameters.get('slow_period', 26)
        self.signal_period = config.parameters.get('signal_period', 9)
        self.histogram_threshold = config.parameters.get('histogram_threshold', 0.1)
        
        logger.info(f"MACD strategy initialized: "
                   f"({self.fast_period},{self.slow_period},{self.signal_period}), "
                   f"histogram_threshold={self.histogram_threshold}")
    
    async def analyze(self, market_data: MarketData) -> Optional[Signal]:
        """
        Analyze market data using MACD indicator
        
        Args:
            market_data: Current market data with indicators
            
        Returns:
            Trading signal or None
        """
        symbol = market_data.symbol
        current_price = market_data.close
        
        # Get MACD components from indicators
        macd = market_data.indicators.get('macd')
        macd_signal = market_data.indicators.get('macdSignal', market_data.indicators.get('macd_signal'))
        macd_histogram = market_data.indicators.get('macdHist', market_data.indicators.get('macd_histogram'))
        
        if macd is None or macd_signal is None or macd_histogram is None:
            logger.warning(f"MACD indicators not available for {symbol}")
            return None
        
        # Check for bullish signal (MACD line crosses above signal line)
        if (macd > macd_signal and 
            macd_histogram > self.histogram_threshold and
            self.should_enter_position(symbol, current_price)):
            
            confidence = min(1.0, abs(macd_histogram) / (abs(macd) + 0.001))
            
            return Signal(
                action=SignalAction.BUY,
                signal_type=SignalType.ENTRY,
                symbol=symbol,
                price=current_price,
                confidence=confidence,
                reason=f"MACD bullish crossover: MACD({macd:.3f}) > Signal({macd_signal:.3f}), "
                       f"Histogram={macd_histogram:.3f}",
                metadata={
                    'macd': macd,
                    'macd_signal': macd_signal,
                    'macd_histogram': macd_histogram,
                    'signal_type': 'bullish_crossover'
                }
            )
        
        # Check for bearish signal (MACD line crosses below signal line)
        if macd < macd_signal and macd_histogram < -self.histogram_threshold:
            position = self.positions.get(symbol)
            if position and position.get('status') == 'open' and position.get('side') == 'buy':
                
                return Signal(
                    action=SignalAction.SELL,
                    signal_type=SignalType.EXIT,
                    symbol=symbol,
                    price=current_price,
                    confidence=1.0,
                    reason=f"MACD bearish crossover: MACD({macd:.3f}) < Signal({macd_signal:.3f}), "
                           f"Histogram={macd_histogram:.3f}",
                    metadata={
                        'macd': macd,
                        'macd_signal': macd_signal,
                        'macd_histogram': macd_histogram,
                        'signal_type': 'bearish_crossover'
                    }
                )
        
        # Check standard exit conditions
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
        """Required indicators for MACD strategy"""
        return ['macd', 'macdSignal', 'macdHist']

class ComboIndicatorStrategy(BaseStrategy, IndicatorMixin):
    """
    Multi-indicator strategy combining RSI, MA, and MACD for confirmation
    
    Configuration parameters:
    - entry_indicators: List of indicators required for entry (default: ['rsi', 'ma_cross'])
    - confirmation_indicators: List of indicators for confirmation (default: ['macd'])
    - rsi_oversold: RSI oversold threshold (default: 35)
    - rsi_overbought: RSI overbought threshold (default: 65)
    - require_all_signals: Require all indicators to agree (default: True)
    """
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        
        # Default parameters
        self.entry_indicators = config.parameters.get('entry_indicators', ['rsi', 'ma_cross'])
        self.confirmation_indicators = config.parameters.get('confirmation_indicators', ['macd'])
        self.rsi_oversold = config.parameters.get('rsi_oversold', 35)
        self.rsi_overbought = config.parameters.get('rsi_overbought', 65)
        self.require_all_signals = config.parameters.get('require_all_signals', True)
        
        logger.info(f"Combo indicator strategy initialized: "
                   f"entry={self.entry_indicators}, confirmation={self.confirmation_indicators}")
    
    async def analyze(self, market_data: MarketData) -> Optional[Signal]:
        """
        Analyze market data using multiple indicators
        
        Args:
            market_data: Current market data with indicators
            
        Returns:
            Trading signal or None
        """
        symbol = market_data.symbol
        current_price = market_data.close
        indicators = market_data.indicators
        
        # Collect signals from different indicators
        entry_signals = []
        confirmation_signals = []
        exit_signals = []
        
        # RSI signals
        if 'rsi' in self.entry_indicators:
            rsi = indicators.get('rsi', indicators.get('rsi_14'))
            if rsi is not None:
                if rsi <= self.rsi_oversold:
                    entry_signals.append({
                        'indicator': 'rsi',
                        'action': 'buy',
                        'confidence': (self.rsi_oversold - rsi) / self.rsi_oversold,
                        'value': rsi
                    })
                elif rsi >= self.rsi_overbought:
                    exit_signals.append({
                        'indicator': 'rsi',
                        'action': 'sell',
                        'confidence': (rsi - self.rsi_overbought) / (100 - self.rsi_overbought),
                        'value': rsi
                    })
        
        # Moving Average Cross signals
        if 'ma_cross' in self.entry_indicators:
            ema12 = indicators.get('ema12')
            ema26 = indicators.get('ema26')
            if ema12 is not None and ema26 is not None:
                if ema12 > ema26:
                    entry_signals.append({
                        'indicator': 'ma_cross',
                        'action': 'buy',
                        'confidence': min(1.0, (ema12 - ema26) / ema26 * 100),
                        'value': f"EMA12({ema12:.2f}) > EMA26({ema26:.2f})"
                    })
                else:
                    exit_signals.append({
                        'indicator': 'ma_cross',
                        'action': 'sell',
                        'confidence': 1.0,
                        'value': f"EMA12({ema12:.2f}) < EMA26({ema26:.2f})"
                    })
        
        # MACD confirmation signals
        if 'macd' in self.confirmation_indicators:
            macd = indicators.get('macd')
            macd_signal = indicators.get('macdSignal')
            macd_hist = indicators.get('macdHist')
            
            if all(x is not None for x in [macd, macd_signal, macd_hist]):
                if macd > macd_signal and macd_hist > 0:
                    confirmation_signals.append({
                        'indicator': 'macd',
                        'action': 'buy',
                        'confidence': min(1.0, abs(macd_hist) / (abs(macd) + 0.001)),
                        'value': f"MACD({macd:.3f}) > Signal({macd_signal:.3f})"
                    })
                elif macd < macd_signal and macd_hist < 0:
                    exit_signals.append({
                        'indicator': 'macd',
                        'action': 'sell',
                        'confidence': 1.0,
                        'value': f"MACD({macd:.3f}) < Signal({macd_signal:.3f})"
                    })
        
        # Evaluate entry signals
        if (entry_signals and 
            (not self.require_all_signals or len(entry_signals) >= len(self.entry_indicators)) and
            self.should_enter_position(symbol, current_price)):
            
            # Check confirmation if required
            if self.confirmation_indicators and not confirmation_signals:
                return None  # Wait for confirmation
            
            # Calculate combined confidence
            total_confidence = sum(s['confidence'] for s in entry_signals + confirmation_signals)
            avg_confidence = total_confidence / (len(entry_signals) + len(confirmation_signals))
            
            signal_reasons = [f"{s['indicator']}({s['value']})" for s in entry_signals + confirmation_signals]
            
            return Signal(
                action=SignalAction.BUY,
                signal_type=SignalType.ENTRY,
                symbol=symbol,
                price=current_price,
                confidence=avg_confidence,
                reason=f"Multi-indicator buy: {', '.join(signal_reasons)}",
                metadata={
                    'entry_signals': entry_signals,
                    'confirmation_signals': confirmation_signals,
                    'combined_confidence': avg_confidence
                }
            )
        
        # Evaluate exit signals
        if exit_signals:
            position = self.positions.get(symbol)
            if position and position.get('status') == 'open':
                
                signal_reasons = [f"{s['indicator']}({s['value']})" for s in exit_signals]
                
                return Signal(
                    action=SignalAction.SELL,
                    signal_type=SignalType.EXIT,
                    symbol=symbol,
                    price=current_price,
                    confidence=1.0,
                    reason=f"Multi-indicator sell: {', '.join(signal_reasons)}",
                    metadata={
                        'exit_signals': exit_signals
                    }
                )
        
        # Check standard exit conditions
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
        """Required indicators for combo strategy"""
        required = []
        
        if 'rsi' in self.entry_indicators:
            required.extend(['rsi', 'rsi_14'])
        
        if 'ma_cross' in self.entry_indicators:
            required.extend(['ema12', 'ema26'])
        
        if 'macd' in self.confirmation_indicators:
            required.extend(['macd', 'macdSignal', 'macdHist'])
        
        return required