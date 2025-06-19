# src/core/engine/trading_engine.py

import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
import threading
import time
import uuid

class EngineState(Enum):
    """Trading engine states"""
    CREATED = "created"
    INITIALIZING = "initializing" 
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"

class TradingMode(Enum):
    """Trading modes"""
    LIVE = "live"
    PAPER = "paper"
    BACKTEST = "backtest"

@dataclass
class EngineEvent:
    """Engine event data structure"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = "engine"

@dataclass
class EngineStatus:
    """Engine status information"""
    state: EngineState
    mode: TradingMode
    start_time: Optional[datetime] = None
    uptime_seconds: float = 0
    total_trades: int = 0
    active_trades: int = 0
    last_error: Optional[str] = None
    health_score: float = 100.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'state': self.state.value,
            'mode': self.mode.value,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'uptime_seconds': self.uptime_seconds,
            'total_trades': self.total_trades,
            'active_trades': self.active_trades,
            'last_error': self.last_error,
            'health_score': self.health_score
        }

class TradingEngine:
    """
    Core trading engine with state management and lifecycle control.
    Supports multiple trading modes and provides event-driven architecture.
    """
    
    def __init__(self, settings, logger):
        self.settings = settings
        self.logger = logger
        
        # Engine state
        self._state = EngineState.CREATED
        self._mode = TradingMode.PAPER  # Default to paper trading
        self._state_lock = threading.RLock()
        
        # Status tracking
        self._status = EngineStatus(state=self._state, mode=self._mode)
        self._start_time: Optional[datetime] = None
        self._last_heartbeat = datetime.utcnow()
        
        # Event system
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._event_queue = asyncio.Queue() if asyncio.get_event_loop().is_running() else None
        
        # Components (will be injected)
        self.mode_manager = None
        self.strategy_manager = None
        self.risk_manager = None
        self.order_manager = None
        self.data_manager = None
        
        # Control flags
        self._shutdown_event = threading.Event()
        self._pause_event = threading.Event()
        self._main_loop_task: Optional[asyncio.Task] = None
        
        self.logger.info(f"Trading engine created with config: {self.settings.get('name', 'default')}")
    
    # State Management
    def get_state(self) -> EngineState:
        """Get current engine state"""
        with self._state_lock:
            return self._state
    
    def _set_state(self, new_state: EngineState, error_msg: Optional[str] = None):
        """Internal method to set engine state with event emission"""
        with self._state_lock:
            old_state = self._state
            self._state = new_state
            self._status.state = new_state
            
            if error_msg:
                self._status.last_error = error_msg
                self.logger.error(f"Engine state changed to {new_state.value}: {error_msg}")
            else:
                self.logger.info(f"Engine state changed: {old_state.value} -> {new_state.value}")
            
            # Emit state change event
            self._emit_event("state_changed", {
                "old_state": old_state.value,
                "new_state": new_state.value,
                "error": error_msg
            })
    
    # Lifecycle Methods
    async def initialize(self, mode: TradingMode = TradingMode.PAPER) -> bool:
        """Initialize the trading engine"""
        try:
            self._set_state(EngineState.INITIALIZING)
            self._mode = mode
            self._status.mode = mode
            
            self.logger.info(f"Initializing trading engine in {mode.value} mode")
            
            # Initialize components
            if not await self._initialize_components():
                raise Exception("Failed to initialize engine components")
            
            # Validate configuration
            if not self._validate_configuration():
                raise Exception("Configuration validation failed")
            
            # Setup event queue if not exists
            if self._event_queue is None:
                self._event_queue = asyncio.Queue()
            
            self._set_state(EngineState.STOPPED)
            self.logger.info("Trading engine initialized successfully")
            return True
            
        except Exception as e:
            self._set_state(EngineState.ERROR, str(e))
            return False
    
    async def start(self) -> bool:
        """Start the trading engine"""
        if self._state not in [EngineState.STOPPED, EngineState.PAUSED]:
            self.logger.warning(f"Cannot start engine from state: {self._state.value}")
            return False
        
        try:
            self._set_state(EngineState.RUNNING)
            self._start_time = datetime.utcnow()
            self._status.start_time = self._start_time
            self._shutdown_event.clear()
            self._pause_event.clear()
            
            # Start main loop
            self._main_loop_task = asyncio.create_task(self._main_loop())
            
            self.logger.info("Trading engine started successfully")
            self._emit_event("engine_started", {"mode": self._mode.value})
            return True
            
        except Exception as e:
            self._set_state(EngineState.ERROR, str(e))
            return False
    
    async def stop(self, force: bool = False) -> bool:
        """Stop the trading engine"""
        if self._state == EngineState.STOPPED:
            return True
        
        try:
            self._set_state(EngineState.STOPPING)
            
            # Signal shutdown
            self._shutdown_event.set()
            
            # Cancel main loop task
            if self._main_loop_task and not self._main_loop_task.done():
                if force:
                    self._main_loop_task.cancel()
                else:
                    await asyncio.wait_for(self._main_loop_task, timeout=10.0)
            
            # Cleanup components
            await self._cleanup_components()
            
            self._set_state(EngineState.STOPPED)
            self.logger.info("Trading engine stopped successfully")
            self._emit_event("engine_stopped", {"force": force})
            return True
            
        except Exception as e:
            self._set_state(EngineState.ERROR, str(e))
            return False
    
    async def pause(self) -> bool:
        """Pause the trading engine"""
        if self._state != EngineState.RUNNING:
            return False
        
        try:
            self._pause_event.set()
            self._set_state(EngineState.PAUSED)
            self.logger.info("Trading engine paused")
            self._emit_event("engine_paused", {})
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to pause engine: {e}")
            return False
    
    async def resume(self) -> bool:
        """Resume the trading engine"""
        if self._state != EngineState.PAUSED:
            return False
        
        try:
            self._pause_event.clear()
            self._set_state(EngineState.RUNNING)
            self.logger.info("Trading engine resumed")
            self._emit_event("engine_resumed", {})
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to resume engine: {e}")
            return False
    
    # Status and Health
    def get_status(self) -> EngineStatus:
        """Get current engine status"""
        if self._start_time:
            self._status.uptime_seconds = (datetime.utcnow() - self._start_time).total_seconds()
        
        # Update health score
        self._status.health_score = self._calculate_health_score()
        
        return self._status
    
    def is_healthy(self) -> bool:
        """Check if engine is healthy"""
        return (
            self._state in [EngineState.RUNNING, EngineState.PAUSED] and
            self._calculate_health_score() > 50.0
        )
    
    def _calculate_health_score(self) -> float:
        """Calculate engine health score (0-100)"""
        score = 100.0
        
        # Deduct for error state
        if self._state == EngineState.ERROR:
            score -= 50.0
        
        # Check heartbeat
        time_since_heartbeat = (datetime.utcnow() - self._last_heartbeat).total_seconds()
        if time_since_heartbeat > 60:  # 1 minute
            score -= min(30.0, time_since_heartbeat / 60 * 10)
        
        # Check component health
        if hasattr(self, 'mode_manager') and self.mode_manager:
            if not getattr(self.mode_manager, 'is_healthy', lambda: True)():
                score -= 10.0
        
        return max(0.0, score)
    
    # Event System
    def add_event_handler(self, event_type: str, handler: Callable):
        """Add event handler for specific event type"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
    
    def remove_event_handler(self, event_type: str, handler: Callable):
        """Remove event handler"""
        if event_type in self._event_handlers:
            try:
                self._event_handlers[event_type].remove(handler)
            except ValueError:
                pass
    
    def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit event to all registered handlers"""
        event = EngineEvent(
            event_type=event_type,
            data=data,
            source=f"engine.{self.__class__.__name__}"
        )
        
        # Call synchronous handlers
        if event_type in self._event_handlers:
            for handler in self._event_handlers[event_type]:
                try:
                    handler(event)
                except Exception as e:
                    self.logger.error(f"Error in event handler for {event_type}: {e}")
        
        # Add to async event queue
        if self._event_queue:
            try:
                self._event_queue.put_nowait(event)
            except asyncio.QueueFull:
                self.logger.warning(f"Event queue full, dropping event: {event_type}")
    
    # Main Loop
    async def _main_loop(self):
        """Main engine loop"""
        self.logger.info("Starting main engine loop")
        
        try:
            while not self._shutdown_event.is_set():
                # Check for pause
                if self._pause_event.is_set():
                    await asyncio.sleep(1.0)
                    continue
                
                # Update heartbeat
                self._last_heartbeat = datetime.utcnow()
                
                # Process engine cycle
                await self._process_engine_cycle()
                
                # Process events
                await self._process_events()
                
                # Sleep to prevent CPU overload
                await asyncio.sleep(0.1)
                
        except asyncio.CancelledError:
            self.logger.info("Main loop cancelled")
        except Exception as e:
            self.logger.error(f"Error in main loop: {e}")
            self._set_state(EngineState.ERROR, str(e))
        
        self.logger.info("Main engine loop stopped")
    
    async def _process_engine_cycle(self):
        """Process one engine cycle"""
        try:
            # Update status
            if self.mode_manager:
                await self.mode_manager.process_cycle()
            
            # Process strategies
            if self.strategy_manager:
                await self.strategy_manager.process_cycle()
            
            # Process orders
            if self.order_manager:
                await self.order_manager.process_cycle()
            
        except Exception as e:
            self.logger.error(f"Error in engine cycle: {e}")
    
    async def _process_events(self):
        """Process queued events"""
        if not self._event_queue:
            return
        
        processed = 0
        while not self._event_queue.empty() and processed < 10:  # Limit per cycle
            try:
                event = self._event_queue.get_nowait()
                await self._handle_async_event(event)
                processed += 1
            except asyncio.QueueEmpty:
                break
            except Exception as e:
                self.logger.error(f"Error processing event: {e}")
    
    async def _handle_async_event(self, event: EngineEvent):
        """Handle async event processing"""
        # Override in subclasses for custom event handling
        pass
    
    # Component Management
    async def _initialize_components(self) -> bool:
        """Initialize all engine components"""
        try:
            # Components will be injected by engine factory
            # This is where we would initialize mode_manager, strategy_manager, etc.
            self.logger.info("Components initialization placeholder")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            return False
    
    async def _cleanup_components(self):
        """Cleanup all engine components"""
        try:
            # Cleanup components
            if self.mode_manager:
                await getattr(self.mode_manager, 'cleanup', lambda: None)()
            
            if self.strategy_manager:
                await getattr(self.strategy_manager, 'cleanup', lambda: None)()
            
            if self.order_manager:
                await getattr(self.order_manager, 'cleanup', lambda: None)()
            
            self.logger.info("Components cleaned up successfully")
        except Exception as e:
            self.logger.error(f"Error during component cleanup: {e}")
    
    def _validate_configuration(self) -> bool:
        """Validate engine configuration"""
        required_config = ['name', 'mode']
        
        for key in required_config:
            if key not in self.settings:
                self.logger.error(f"Missing required configuration: {key}")
                return False
        
        return True
    
    # Dependency Injection
    def set_mode_manager(self, mode_manager):
        """Set mode manager component"""
        self.mode_manager = mode_manager
    
    def set_strategy_manager(self, strategy_manager):
        """Set strategy manager component"""
        self.strategy_manager = strategy_manager
    
    def set_risk_manager(self, risk_manager):
        """Set risk manager component"""
        self.risk_manager = risk_manager
    
    def set_order_manager(self, order_manager):
        """Set order manager component"""
        self.order_manager = order_manager
    
    def set_data_manager(self, data_manager):
        """Set data manager component"""
        self.data_manager = data_manager