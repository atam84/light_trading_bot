# src/core/engine/mode_manager.py

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from .trading_engine import TradingMode, EngineEvent

class ModeState(Enum):
    """Mode states"""
    INACTIVE = "inactive"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ERROR = "error"

@dataclass
class ModeStatus:
    """Mode status information"""
    mode: TradingMode
    state: ModeState
    start_time: Optional[datetime] = None
    trades_executed: int = 0
    last_error: Optional[str] = None
    balance: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0

class BaseTradingMode(ABC):
    """Abstract base class for trading modes"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._state = ModeState.INACTIVE
        self._status = ModeStatus(mode=self.get_mode(), state=self._state)
        self._last_update = datetime.utcnow()
    
    @abstractmethod
    def get_mode(self) -> TradingMode:
        """Get the trading mode type"""
        pass
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the trading mode"""
        pass
    
    @abstractmethod
    async def execute_trade(self, symbol: str, side: str, amount: float, 
                          price: Optional[float] = None, order_type: str = "market") -> Dict[str, Any]:
        """Execute a trade in this mode"""
        pass
    
    @abstractmethod
    async def get_balance(self, asset: str = "USDT") -> float:
        """Get balance for specific asset"""
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions"""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        pass
    
    async def process_cycle(self):
        """Process one cycle of the trading mode"""
        self._last_update = datetime.utcnow()
        await self._update_status()
    
    async def _update_status(self):
        """Update mode status"""
        try:
            self._status.balance = await self.get_balance()
            # Update other status fields as needed
        except Exception as e:
            self.logger.error(f"Error updating status: {e}")
    
    def get_status(self) -> ModeStatus:
        """Get current mode status"""
        return self._status
    
    def is_healthy(self) -> bool:
        """Check if mode is healthy"""
        return (
            self._state == ModeState.ACTIVE and
            (datetime.utcnow() - self._last_update).total_seconds() < 300  # 5 minutes
        )
    
    async def cleanup(self):
        """Cleanup mode resources"""
        self._state = ModeState.INACTIVE
        self.logger.info(f"{self.get_mode().value} mode cleaned up")

class LiveTradingMode(BaseTradingMode):
    """Live trading mode with real money"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.exchange_client = None
        self.api_key = config.get('api_key')
        self.api_secret = config.get('api_secret')
        self.exchange_name = config.get('exchange', 'kucoin')
        self.testnet = config.get('testnet', False)
    
    def get_mode(self) -> TradingMode:
        return TradingMode.LIVE
    
    async def initialize(self) -> bool:
        """Initialize live trading mode"""
        try:
            self._state = ModeState.INITIALIZING
            
            # Validate API credentials
            if not self.api_key or not self.api_secret:
                raise ValueError("API credentials required for live trading")
            
            # Initialize exchange client (placeholder for ccxt-gateway integration)
            await self._initialize_exchange_client()
            
            # Test connection
            await self._test_connection()
            
            self._state = ModeState.ACTIVE
            self._status.start_time = datetime.utcnow()
            self.logger.info("Live trading mode initialized successfully")
            return True
            
        except Exception as e:
            self._state = ModeState.ERROR
            self._status.last_error = str(e)
            self.logger.error(f"Failed to initialize live trading mode: {e}")
            return False
    
    async def _initialize_exchange_client(self):
        """Initialize exchange client"""
        # This will integrate with ccxt-gateway
        self.logger.info(f"Initializing {self.exchange_name} client")
        # Placeholder: self.exchange_client = ExchangeClient(...)
    
    async def _test_connection(self):
        """Test exchange connection"""
        # Test API connection
        self.logger.info("Testing exchange connection")
        # Placeholder: await self.exchange_client.test_connection()
    
    async def execute_trade(self, symbol: str, side: str, amount: float, 
                          price: Optional[float] = None, order_type: str = "market") -> Dict[str, Any]:
        """Execute a real trade"""
        try:
            self.logger.info(f"Executing LIVE trade: {side} {amount} {symbol}")
            
            # Prepare trade data
            trade_data = {
                "symbol": symbol,
                "side": side,
                "type": order_type,
                "amount": amount
            }
            
            if price and order_type == "limit":
                trade_data["price"] = price
            
            # Execute via ccxt-gateway
            # result = await self.exchange_client.create_order(**trade_data)
            
            # Placeholder result
            result = {
                "id": f"live_order_{datetime.utcnow().timestamp()}",
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "price": price,
                "status": "filled",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self._status.trades_executed += 1
            self.logger.info(f"Live trade executed: {result['id']}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to execute live trade: {e}")
            raise
    
    async def get_balance(self, asset: str = "USDT") -> float:
        """Get real account balance"""
        try:
            # Get balance via ccxt-gateway
            # balance = await self.exchange_client.get_balance()
            # return balance.get(asset, 0.0)
            
            # Placeholder
            return 1000.0
            
        except Exception as e:
            self.logger.error(f"Failed to get balance: {e}")
            return 0.0
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get real positions"""
        try:
            # Get positions via ccxt-gateway
            # return await self.exchange_client.get_positions()
            
            # Placeholder
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to get positions: {e}")
            return []
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a real order"""
        try:
            # Cancel via ccxt-gateway
            # await self.exchange_client.cancel_order(order_id)
            
            self.logger.info(f"Live order cancelled: {order_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cancel order {order_id}: {e}")
            return False

class PaperTradingMode(BaseTradingMode):
    """Paper trading mode with simulated trades"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.initial_balance = config.get('initial_balance', 10000.0)
        self.current_balance = self.initial_balance
        self.positions = {}
        self.orders = {}
        self.trade_history = []
        self.fee_rate = config.get('fee_rate', 0.0005)  # 0.05%
        self.slippage = config.get('slippage', 0.0002)  # 0.02%
    
    def get_mode(self) -> TradingMode:
        return TradingMode.PAPER
    
    async def initialize(self) -> bool:
        """Initialize paper trading mode"""
        try:
            self._state = ModeState.INITIALIZING
            
            # Reset paper trading state
            self.current_balance = self.initial_balance
            self.positions.clear()
            self.orders.clear()
            self.trade_history.clear()
            
            self._state = ModeState.ACTIVE
            self._status.start_time = datetime.utcnow()
            self._status.balance = self.current_balance
            
            self.logger.info(f"Paper trading mode initialized with ${self.initial_balance}")
            return True
            
        except Exception as e:
            self._state = ModeState.ERROR
            self._status.last_error = str(e)
            self.logger.error(f"Failed to initialize paper trading mode: {e}")
            return False
    
    async def execute_trade(self, symbol: str, side: str, amount: float, 
                          price: Optional[float] = None, order_type: str = "market") -> Dict[str, Any]:
        """Execute a simulated trade"""
        try:
            self.logger.info(f"Executing PAPER trade: {side} {amount} {symbol}")
            
            # Get current market price (would come from data manager)
            market_price = await self._get_market_price(symbol)
            
            # Calculate execution price with slippage
            if order_type == "market":
                execution_price = self._apply_slippage(market_price, side)
            else:
                execution_price = price or market_price
            
            # Calculate trade value and fees
            trade_value = amount * execution_price
            fee = trade_value * self.fee_rate
            
            # Validate trade
            if side == "buy" and (trade_value + fee) > self.current_balance:
                raise ValueError("Insufficient balance for paper trade")
            
            # Execute the simulated trade
            order_id = f"paper_{datetime.utcnow().timestamp()}"
            
            if side == "buy":
                self.current_balance -= (trade_value + fee)
                if symbol in self.positions:
                    self.positions[symbol] += amount
                else:
                    self.positions[symbol] = amount
            else:  # sell
                if symbol not in self.positions or self.positions[symbol] < amount:
                    raise ValueError("Insufficient position for sell order")
                
                self.positions[symbol] -= amount
                self.current_balance += (trade_value - fee)
                
                if self.positions[symbol] == 0:
                    del self.positions[symbol]
            
            # Record trade
            trade_record = {
                "id": order_id,
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "price": execution_price,
                "fee": fee,
                "status": "filled",
                "timestamp": datetime.utcnow().isoformat(),
                "mode": "paper"
            }
            
            self.trade_history.append(trade_record)
            self._status.trades_executed += 1
            self._status.balance = self.current_balance
            
            self.logger.info(f"Paper trade executed: {order_id} at ${execution_price}")
            return trade_record
            
        except Exception as e:
            self.logger.error(f"Failed to execute paper trade: {e}")
            raise
    
    async def _get_market_price(self, symbol: str) -> float:
        """Get current market price"""
        # This would integrate with data manager to get real-time price
        # Placeholder: return random price around 45000 for BTC/USDT
        import random
        base_price = 45000.0
        return base_price * (1 + random.uniform(-0.01, 0.01))  # ±1% variation
    
    def _apply_slippage(self, price: float, side: str) -> float:
        """Apply slippage to execution price"""
        if side == "buy":
            return price * (1 + self.slippage)
        else:
            return price * (1 - self.slippage)
    
    async def get_balance(self, asset: str = "USDT") -> float:
        """Get simulated balance"""
        if asset == "USDT":
            return self.current_balance
        elif asset in self.positions:
            return self.positions[asset]
        else:
            return 0.0
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get simulated positions"""
        positions = []
        for symbol, amount in self.positions.items():
            # Get current market price for PnL calculation
            current_price = await self._get_market_price(symbol)
            
            positions.append({
                "symbol": symbol,
                "amount": amount,
                "current_price": current_price,
                "market_value": amount * current_price,
                "unrealized_pnl": 0.0  # Would calculate based on entry price
            })
        
        return positions
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a simulated order"""
        if order_id in self.orders:
            del self.orders[order_id]
            self.logger.info(f"Paper order cancelled: {order_id}")
            return True
        return False

class BacktestingMode(BaseTradingMode):
    """Backtesting mode with historical data"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.initial_balance = config.get('initial_balance', 10000.0)
        self.current_balance = self.initial_balance
        self.positions = {}
        self.trade_history = []
        self.fee_rate = config.get('fee_rate', 0.0005)
        self.slippage = config.get('slippage', 0.0002)
        
        # Backtest specific
        self.start_date = config.get('start_date')
        self.end_date = config.get('end_date')
        self.current_time = None
        self.historical_data = {}
    
    def get_mode(self) -> TradingMode:
        return TradingMode.BACKTEST
    
    async def initialize(self) -> bool:
        """Initialize backtesting mode"""
        try:
            self._state = ModeState.INITIALIZING
            
            # Validate backtest parameters
            if not self.start_date or not self.end_date:
                raise ValueError("Start and end dates required for backtesting")
            
            # Reset backtest state
            self.current_balance = self.initial_balance
            self.positions.clear()
            self.trade_history.clear()
            
            # Load historical data (placeholder)
            await self._load_historical_data()
            
            self._state = ModeState.ACTIVE
            self._status.start_time = datetime.utcnow()
            self._status.balance = self.current_balance
            
            self.logger.info(f"Backtest mode initialized: {self.start_date} to {self.end_date}")
            return True
            
        except Exception as e:
            self._state = ModeState.ERROR
            self._status.last_error = str(e)
            self.logger.error(f"Failed to initialize backtest mode: {e}")
            return False
    
    async def _load_historical_data(self):
        """Load historical market data"""
        # This would load data from ccxt-gateway or cached data
        self.logger.info("Loading historical data for backtesting")
        # Placeholder implementation
    
    async def execute_trade(self, symbol: str, side: str, amount: float, 
                          price: Optional[float] = None, order_type: str = "market") -> Dict[str, Any]:
        """Execute a backtest trade"""
        try:
            # Get historical price at current backtest time
            historical_price = await self._get_historical_price(symbol)
            
            # Apply fees and slippage
            execution_price = self._apply_slippage(historical_price, side)
            trade_value = amount * execution_price
            fee = trade_value * self.fee_rate
            
            # Validate and execute trade (similar to paper trading)
            if side == "buy" and (trade_value + fee) > self.current_balance:
                raise ValueError("Insufficient balance for backtest trade")
            
            order_id = f"backtest_{len(self.trade_history)}"
            
            if side == "buy":
                self.current_balance -= (trade_value + fee)
                self.positions[symbol] = self.positions.get(symbol, 0) + amount
            else:
                if self.positions.get(symbol, 0) < amount:
                    raise ValueError("Insufficient position for sell order")
                self.positions[symbol] -= amount
                self.current_balance += (trade_value - fee)
            
            # Record trade
            trade_record = {
                "id": order_id,
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "price": execution_price,
                "fee": fee,
                "status": "filled",
                "timestamp": self.current_time.isoformat() if self.current_time else datetime.utcnow().isoformat(),
                "mode": "backtest"
            }
            
            self.trade_history.append(trade_record)
            self._status.trades_executed += 1
            
            return trade_record
            
        except Exception as e:
            self.logger.error(f"Failed to execute backtest trade: {e}")
            raise
    
    async def _get_historical_price(self, symbol: str) -> float:
        """Get historical price at current backtest time"""
        # This would look up price from historical data
        # Placeholder
        return 45000.0
    
    def _apply_slippage(self, price: float, side: str) -> float:
        """Apply slippage to execution price"""
        if side == "buy":
            return price * (1 + self.slippage)
        else:
            return price * (1 - self.slippage)
    
    async def get_balance(self, asset: str = "USDT") -> float:
        """Get backtest balance"""
        if asset == "USDT":
            return self.current_balance
        return self.positions.get(asset, 0.0)
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get backtest positions"""
        positions = []
        for symbol, amount in self.positions.items():
            current_price = await self._get_historical_price(symbol)
            positions.append({
                "symbol": symbol,
                "amount": amount,
                "current_price": current_price,
                "market_value": amount * current_price
            })
        return positions
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order in backtest (typically not used)"""
        return True

class ModeManager:
    """Manager for trading modes with switching capabilities"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        self._current_mode: Optional[BaseTradingMode] = None
        self._mode_instances: Dict[TradingMode, BaseTradingMode] = {}
        
        # Initialize mode instances
        self._initialize_modes()
    
    def _initialize_modes(self):
        """Initialize all trading mode instances"""
        try:
            # Live trading mode
            live_config = self.config.get('live', {})
            self._mode_instances[TradingMode.LIVE] = LiveTradingMode(live_config)
            
            # Paper trading mode
            paper_config = self.config.get('paper', {})
            self._mode_instances[TradingMode.PAPER] = PaperTradingMode(paper_config)
            
            # Backtesting mode
            backtest_config = self.config.get('backtest', {})
            self._mode_instances[TradingMode.BACKTEST] = BacktestingMode(backtest_config)
            
            self.logger.info("All trading modes initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize trading modes: {e}")
            raise
    
    async def set_mode(self, mode: TradingMode) -> bool:
        """Switch to specified trading mode"""
        try:
            # Cleanup current mode
            if self._current_mode:
                await self._current_mode.cleanup()
            
            # Switch to new mode
            new_mode = self._mode_instances.get(mode)
            if not new_mode:
                raise ValueError(f"Trading mode not available: {mode.value}")
            
            # Initialize new mode
            if not await new_mode.initialize():
                raise Exception(f"Failed to initialize {mode.value} mode")
            
            self._current_mode = new_mode
            self.logger.info(f"Switched to {mode.value} trading mode")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to switch to {mode.value} mode: {e}")
            return False
    
    def get_current_mode(self) -> Optional[BaseTradingMode]:
        """Get current active trading mode"""
        return self._current_mode
    
    def get_mode_type(self) -> Optional[TradingMode]:
        """Get current mode type"""
        return self._current_mode.get_mode() if self._current_mode else None
    
    async def process_cycle(self):
        """Process cycle for current mode"""
        if self._current_mode:
            await self._current_mode.process_cycle()
    
    def is_healthy(self) -> bool:
        """Check if mode manager is healthy"""
        return (
            self._current_mode is not None and
            self._current_mode.is_healthy()
        )
    
    async def cleanup(self):
        """Cleanup all modes"""
        if self._current_mode:
            await self._current_mode.cleanup()
        
        for mode_instance in self._mode_instances.values():
            await mode_instance.cleanup()
        
        self.logger.info("Mode manager cleaned up")