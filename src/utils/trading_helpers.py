# src/utils/trading_helpers.py

"""
Trading Helper Functions for PnL calculations and market data processing
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal

from ..database.repositories.trade_repository import TradeRepository
from ..clients.ccxt_client import CCXTClient

logger = logging.getLogger(__name__)

async def calculate_pnl(
    user_id: str, 
    symbol: str, 
    sell_amount: float, 
    sell_price: float
) -> float:
    """
    Calculate PnL for a sell trade using FIFO (First In, First Out) method
    """
    try:
        trade_repo = TradeRepository()
        
        # Get all buy trades for this symbol, ordered by timestamp (FIFO)
        buy_trades = await trade_repo.get_user_trades(
            user_id=user_id,
            symbol=symbol,
            status='filled'
        )
        
        # Filter only buy trades and sort by timestamp
        buy_trades = [t for t in buy_trades if t.side == 'buy']
        buy_trades.sort(key=lambda x: x.timestamp)
        
        remaining_sell_amount = sell_amount
        total_cost_basis = 0.0
        
        # Apply FIFO method
        for buy_trade in buy_trades:
            if remaining_sell_amount <= 0:
                break
                
            available_amount = buy_trade.filled_amount
            
            # Calculate how much to use from this buy trade
            amount_to_use = min(remaining_sell_amount, available_amount)
            
            # Add to cost basis
            total_cost_basis += amount_to_use * buy_trade.price
            
            # Reduce remaining amount
            remaining_sell_amount -= amount_to_use
        
        # Calculate PnL
        total_revenue = sell_amount * sell_price
        pnl = total_revenue - total_cost_basis
        
        logger.info(f"PnL calculation: {symbol} sell {sell_amount} @ {sell_price} = ${pnl:.2f}")
        return pnl
        
    except Exception as e:
        logger.error(f"Error calculating PnL: {str(e)}")
        return 0.0

async def calculate_unrealized_pnl(
    user_id: str, 
    positions: List[Dict[str, Any]], 
    ccxt_client: CCXTClient,
    exchange: str = 'kucoin'
) -> Dict[str, float]:
    """
    Calculate unrealized PnL for open positions
    """
    try:
        unrealized_pnl = {}
        
        for position in positions:
            symbol = position['symbol']
            position_size = position['position_size']
            avg_buy_price = position['avg_buy_price']
            
            try:
                # Get current market price
                ticker = await ccxt_client.get_ticker(symbol, exchange)
                current_price = ticker['last']
                
                # Calculate unrealized PnL
                current_value = position_size * current_price
                cost_basis = position_size * avg_buy_price
                pnl = current_value - cost_basis
                
                unrealized_pnl[symbol] = {
                    'pnl': pnl,
                    'pnl_pct': (pnl / cost_basis * 100) if cost_basis > 0 else 0,
                    'current_price': current_price,
                    'avg_buy_price': avg_buy_price,
                    'position_size': position_size,
                    'current_value': current_value,
                    'cost_basis': cost_basis
                }
                
            except Exception as e:
                logger.error(f"Error calculating unrealized PnL for {symbol}: {str(e)}")
                unrealized_pnl[symbol] = {
                    'pnl': 0,
                    'pnl_pct': 0,
                    'current_price': 0,
                    'avg_buy_price': avg_buy_price,
                    'position_size': position_size,
                    'current_value': 0,
                    'cost_basis': position_size * avg_buy_price
                }
        
        return unrealized_pnl
        
    except Exception as e:
        logger.error(f"Error calculating unrealized PnL: {str(e)}")
        return {}

def format_currency(amount: float, currency: str = 'USD', decimals: int = 2) -> str:
    """Format currency amount for display"""
    try:
        if currency == 'USD':
            return f"${amount:,.{decimals}f}"
        else:
            return f"{amount:,.{decimals}f} {currency}"
    except:
        return f"{amount} {currency}"

def format_percentage(value: float, decimals: int = 2) -> str:
    """Format percentage for display"""
    try:
        return f"{value:+.{decimals}f}%"
    except:
        return f"{value}%"

def calculate_win_rate(winning_trades: int, total_trades: int) -> float:
    """Calculate win rate percentage"""
    if total_trades == 0:
        return 0.0
    return (winning_trades / total_trades) * 100

def calculate_profit_factor(gross_profit: float, gross_loss: float) -> float:
    """Calculate profit factor (gross profit / gross loss)"""
    if gross_loss == 0:
        return float('inf') if gross_profit > 0 else 0
    return gross_profit / abs(gross_loss)

def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.02) -> float:
    """Calculate Sharpe ratio for a series of returns"""
    try:
        if not returns or len(returns) < 2:
            return 0.0
            
        import statistics
        
        avg_return = statistics.mean(returns)
        std_return = statistics.stdev(returns)
        
        if std_return == 0:
            return 0.0
            
        # Annualized Sharpe ratio
        excess_return = avg_return - (risk_free_rate / 252)  # Daily risk-free rate
        sharpe = (excess_return / std_return) * (252 ** 0.5)  # Annualized
        
        return sharpe
        
    except Exception as e:
        logger.error(f"Error calculating Sharpe ratio: {str(e)}")
        return 0.0

def calculate_max_drawdown(portfolio_values: List[float]) -> Tuple[float, int]:
    """Calculate maximum drawdown and duration"""
    try:
        if not portfolio_values or len(portfolio_values) < 2:
            return 0.0, 0
            
        peak = portfolio_values[0]
        max_drawdown = 0.0
        max_duration = 0
        current_duration = 0
        
        for value in portfolio_values:
            if value > peak:
                peak = value
                current_duration = 0
            else:
                current_duration += 1
                drawdown = (peak - value) / peak
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
                    max_duration = current_duration
        
        return max_drawdown * 100, max_duration  # Return as percentage
        
    except Exception as e:
        logger.error(f"Error calculating max drawdown: {str(e)}")
        return 0.0, 0

async def get_portfolio_summary(
    user_id: str,
    ccxt_client: CCXTClient,
    exchange: str = 'kucoin'
) -> Dict[str, Any]:
    """Get comprehensive portfolio summary"""
    try:
        trade_repo = TradeRepository()
        
        # Get open positions
        positions = await trade_repo.get_open_positions(user_id)
        
        # Get performance metrics
        performance = await trade_repo.get_performance_metrics(user_id, days=30)
        
        # Calculate unrealized PnL
        unrealized_pnl = await calculate_unrealized_pnl(user_id, positions, ccxt_client, exchange)
        
        # Get recent trades for portfolio value calculation
        recent_trades = await trade_repo.get_user_trades(user_id, limit=100)
        
        # Calculate portfolio metrics
        total_unrealized_pnl = sum(pos['pnl'] for pos in unrealized_pnl.values())
        total_realized_pnl = performance.get('total_pnl', 0)
        total_pnl = total_realized_pnl + total_unrealized_pnl
        
        # Calculate current portfolio value
        position_values = sum(pos['current_value'] for pos in unrealized_pnl.values())
        
        return {
            'positions': positions,
            'unrealized_pnl': unrealized_pnl,
            'performance': performance,
            'summary': {
                'total_positions': len(positions),
                'total_unrealized_pnl': total_unrealized_pnl,
                'total_realized_pnl': total_realized_pnl,
                'total_pnl': total_pnl,
                'position_values': position_values,
                'win_rate': performance.get('win_rate', 0),
                'total_trades': performance.get('total_trades', 0),
                'avg_trade_size': performance.get('avg_trade_size', 0)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting portfolio summary: {str(e)}")
        raise

def validate_trading_symbol(symbol: str) -> bool:
    """Validate trading symbol format"""
    try:
        # Basic validation for symbol format (e.g., BTC/USDT, ETH/USD)
        if '/' not in symbol:
            return False
            
        base, quote = symbol.split('/')
        
        # Check minimum length
        if len(base) < 2 or len(quote) < 2:
            return False
            
        # Check for valid characters (alphanumeric)
        if not base.isalnum() or not quote.isalnum():
            return False
            
        return True
        
    except:
        return False

def validate_trade_amount(amount: float, min_amount: float = 0.0001) -> bool:
    """Validate trade amount"""
    try:
        return amount > min_amount and amount <= 1000000  # Max 1M
    except:
        return False

def validate_trade_price(price: float, min_price: float = 0.0001) -> bool:
    """Validate trade price"""
    try:
        return price > min_price and price <= 10000000  # Max 10M
    except:
        return False

async def get_market_overview(
    symbols: List[str],
    ccxt_client: CCXTClient,
    exchange: str = 'kucoin'
) -> Dict[str, Any]:
    """Get market overview for multiple symbols"""
    try:
        market_data = {}
        
        for symbol in symbols:
            try:
                ticker = await ccxt_client.get_ticker(symbol, exchange)
                stats_24h = await ccxt_client.get_24h_stats(symbol, exchange)
                
                market_data[symbol] = {
                    'price': ticker['last'],
                    'change_24h': stats_24h.get('change', 0),
                    'change_24h_pct': stats_24h.get('percentage', 0),
                    'volume_24h': stats_24h.get('quoteVolume', 0),
                    'high_24h': stats_24h.get('high', 0),
                    'low_24h': stats_24h.get('low', 0),
                    'timestamp': datetime.utcnow()
                }
                
            except Exception as e:
                logger.error(f"Error getting market data for {symbol}: {str(e)}")
                market_data[symbol] = {
                    'price': 0,
                    'change_24h': 0,
                    'change_24h_pct': 0,
                    'volume_24h': 0,
                    'high_24h': 0,
                    'low_24h': 0,
                    'timestamp': datetime.utcnow(),
                    'error': str(e)
                }
        
        return market_data
        
    except Exception as e:
        logger.error(f"Error getting market overview: {str(e)}")
        return {}

def calculate_risk_metrics(
    balance: float,
    trade_amount: float,
    open_trades: int,
    max_concurrent_trades: int = 10,
    max_balance_usage: float = 0.5
) -> Dict[str, Any]:
    """Calculate risk metrics for a trade"""
    try:
        # Calculate current balance usage
        balance_usage_pct = trade_amount / balance if balance > 0 else 1
        
        # Check if trade exceeds limits
        exceeds_balance_limit = balance_usage_pct > max_balance_usage
        exceeds_trade_limit = open_trades >= max_concurrent_trades
        
        return {
            'balance_usage_pct': balance_usage_pct * 100,
            'max_balance_usage_pct': max_balance_usage * 100,
            'open_trades': open_trades,
            'max_concurrent_trades': max_concurrent_trades,
            'exceeds_balance_limit': exceeds_balance_limit,
            'exceeds_trade_limit': exceeds_trade_limit,
            'risk_level': 'HIGH' if (exceeds_balance_limit or exceeds_trade_limit) else 'MEDIUM' if balance_usage_pct > 0.2 else 'LOW'
        }
        
    except Exception as e:
        logger.error(f"Error calculating risk metrics: {str(e)}")
        return {
            'balance_usage_pct': 0,
            'max_balance_usage_pct': 50,
            'open_trades': 0,
            'max_concurrent_trades': 10,
            'exceeds_balance_limit': False,
            'exceeds_trade_limit': False,
            'risk_level': 'UNKNOWN'
        }
