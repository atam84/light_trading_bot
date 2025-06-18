# src/core/risk/risk_manager.py

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid

class RiskLevel(Enum):
    """Risk levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class RiskAction(Enum):
    """Risk management actions"""
    ALLOW = "allow"
    REDUCE = "reduce"
    BLOCK = "block"
    EMERGENCY_STOP = "emergency_stop"

@dataclass
class RiskRule:
    """Risk management rule"""
    rule_id: str
    name: str
    description: str
    rule_type: str  # balance, position, trade_frequency, etc.
    threshold: float
    action: RiskAction
    enabled: bool = True
    priority: int = 1  # Higher number = higher priority

@dataclass
class RiskViolation:
    """Risk rule violation"""
    violation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    rule_id: str = ""
    rule_name: str = ""
    current_value: float = 0.0
    threshold: float = 0.0
    violation_percentage: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    action_taken: RiskAction = RiskAction.ALLOW
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TradeValidationRequest:
    """Trade validation request"""
    symbol: str
    side: str  # buy, sell
    amount: float
    price: float
    order_type: str = "market"
    strategy_name: str = ""
    mode: str = "paper"  # live, paper, backtest

@dataclass
class TradeValidationResult:
    """Trade validation result"""
    is_valid: bool
    action: RiskAction
    adjusted_amount: Optional[float] = None
    adjusted_price: Optional[float] = None
    violations: List[RiskViolation] = field(default_factory=list)
    risk_score: float = 0.0
    reason: str = ""

@dataclass
class PositionInfo:
    """Position information for risk calculation"""
    symbol: str
    amount: float
    entry_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    percentage_of_portfolio: float

@dataclass
class RiskMetrics:
    """Risk metrics and statistics"""
    total_balance: float = 0.0
    available_balance: float = 0.0
    allocated_balance: float = 0.0
    allocation_percentage: float = 0.0
    total_positions: int = 0
    max_position_exposure: float = 0.0
    portfolio_concentration: float = 0.0
    daily_trades: int = 0
    hourly_trades: int = 0
    last_updated: datetime = field(default_factory=datetime.utcnow)

class RiskManager:
    """Comprehensive risk management system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Risk rules storage
        self._risk_rules: Dict[str, RiskRule] = {}
        self._violation_history: List[RiskViolation] = []
        
        # Risk state tracking
        self._current_positions: Dict[str, PositionInfo] = {}
        self._trade_history: List[Dict[str, Any]] = []
        self._risk_metrics = RiskMetrics()
        
        # Emergency state
        self._emergency_stop = False
        self._emergency_reason = ""
        
        # Risk limits from config
        self._load_risk_limits()
        self._initialize_default_rules()
    
    def _load_risk_limits(self):
        """Load risk limits from configuration"""
        risk_config = self.config.get('risk_management', {})
        
        # Balance limits
        self.max_allocation_percentage = risk_config.get('max_allocation_percentage', 0.5)  # 50%
        self.max_trade_amount = risk_config.get('max_trade_amount', 1000.0)  # $1000
        self.min_trade_amount = risk_config.get('min_trade_amount', 10.0)  # $10
        
        # Position limits
        self.max_positions = risk_config.get('max_positions', 10)
        self.max_positions_per_symbol = risk_config.get('max_positions_per_symbol', 2)
        self.max_position_size = risk_config.get('max_position_size', 0.1)  # 10% of portfolio
        
        # Trading frequency limits
        self.max_trades_per_hour = risk_config.get('max_trades_per_hour', 20)
        self.max_trades_per_day = risk_config.get('max_trades_per_day', 100)
        
        # Stop loss and take profit
        self.default_stop_loss_pct = risk_config.get('default_stop_loss_pct', 0.05)  # 5%
        self.default_take_profit_pct = risk_config.get('default_take_profit_pct', 0.15)  # 15%
        
        # Drawdown limits
        self.max_daily_loss_pct = risk_config.get('max_daily_loss_pct', 0.02)  # 2%
        self.max_total_drawdown_pct = risk_config.get('max_total_drawdown_pct', 0.1)  # 10%
        
        self.logger.info("Risk limits loaded from configuration")
    
    def _initialize_default_rules(self):
        """Initialize default risk rules"""
        # Balance allocation rule
        self.add_risk_rule(RiskRule(
            rule_id="balance_allocation",
            name="Balance Allocation Limit",
            description=f"Maximum {self.max_allocation_percentage*100}% of balance allocation",
            rule_type="balance",
            threshold=self.max_allocation_percentage,
            action=RiskAction.BLOCK,
            priority=10
        ))
        
        # Maximum positions rule
        self.add_risk_rule(RiskRule(
            rule_id="max_positions",
            name="Maximum Positions Limit",
            description=f"Maximum {self.max_positions} open positions",
            rule_type="position_count",
            threshold=self.max_positions,
            action=RiskAction.BLOCK,
            priority=9
        ))
        
        # Trade frequency rule
        self.add_risk_rule(RiskRule(
            rule_id="trade_frequency_hour",
            name="Hourly Trade Frequency",
            description=f"Maximum {self.max_trades_per_hour} trades per hour",
            rule_type="trade_frequency",
            threshold=self.max_trades_per_hour,
            action=RiskAction.BLOCK,
            priority=8
        ))
        
        # Position size rule
        self.add_risk_rule(RiskRule(
            rule_id="position_size",
            name="Position Size Limit",
            description=f"Maximum {self.max_position_size*100}% position size",
            rule_type="position_size",
            threshold=self.max_position_size,
            action=RiskAction.REDUCE,
            priority=7
        ))
        
        # Daily loss rule
        self.add_risk_rule(RiskRule(
            rule_id="daily_loss",
            name="Daily Loss Limit",
            description=f"Maximum {self.max_daily_loss_pct*100}% daily loss",
            rule_type="daily_loss",
            threshold=self.max_daily_loss_pct,
            action=RiskAction.EMERGENCY_STOP,
            priority=10
        ))
        
        self.logger.info(f"Initialized {len(self._risk_rules)} default risk rules")
    
    def add_risk_rule(self, rule: RiskRule):
        """Add a risk rule"""
        self._risk_rules[rule.rule_id] = rule
        self.logger.info(f"Added risk rule: {rule.name}")
    
    def remove_risk_rule(self, rule_id: str) -> bool:
        """Remove a risk rule"""
        if rule_id in self._risk_rules:
            del self._risk_rules[rule_id]
            self.logger.info(f"Removed risk rule: {rule_id}")
            return True
        return False
    
    def enable_rule(self, rule_id: str) -> bool:
        """Enable a risk rule"""
        if rule_id in self._risk_rules:
            self._risk_rules[rule_id].enabled = True
            return True
        return False
    
    def disable_rule(self, rule_id: str) -> bool:
        """Disable a risk rule"""
        if rule_id in self._risk_rules:
            self._risk_rules[rule_id].enabled = False
            return True
        return False
    
    async def validate_trade(self, request: TradeValidationRequest) -> TradeValidationResult:
        """Validate a trade request against all risk rules"""
        if self._emergency_stop:
            return TradeValidationResult(
                is_valid=False,
                action=RiskAction.EMERGENCY_STOP,
                reason=f"Emergency stop active: {self._emergency_reason}"
            )
        
        violations = []
        risk_score = 0.0
        final_action = RiskAction.ALLOW
        adjusted_amount = request.amount
        
        try:
            # Update risk metrics before validation
            await self._update_risk_metrics()
            
            # Check each enabled rule
            for rule in self._risk_rules.values():
                if not rule.enabled:
                    continue
                
                violation = await self._check_rule(rule, request)
                if violation:
                    violations.append(violation)
                    risk_score += violation.violation_percentage
                    
                    # Update final action based on rule priority
                    if (rule.action.value == RiskAction.EMERGENCY_STOP.value or
                        (rule.action.value == RiskAction.BLOCK.value and final_action != RiskAction.EMERGENCY_STOP) or
                        (rule.action.value == RiskAction.REDUCE.value and final_action == RiskAction.ALLOW)):
                        final_action = rule.action
                        
                        # Calculate adjusted amount for REDUCE action
                        if rule.action == RiskAction.REDUCE:
                            adjusted_amount = await self._calculate_reduced_amount(rule, request)
            
            # Determine if trade is valid
            is_valid = final_action in [RiskAction.ALLOW, RiskAction.REDUCE]
            
            # Handle emergency stop
            if final_action == RiskAction.EMERGENCY_STOP:
                await self._trigger_emergency_stop("Risk rule violation")
            
            result = TradeValidationResult(
                is_valid=is_valid,
                action=final_action,
                adjusted_amount=adjusted_amount if final_action == RiskAction.REDUCE else None,
                violations=violations,
                risk_score=min(risk_score, 100.0),  # Cap at 100%
                reason=self._build_validation_reason(violations, final_action)
            )
            
            self.logger.info(
                f"Trade validation: {request.symbol} {request.side} {request.amount} - "
                f"Result: {final_action.value}, Risk Score: {risk_score:.1f}%"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error during trade validation: {e}")
            return TradeValidationResult(
                is_valid=False,
                action=RiskAction.BLOCK,
                reason=f"Validation error: {str(e)}"
            )
    
    async def _check_rule(self, rule: RiskRule, request: TradeValidationRequest) -> Optional[RiskViolation]:
        """Check a specific rule against trade request"""
        try:
            current_value = 0.0
            
            if rule.rule_type == "balance":
                # Check balance allocation
                trade_value = request.amount * request.price
                current_value = (self._risk_metrics.allocated_balance + trade_value) / self._risk_metrics.total_balance
                
            elif rule.rule_type == "position_count":
                # Check number of positions
                current_value = len(self._current_positions)
                if request.side == "buy":
                    current_value += 1  # Would add new position
                    
            elif rule.rule_type == "position_size":
                # Check position size as percentage of portfolio
                trade_value = request.amount * request.price
                current_value = trade_value / self._risk_metrics.total_balance
                
            elif rule.rule_type == "trade_frequency":
                # Check trades in last hour
                current_value = self._count_recent_trades(hours=1)
                
            elif rule.rule_type == "daily_loss":
                # Check daily P&L
                daily_pnl = self._calculate_daily_pnl()
                current_value = abs(daily_pnl) / self._risk_metrics.total_balance if daily_pnl < 0 else 0
                
            # Check if threshold is exceeded
            if current_value > rule.threshold:
                violation_percentage = ((current_value - rule.threshold) / rule.threshold) * 100
                
                violation = RiskViolation(
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    current_value=current_value,
                    threshold=rule.threshold,
                    violation_percentage=violation_percentage,
                    action_taken=rule.action,
                    metadata={
                        "trade_request": {
                            "symbol": request.symbol,
                            "side": request.side,
                            "amount": request.amount,
                            "price": request.price
                        }
                    }
                )
                
                self._violation_history.append(violation)
                return violation
                
        except Exception as e:
            self.logger.error(f"Error checking rule {rule.rule_id}: {e}")
        
        return None
    
    async def _calculate_reduced_amount(self, rule: RiskRule, request: TradeValidationRequest) -> float:
        """Calculate reduced trade amount to comply with risk rule"""
        try:
            if rule.rule_type == "position_size":
                # Reduce amount to stay within position size limit
                max_trade_value = self._risk_metrics.total_balance * rule.threshold
                max_amount = max_trade_value / request.price
                return min(request.amount, max_amount)
                
            elif rule.rule_type == "balance":
                # Reduce amount to stay within balance allocation
                available_allocation = (self._risk_metrics.total_balance * rule.threshold) - self._risk_metrics.allocated_balance
                max_amount = available_allocation / request.price
                return min(request.amount, max_amount)
                
        except Exception as e:
            self.logger.error(f"Error calculating reduced amount: {e}")
        
        # Default to 50% reduction if calculation fails
        return request.amount * 0.5
    
    def _build_validation_reason(self, violations: List[RiskViolation], action: RiskAction) -> str:
        """Build human-readable validation reason"""
        if not violations:
            return "Trade approved - no risk violations"
        
        if action == RiskAction.EMERGENCY_STOP:
            return "Emergency stop triggered due to critical risk violation"
        elif action == RiskAction.BLOCK:
            violation_names = [v.rule_name for v in violations]
            return f"Trade blocked due to violations: {', '.join(violation_names)}"
        elif action == RiskAction.REDUCE:
            return "Trade amount reduced to comply with risk limits"
        else:
            return "Trade approved with warnings"
    
    async def _update_risk_metrics(self):
        """Update current risk metrics"""
        try:
            # This would integrate with account manager to get real balances
            # For now, using placeholder values
            self._risk_metrics.total_balance = 10000.0  # Would come from account manager
            self._risk_metrics.allocated_balance = sum(
                pos.market_value for pos in self._current_positions.values()
            )
            self._risk_metrics.available_balance = (
                self._risk_metrics.total_balance - self._risk_metrics.allocated_balance
            )
            self._risk_metrics.allocation_percentage = (
                self._risk_metrics.allocated_balance / self._risk_metrics.total_balance
                if self._risk_metrics.total_balance > 0 else 0
            )
            self._risk_metrics.total_positions = len(self._current_positions)
            self._risk_metrics.daily_trades = self._count_recent_trades(hours=24)
            self._risk_metrics.hourly_trades = self._count_recent_trades(hours=1)
            self._risk_metrics.last_updated = datetime.utcnow()
            
        except Exception as e:
            self.logger.error(f"Error updating risk metrics: {e}")
    
    def _count_recent_trades(self, hours: int) -> int:
        """Count trades in the last N hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        count = 0
        for trade in self._trade_history:
            trade_time = datetime.fromisoformat(trade.get('timestamp', ''))
            if trade_time > cutoff_time:
                count += 1
        
        return count
    
    def _calculate_daily_pnl(self) -> float:
        """Calculate daily P&L"""
        # This would calculate based on realized and unrealized P&L
        # Placeholder implementation
        return 0.0
    
    # Emergency controls
    async def trigger_emergency_stop(self, reason: str = "Manual trigger"):
        """Trigger emergency stop"""
        await self._trigger_emergency_stop(reason)
    
    async def _trigger_emergency_stop(self, reason: str):
        """Internal emergency stop trigger"""
        self._emergency_stop = True
        self._emergency_reason = reason
        
        self.logger.critical(f"EMERGENCY STOP TRIGGERED: {reason}")
        
        # Here we would:
        # 1. Cancel all pending orders
        # 2. Close all positions (if configured)
        # 3. Send emergency notifications
        # 4. Log the emergency event
    
    def clear_emergency_stop(self, reason: str = "Manual clear"):
        """Clear emergency stop"""
        self._emergency_stop = False
        self._emergency_reason = ""
        self.logger.warning(f"Emergency stop cleared: {reason}")
    
    def is_emergency_stop_active(self) -> bool:
        """Check if emergency stop is active"""
        return self._emergency_stop
    
    # Position management
    def update_position(self, symbol: str, position_info: PositionInfo):
        """Update position information"""
        self._current_positions[symbol] = position_info
    
    def remove_position(self, symbol: str):
        """Remove position"""
        if symbol in self._current_positions:
            del self._current_positions[symbol]
    
    def get_positions(self) -> Dict[str, PositionInfo]:
        """Get current positions"""
        return self._current_positions.copy()
    
    # Trade tracking
    def record_trade(self, trade_info: Dict[str, Any]):
        """Record completed trade"""
        trade_info['timestamp'] = datetime.utcnow().isoformat()
        self._trade_history.append(trade_info)
        
        # Keep only recent trades (last 1000)
        if len(self._trade_history) > 1000:
            self._trade_history = self._trade_history[-1000:]
    
    # Status and metrics
    def get_risk_metrics(self) -> RiskMetrics:
        """Get current risk metrics"""
        return self._risk_metrics
    
    def get_risk_rules(self) -> Dict[str, RiskRule]:
        """Get all risk rules"""
        return self._risk_rules.copy()
    
    def get_violation_history(self, limit: int = 100) -> List[RiskViolation]:
        """Get recent risk violations"""
        return self._violation_history[-limit:] if self._violation_history else []
    
    def get_risk_status(self) -> Dict[str, Any]:
        """Get comprehensive risk status"""
        return {
            'emergency_stop': self._emergency_stop,
            'emergency_reason': self._emergency_reason,
            'metrics': self._risk_metrics.__dict__,
            'active_rules': len([r for r in self._risk_rules.values() if r.enabled]),
            'total_rules': len(self._risk_rules),
            'recent_violations': len([v for v in self._violation_history 
                                   if (datetime.utcnow() - v.timestamp).total_seconds() < 3600]),
            'current_positions': len(self._current_positions),
            'last_updated': datetime.utcnow().isoformat()
        }
    
    def is_healthy(self) -> bool:
        """Check if risk manager is healthy"""
        return (
            not self._emergency_stop and
            (datetime.utcnow() - self._risk_metrics.last_updated).total_seconds() < 300 and  # 5 minutes
            len([v for v in self._violation_history 
                if (datetime.utcnow() - v.timestamp).total_seconds() < 300]) < 5  # Less than 5 violations in 5 min
        )
    
    async def cleanup(self):
        """Cleanup risk manager"""
        self._current_positions.clear()
        self._trade_history.clear()
        self._violation_history.clear()
        self.logger.info("Risk manager cleaned up")


# Position Sizer utility class
class PositionSizer:
    """Utility class for calculating position sizes"""
    
    @staticmethod
    def fixed_amount(amount: float) -> float:
        """Fixed amount position sizing"""
        return amount
    
    @staticmethod
    def percentage_of_balance(balance: float, percentage: float) -> float:
        """Position size as percentage of balance"""
        return balance * percentage
    
    @staticmethod
    def risk_based(balance: float, entry_price: float, stop_loss_price: float, 
                   risk_amount: float) -> float:
        """Risk-based position sizing"""
        if stop_loss_price == 0 or entry_price == stop_loss_price:
            return 0
        
        risk_per_share = abs(entry_price - stop_loss_price)
        position_size = risk_amount / risk_per_share
        
        return position_size
    
    @staticmethod
    def kelly_criterion(win_rate: float, avg_win: float, avg_loss: float, 
                       balance: float) -> float:
        """Kelly criterion position sizing"""
        if avg_loss == 0:
            return 0
        
        b = avg_win / avg_loss  # Ratio of win to loss
        p = win_rate  # Probability of win
        q = 1 - p  # Probability of loss
        
        kelly_percentage = (b * p - q) / b
        
        # Apply conservative scaling (typically 25-50% of Kelly)
        kelly_percentage = max(0, min(kelly_percentage * 0.25, 0.1))  # Cap at 10%
        
        return balance * kelly_percentage