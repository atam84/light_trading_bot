# src/core/orders/order_manager.py

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid
import json

class OrderType(Enum):
    """Order types"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    STOP_LIMIT = "stop_limit"

class OrderSide(Enum):
    """Order sides"""
    BUY = "buy"
    SELL = "sell"

class OrderStatus(Enum):
    """Order statuses"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL_FILLED = "partial_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    ERROR = "error"

class OrderPriority(Enum):
    """Order priorities"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

@dataclass
class Order:
    """Order data structure"""
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    client_order_id: str = ""
    exchange_order_id: str = ""
    
    # Basic order info
    symbol: str = ""
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.MARKET
    amount: float = 0.0
    price: Optional[float] = None
    
    # Execution info
    filled_amount: float = 0.0
    remaining_amount: float = 0.0
    average_price: float = 0.0
    total_fee: float = 0.0
    
    # Status and timing
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Trading context
    strategy_name: str = ""
    trading_mode: str = "paper"  # live, paper, backtest
    priority: OrderPriority = OrderPriority.NORMAL
    
    # Stop loss and take profit
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        self.remaining_amount = self.amount
        if not self.client_order_id:
            self.client_order_id = f"client_{self.order_id[:8]}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert order to dictionary"""
        return {
            'order_id': self.order_id,
            'client_order_id': self.client_order_id,
            'exchange_order_id': self.exchange_order_id,
            'symbol': self.symbol,
            'side': self.side.value,
            'order_type': self.order_type.value,
            'amount': self.amount,
            'price': self.price,
            'filled_amount': self.filled_amount,
            'remaining_amount': self.remaining_amount,
            'average_price': self.average_price,
            'total_fee': self.total_fee,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'filled_at': self.filled_at.isoformat() if self.filled_at else None,
            'updated_at': self.updated_at.isoformat(),
            'strategy_name': self.strategy_name,
            'trading_mode': self.trading_mode,
            'priority': self.priority.value,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'metadata': self.metadata,
            'error_message': self.error_message,
            'retry_count': self.retry_count
        }
    
    def update_status(self, status: OrderStatus, message: str = ""):
        """Update order status"""
        self.status = status
        self.updated_at = datetime.utcnow()
        if message:
            self.error_message = message
        
        if status == OrderStatus.SUBMITTED:
            self.submitted_at = datetime.utcnow()
        elif status in [OrderStatus.FILLED, OrderStatus.PARTIAL_FILLED]:
            self.filled_at = datetime.utcnow()
    
    def is_active(self) -> bool:
        """Check if order is still active"""
        return self.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIAL_FILLED]
    
    def is_terminal(self) -> bool:
        """Check if order is in terminal state"""
        return self.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED, OrderStatus.EXPIRED, OrderStatus.ERROR]
    
    def get_fill_percentage(self) -> float:
        """Get fill percentage"""
        if self.amount == 0:
            return 0.0
        return (self.filled_amount / self.amount) * 100

@dataclass
class ExecutionReport:
    """Order execution report"""
    report_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str = ""
    exchange_order_id: str = ""
    execution_price: float = 0.0
    execution_amount: float = 0.0
    execution_fee: float = 0.0
    execution_time: datetime = field(default_factory=datetime.utcnow)
    trade_id: str = ""
    is_partial: bool = False

class OrderManager:
    """Order management system with execution queue and lifecycle tracking"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Order storage
        self._orders: Dict[str, Order] = {}
        self._execution_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._execution_reports: List[ExecutionReport] = []
        
        # Event handlers
        self._order_handlers: Dict[str, List[Callable]] = {}
        
        # Execution settings
        self.max_concurrent_executions = config.get('max_concurrent_executions', 5)
        self.execution_timeout = config.get('execution_timeout', 30)  # seconds
        self.retry_delay = config.get('retry_delay', 5)  # seconds
        
        # Trading mode manager reference (will be injected)
        self.mode_manager = None
        
        # Execution workers
        self._execution_workers: List[asyncio.Task] = []
        self._execution_enabled = False
        
        self.logger.info("Order manager initialized")
    
    async def initialize(self) -> bool:
        """Initialize order manager"""
        try:
            # Start execution workers
            await self._start_execution_workers()
            self._execution_enabled = True
            
            self.logger.info("Order manager initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize order manager: {e}")
            return False
    
    async def _start_execution_workers(self):
        """Start order execution workers"""
        for i in range(self.max_concurrent_executions):
            worker = asyncio.create_task(self._execution_worker(f"worker_{i}"))
            self._execution_workers.append(worker)
        
        self.logger.info(f"Started {len(self._execution_workers)} execution workers")
    
    async def _stop_execution_workers(self):
        """Stop order execution workers"""
        self._execution_enabled = False
        
        # Cancel all workers
        for worker in self._execution_workers:
            worker.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*self._execution_workers, return_exceptions=True)
        
        self._execution_workers.clear()
        self.logger.info("All execution workers stopped")
    
    async def submit_order(self, order: Order) -> bool:
        """Submit order for execution"""
        try:
            # Validate order
            if not self._validate_order(order):
                order.update_status(OrderStatus.REJECTED, "Order validation failed")
                return False
            
            # Store order
            self._orders[order.order_id] = order
            
            # Add to execution queue with priority
            priority = -order.priority.value  # Negative for high priority first
            await self._execution_queue.put((priority, order.created_at, order.order_id))
            
            order.update_status(OrderStatus.PENDING)
            
            self.logger.info(f"Order submitted: {order.order_id} - {order.symbol} {order.side.value} {order.amount}")
            
            # Emit order event
            await self._emit_order_event("order_submitted", order)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to submit order {order.order_id}: {e}")
            order.update_status(OrderStatus.ERROR, str(e))
            return False
    
    def _validate_order(self, order: Order) -> bool:
        """Validate order before submission"""
        try:
            # Basic validation
            if not order.symbol:
                self.logger.error("Order missing symbol")
                return False
            
            if order.amount <= 0:
                self.logger.error("Order amount must be positive")
                return False
            
            if order.order_type == OrderType.LIMIT and not order.price:
                self.logger.error("Limit order missing price")
                return False
            
            if order.order_type == OrderType.LIMIT and order.price <= 0:
                self.logger.error("Order price must be positive")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating order: {e}")
            return False
    
    async def cancel_order(self, order_id: str, reason: str = "User request") -> bool:
        """Cancel an order"""
        try:
            order = self._orders.get(order_id)
            if not order:
                self.logger.warning(f"Order not found for cancellation: {order_id}")
                return False
            
            if order.is_terminal():
                self.logger.warning(f"Cannot cancel order in terminal state: {order.status.value}")
                return False
            
            # Cancel with exchange if submitted
            if order.status == OrderStatus.SUBMITTED and order.exchange_order_id:
                success = await self._cancel_with_exchange(order)
                if not success:
                    self.logger.error(f"Failed to cancel order with exchange: {order_id}")
                    return False
            
            # Update order status
            order.update_status(OrderStatus.CANCELLED, reason)
            
            self.logger.info(f"Order cancelled: {order_id} - Reason: {reason}")
            
            # Emit order event
            await self._emit_order_event("order_cancelled", order)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cancel order {order_id}: {e}")
            return False
    
    async def _cancel_with_exchange(self, order: Order) -> bool:
        """Cancel order with exchange"""
        try:
            if not self.mode_manager:
                self.logger.error("Mode manager not available for order cancellation")
                return False
            
            current_mode = self.mode_manager.get_current_mode()
            if not current_mode:
                self.logger.error("No active trading mode for order cancellation")
                return False
            
            # Cancel with current mode
            success = await current_mode.cancel_order(order.exchange_order_id)
            return success
            
        except Exception as e:
            self.logger.error(f"Error cancelling order with exchange: {e}")
            return False
    
    async def _execution_worker(self, worker_name: str):
        """Order execution worker"""
        self.logger.info(f"Execution worker {worker_name} started")
        
        while self._execution_enabled:
            try:
                # Get order from queue with timeout
                try:
                    priority, created_at, order_id = await asyncio.wait_for(
                        self._execution_queue.get(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Get order
                order = self._orders.get(order_id)
                if not order:
                    continue
                
                # Skip if order is no longer active
                if not order.is_active():
                    continue
                
                # Execute order
                await self._execute_order(order, worker_name)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in execution worker {worker_name}: {e}")
                await asyncio.sleep(1)
        
        self.logger.info(f"Execution worker {worker_name} stopped")
    
    async def _execute_order(self, order: Order, worker_name: str):
        """Execute an order"""
        try:
            self.logger.info(f"[{worker_name}] Executing order: {order.order_id}")
            
            # Check if mode manager is available
            if not self.mode_manager:
                raise Exception("Mode manager not available")
            
            current_mode = self.mode_manager.get_current_mode()
            if not current_mode:
                raise Exception("No active trading mode")
            
            # Update order status
            order.update_status(OrderStatus.SUBMITTED)
            await self._emit_order_event("order_submitted", order)
            
            # Execute trade through current mode
            execution_result = await asyncio.wait_for(
                current_mode.execute_trade(
                    symbol=order.symbol,
                    side=order.side.value,
                    amount=order.amount,
                    price=order.price,
                    order_type=order.order_type.value
                ),
                timeout=self.execution_timeout
            )
            
            # Process execution result
            await self._process_execution_result(order, execution_result)
            
            self.logger.info(f"[{worker_name}] Order executed successfully: {order.order_id}")
            
        except asyncio.TimeoutError:
            self.logger.error(f"Order execution timeout: {order.order_id}")
            await self._handle_execution_error(order, "Execution timeout")
            
        except Exception as e:
            self.logger.error(f"Order execution failed: {order.order_id} - {e}")
            await self._handle_execution_error(order, str(e))
    
    async def _process_execution_result(self, order: Order, result: Dict[str, Any]):
        """Process order execution result"""
        try:
            # Update order with execution data
            order.exchange_order_id = result.get('id', '')
            
            if result.get('status') == 'filled':
                # Full fill
                order.filled_amount = result.get('amount', order.amount)
                order.remaining_amount = 0.0
                order.average_price = result.get('price', order.price or 0.0)
                order.total_fee = result.get('fee', 0.0)
                order.update_status(OrderStatus.FILLED)
                
                # Create execution report
                execution_report = ExecutionReport(
                    order_id=order.order_id,
                    exchange_order_id=order.exchange_order_id,
                    execution_price=order.average_price,
                    execution_amount=order.filled_amount,
                    execution_fee=order.total_fee,
                    trade_id=result.get('trade_id', ''),
                    is_partial=False
                )
                self._execution_reports.append(execution_report)
                
                await self._emit_order_event("order_filled", order)
                
            elif result.get('status') == 'partial':
                # Partial fill
                filled_amount = result.get('filled_amount', 0.0)
                order.filled_amount += filled_amount
                order.remaining_amount = order.amount - order.filled_amount
                order.update_status(OrderStatus.PARTIAL_FILLED)
                
                # Create execution report for partial fill
                execution_report = ExecutionReport(
                    order_id=order.order_id,
                    exchange_order_id=order.exchange_order_id,
                    execution_price=result.get('price', 0.0),
                    execution_amount=filled_amount,
                    execution_fee=result.get('fee', 0.0),
                    trade_id=result.get('trade_id', ''),
                    is_partial=True
                )
                self._execution_reports.append(execution_report)
                
                await self._emit_order_event("order_partial_filled", order)
                
            else:
                # Handle other statuses
                order.update_status(OrderStatus.SUBMITTED)
            
            # Update average price calculation
            if order.filled_amount > 0:
                total_value = sum(
                    report.execution_price * report.execution_amount
                    for report in self._execution_reports
                    if report.order_id == order.order_id
                )
                order.average_price = total_value / order.filled_amount
                
                # Update total fees
                order.total_fee = sum(
                    report.execution_fee
                    for report in self._execution_reports
                    if report.order_id == order.order_id
                )
            
        except Exception as e:
            self.logger.error(f"Error processing execution result: {e}")
            await self._handle_execution_error(order, f"Result processing error: {e}")
    
    async def _handle_execution_error(self, order: Order, error_message: str):
        """Handle order execution error"""
        try:
            order.retry_count += 1
            
            if order.retry_count <= order.max_retries:
                # Retry after delay
                self.logger.info(f"Retrying order execution: {order.order_id} (attempt {order.retry_count})")
                
                # Add back to queue with delay
                await asyncio.sleep(self.retry_delay)
                priority = -order.priority.value
                await self._execution_queue.put((priority, datetime.utcnow(), order.order_id))
                
            else:
                # Max retries exceeded
                order.update_status(OrderStatus.ERROR, f"Max retries exceeded: {error_message}")
                await self._emit_order_event("order_error", order)
                
        except Exception as e:
            self.logger.error(f"Error handling execution error: {e}")
            order.update_status(OrderStatus.ERROR, str(e))
    
    # Event system
    def add_order_handler(self, event_type: str, handler: Callable):
        """Add order event handler"""
        if event_type not in self._order_handlers:
            self._order_handlers[event_type] = []
        self._order_handlers[event_type].append(handler)
    
    async def _emit_order_event(self, event_type: str, order: Order):
        """Emit order event"""
        if event_type in self._order_handlers:
            for handler in self._order_handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(order)
                    else:
                        handler(order)
                except Exception as e:
                    self.logger.error(f"Error in order event handler: {e}")
    
    # Order queries
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return self._orders.get(order_id)
    
    def get_orders(self, status: Optional[OrderStatus] = None, 
                   symbol: Optional[str] = None,
                   strategy: Optional[str] = None) -> List[Order]:
        """Get orders with optional filters"""
        orders = list(self._orders.values())
        
        if status:
            orders = [o for o in orders if o.status == status]
        
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        
        if strategy:
            orders = [o for o in orders if o.strategy_name == strategy]
        
        return orders
    
    def get_active_orders(self) -> List[Order]:
        """Get all active orders"""
        return [order for order in self._orders.values() if order.is_active()]
    
    def get_filled_orders(self, since: Optional[datetime] = None) -> List[Order]:
        """Get filled orders"""
        orders = [order for order in self._orders.values() if order.status == OrderStatus.FILLED]
        
        if since:
            orders = [order for order in orders if order.filled_at and order.filled_at >= since]
        
        return orders
    
    def get_execution_reports(self, order_id: Optional[str] = None) -> List[ExecutionReport]:
        """Get execution reports"""
        if order_id:
            return [report for report in self._execution_reports if report.order_id == order_id]
        return self._execution_reports.copy()
    
    # Statistics
    def get_order_statistics(self) -> Dict[str, Any]:
        """Get order statistics"""
        total_orders = len(self._orders)
        if total_orders == 0:
            return {}
        
        status_counts = {}
        for status in OrderStatus:
            status_counts[status.value] = len([o for o in self._orders.values() if o.status == status])
        
        filled_orders = [o for o in self._orders.values() if o.status == OrderStatus.FILLED]
        
        return {
            'total_orders': total_orders,
            'active_orders': len(self.get_active_orders()),
            'status_breakdown': status_counts,
            'fill_rate': len(filled_orders) / total_orders * 100 if total_orders > 0 else 0,
            'avg_execution_time': self._calculate_avg_execution_time(),
            'total_volume': sum(o.filled_amount * o.average_price for o in filled_orders),
            'total_fees': sum(o.total_fee for o in filled_orders),
            'queue_size': self._execution_queue.qsize()
        }
    
    def _calculate_avg_execution_time(self) -> float:
        """Calculate average execution time in seconds"""
        filled_orders = [o for o in self._orders.values() 
                        if o.status == OrderStatus.FILLED and o.submitted_at and o.filled_at]
        
        if not filled_orders:
            return 0.0
        
        total_time = sum((o.filled_at - o.submitted_at).total_seconds() for o in filled_orders)
        return total_time / len(filled_orders)
    
    # Lifecycle
    async def process_cycle(self):
        """Process order manager cycle"""
        try:
            # Update order statuses for submitted orders
            await self._update_order_statuses()
            
            # Clean up old completed orders
            await self._cleanup_old_orders()
            
        except Exception as e:
            self.logger.error(f"Error in order manager cycle: {e}")
    
    async def _update_order_statuses(self):
        """Update statuses for submitted orders"""
        # This would query exchange for order status updates
        # For now, it's a placeholder for status synchronization
        pass
    
    async def _cleanup_old_orders(self):
        """Clean up old completed orders"""
        cutoff_time = datetime.utcnow() - timedelta(days=7)  # Keep 7 days
        
        orders_to_remove = []
        for order_id, order in self._orders.items():
            if order.is_terminal() and order.updated_at < cutoff_time:
                orders_to_remove.append(order_id)
        
        for order_id in orders_to_remove:
            del self._orders[order_id]
        
        if orders_to_remove:
            self.logger.info(f"Cleaned up {len(orders_to_remove)} old orders")
    
    def is_healthy(self) -> bool:
        """Check if order manager is healthy"""
        return (
            self._execution_enabled and
            len(self._execution_workers) > 0 and
            not any(worker.done() for worker in self._execution_workers)
        )
    
    def set_mode_manager(self, mode_manager):
        """Set mode manager reference"""
        self.mode_manager = mode_manager
    
    async def cleanup(self):
        """Cleanup order manager"""
        await self._stop_execution_workers()
        self._orders.clear()
        self._execution_reports.clear()
        self._order_handlers.clear()
        
        # Clear queue
        while not self._execution_queue.empty():
            try:
                self._execution_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        
        self.logger.info("Order manager cleaned up")