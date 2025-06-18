# src/strategies/grid.py

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging
import uuid

from .base import (
    BaseStrategy, Signal, SignalAction, SignalType, 
    MarketData, StrategyConfig, StrategyType
)

logger = logging.getLogger(__name__)

class GridTradingStrategy(BaseStrategy):
    """
    Grid trading strategy - places buy and sell orders at regular intervals
    
    Configuration parameters:
    - grid_levels: Number of grid levels (default: 10)
    - grid_spacing_pct: Percentage spacing between levels (default: 1.0%)
    - base_amount_usd: USD amount per grid level (default: 100)
    - center_price: Center price for grid (if None, uses current price)
    - upper_limit: Upper price limit (if None, calculated from center)
    - lower_limit: Lower price limit (if None, calculated from center)
    - rebalance_threshold_pct: Rebalance when price moves X% (default: 5%)
    - take_profit_pct: Take profit percentage per trade (default: 1.5%)
    """
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.grid_levels = {}  # symbol -> grid configuration
        self.grid_orders = {}  # symbol -> active grid orders
        
        # Default parameters
        self.num_grid_levels = config.parameters.get('grid_levels', 10)
        self.grid_spacing_pct = config.parameters.get('grid_spacing_pct', 1.0)
        self.base_amount_usd = config.parameters.get('base_amount_usd', 100.0)
        self.center_price = config.parameters.get('center_price', None)
        self.upper_limit = config.parameters.get('upper_limit', None)
        self.lower_limit = config.parameters.get('lower_limit', None)
        self.rebalance_threshold_pct = config.parameters.get('rebalance_threshold_pct', 5.0)
        self.take_profit_pct = config.parameters.get('take_profit_pct', 1.5)
        
        logger.info(f"Grid trading strategy initialized: "
                   f"{self.num_grid_levels} levels, "
                   f"{self.grid_spacing_pct}% spacing, "
                   f"${self.base_amount_usd} per level")
    
    async def analyze(self, market_data: MarketData) -> Optional[Signal]:
        """
        Analyze market data for grid trading opportunities
        
        Args:
            market_data: Current market data
            
        Returns:
            Trading signal or None
        """
        symbol = market_data.symbol
        current_price = market_data.close
        
        # Initialize grid if not exists
        if symbol not in self.grid_levels:
            self._initialize_grid(symbol, current_price)
        
        grid = self.grid_levels[symbol]
        
        # Check if we need to rebalance grid
        price_change_pct = abs((current_price - grid['center_price']) / grid['center_price']) * 100
        if price_change_pct > self.rebalance_threshold_pct:
            logger.info(f"Rebalancing grid for {symbol}: price moved {price_change_pct:.2f}%")
            self._initialize_grid(symbol, current_price)
            grid = self.grid_levels[symbol]
        
        # Find closest grid levels
        lower_level, upper_level = self._find_surrounding_levels(symbol, current_price)
        
        if lower_level is None or upper_level is None:
            return None
        
        # Check for buy signal (price near lower level)
        buy_trigger_price = lower_level['price'] * (1 + self.grid_spacing_pct / 200)  # Half spacing
        if current_price <= buy_trigger_price and not lower_level.get('buy_executed', False):
            
            # Calculate buy amount
            crypto_amount = self.base_amount_usd / current_price
            
            # Mark level as executed
            lower_level['buy_executed'] = True
            lower_level['buy_price'] = current_price
            lower_level['buy_time'] = market_data.timestamp
            
            return Signal(
                action=SignalAction.BUY,
                signal_type=SignalType.ENTRY,
                symbol=symbol,
                price=current_price,
                confidence=1.0,
                reason=f"Grid buy at level {lower_level['level']} "
                       f"(target: {lower_level['price']:.2f}, actual: {current_price:.2f})",
                metadata={
                    'grid_level': lower_level['level'],
                    'target_price': lower_level['price'],
                    'amount_usd': self.base_amount_usd,
                    'crypto_amount': crypto_amount,
                    'grid_type': 'buy'
                }
            )
        
        # Check for sell signal (price near upper level)
        sell_trigger_price = upper_level['price'] * (1 - self.grid_spacing_pct / 200)  # Half spacing
        if current_price >= sell_trigger_price and not upper_level.get('sell_executed', False):
            
            # Check if we have position to sell
            available_position = self._get_available_position(symbol)
            if available_position:
                
                # Mark level as executed
                upper_level['sell_executed'] = True
                upper_level['sell_price'] = current_price
                upper_level['sell_time'] = market_data.timestamp
                
                return Signal(
                    action=SignalAction.SELL,
                    signal_type=SignalType.EXIT,
                    symbol=symbol,
                    price=current_price,
                    confidence=1.0,
                    reason=f"Grid sell at level {upper_level['level']} "
                           f"(target: {upper_level['price']:.2f}, actual: {current_price:.2f})",
                    metadata={
                        'grid_level': upper_level['level'],
                        'target_price': upper_level['price'],
                        'position_id': available_position['id'],
                        'buy_price': available_position['entry_price'],
                        'grid_type': 'sell'
                    }
                )
        
        # Check for take profit on individual positions
        profit_signal = self._check_take_profit(symbol, current_price)
        if profit_signal:
            return profit_signal
        
        return None
    
    def get_required_indicators(self) -> List[str]:
        """No indicators required for grid strategy"""
        return []
    
    def _initialize_grid(self, symbol: str, center_price: float):
        """
        Initialize grid levels around center price
        
        Args:
            symbol: Trading symbol
            center_price: Center price for grid
        """
        # Use provided center price or current price
        if self.center_price:
            center = self.center_price
        else:
            center = center_price
        
        # Calculate grid boundaries
        if self.upper_limit and self.lower_limit:
            upper = self.upper_limit
            lower = self.lower_limit
        else:
            # Calculate based on grid levels and spacing
            total_range_pct = (self.num_grid_levels // 2) * self.grid_spacing_pct
            upper = center * (1 + total_range_pct / 100)
            lower = center * (1 - total_range_pct / 100)
        
        # Create grid levels
        levels = []
        level_spacing = (upper - lower) / (self.num_grid_levels - 1)
        
        for i in range(self.num_grid_levels):
            price = lower + (i * level_spacing)
            levels.append({
                'level': i,
                'price': price,
                'buy_executed': False,
                'sell_executed': False,
                'buy_price': None,
                'sell_price': None,
                'buy_time': None,
                'sell_time': None
            })
        
        self.grid_levels[symbol] = {
            'center_price': center,
            'upper_limit': upper,
            'lower_limit': lower,
            'levels': levels,
            'created_at': datetime.now()
        }
        
        logger.info(f"Grid initialized for {symbol}: "
                   f"center={center:.2f}, range={lower:.2f}-{upper:.2f}, "
                   f"{self.num_grid_levels} levels")
    
    def _find_surrounding_levels(self, symbol: str, current_price: float) -> Tuple[Optional[dict], Optional[dict]]:
        """
        Find grid levels surrounding current price
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            
        Returns:
            Tuple of (lower_level, upper_level)
        """
        if symbol not in self.grid_levels:
            return None, None
        
        levels = self.grid_levels[symbol]['levels']
        
        lower_level = None
        upper_level = None
        
        for level in levels:
            if level['price'] <= current_price:
                lower_level = level
            elif level['price'] > current_price and upper_level is None:
                upper_level = level
                break
        
        return lower_level, upper_level
    
    def _get_available_position(self, symbol: str) -> Optional[dict]:
        """
        Get available position for selling
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Position dictionary or None
        """
        for pos_id, position in self.positions.items():
            if (position.get('symbol') == symbol and 
                position.get('status') == 'open' and 
                position.get('side') == 'buy'):
                return {
                    'id': pos_id,
                    'entry_price': position['entry_price'],
                    'amount': position['amount']
                }
        return None
    
    def _check_take_profit(self, symbol: str, current_price: float) -> Optional[Signal]:
        """
        Check if any position should take profit
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            
        Returns:
            Take profit signal or None
        """
        for pos_id, position in self.positions.items():
            if (position.get('symbol') == symbol and 
                position.get('status') == 'open' and 
                position.get('side') == 'buy'):
                
                entry_price = position['entry_price']
                profit_pct = ((current_price - entry_price) / entry_price) * 100
                
                if profit_pct >= self.take_profit_pct:
                    return Signal(
                        action=SignalAction.SELL,
                        signal_type=SignalType.TAKE_PROFIT,
                        symbol=symbol,
                        price=current_price,
                        confidence=1.0,
                        reason=f"Grid take profit: +{profit_pct:.2f}% "
                               f"(entry: {entry_price:.2f}, current: {current_price:.2f})",
                        metadata={
                            'position_id': pos_id,
                            'entry_price': entry_price,
                            'profit_pct': profit_pct,
                            'grid_type': 'take_profit'
                        }
                    )
        
        return None
    
    def update_position(self, symbol: str, side: str, price: float, amount: float):
        """
        Override to add grid-specific position tracking
        
        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            price: Entry price
            amount: Position size
        """
        position_id = str(uuid.uuid4())
        self.positions[position_id] = {
            'symbol': symbol,
            'side': side,
            'entry_price': price,
            'amount': amount,
            'timestamp': datetime.now(),
            'status': 'open',
            'grid_strategy': True
        }
    
    def get_status(self) -> Dict[str, Any]:
        """
        Override to include grid-specific status
        
        Returns:
            Dictionary with strategy status including grid info
        """
        status = super().get_status()
        
        # Add grid information
        grid_info = {}
        for symbol, grid in self.grid_levels.items():
            executed_buys = len([l for l in grid['levels'] if l['buy_executed']])
            executed_sells = len([l for l in grid['levels'] if l['sell_executed']])
            
            grid_info[symbol] = {
                'center_price': grid['center_price'],
                'upper_limit': grid['upper_limit'],
                'lower_limit': grid['lower_limit'],
                'total_levels': len(grid['levels']),
                'executed_buys': executed_buys,
                'executed_sells': executed_sells,
                'created_at': grid['created_at'].isoformat()
            }
        
        status['grid_info'] = grid_info
        return status
    
    def reset(self):
        """Reset strategy state including grid levels"""
        super().reset()
        self.grid_levels.clear()
        self.grid_orders.clear()