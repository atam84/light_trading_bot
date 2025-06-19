# src/database/repositories/trade_repository.py

"""
Enhanced Trade Repository for Real Trading Operations
Supports real trade storage, retrieval, and PnL calculations
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from decimal import Decimal
from bson import ObjectId

from ..models.trade import TradeModel
from .base_repository import BaseRepository

logger = logging.getLogger(__name__)

class TradeRepository(BaseRepository):
    """Repository for trade operations with real trading support"""
    
    def __init__(self):
        super().__init__('trades')
    
    async def create_trade(self, trade_data: Dict[str, Any]) -> TradeModel:
        """Create a new trade record"""
        try:
            # Add metadata
            trade_data['created_at'] = datetime.utcnow()
            trade_data['updated_at'] = datetime.utcnow()
            
            # Insert into database
            result = await self.collection.insert_one(trade_data)
            trade_data['_id'] = result.inserted_id
            
            # Return as TradeModel
            return TradeModel(**trade_data)
            
        except Exception as e:
            logger.error(f"Error creating trade: {str(e)}")
            raise
    
    async def get_user_trades(
        self, 
        user_id: str, 
        limit: int = 50, 
        offset: int = 0,
        symbol: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[TradeModel]:
        """Get trades for a specific user with filtering"""
        try:
            # Build query
            query = {'user_id': ObjectId(user_id)}
            
            if symbol:
                query['symbol'] = symbol
            if status:
                query['status'] = status
            if start_date or end_date:
                query['timestamp'] = {}
                if start_date:
                    query['timestamp']['$gte'] = start_date
                if end_date:
                    query['timestamp']['$lte'] = end_date
            
            # Execute query with pagination
            cursor = self.collection.find(query).sort('timestamp', -1).skip(offset).limit(limit)
            trades = await cursor.to_list(length=limit)
            
            return [TradeModel(**trade) for trade in trades]
            
        except Exception as e:
            logger.error(f"Error getting user trades: {str(e)}")
            raise
    
    async def get_open_positions(self, user_id: str, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get current open positions for a user"""
        try:
            # Build aggregation pipeline
            match_stage = {
                'user_id': ObjectId(user_id),
                'status': {'$in': ['filled', 'partially_filled']},
                'mode': 'live'
            }
            
            if symbol:
                match_stage['symbol'] = symbol
            
            pipeline = [
                {'$match': match_stage},
                {
                    '$group': {
                        '_id': '$symbol',
                        'total_bought': {
                            '$sum': {
                                '$cond': [
                                    {'$eq': ['$side', 'buy']},
                                    '$filled_amount',
                                    0
                                ]
                            }
                        },
                        'total_sold': {
                            '$sum': {
                                '$cond': [
                                    {'$eq': ['$side', 'sell']},
                                    '$filled_amount',
                                    0
                                ]
                            }
                        },
                        'avg_buy_price': {
                            '$avg': {
                                '$cond': [
                                    {'$eq': ['$side', 'buy']},
                                    '$price',
                                    None
                                ]
                            }
                        },
                        'trades': {'$push': '$$ROOT'}
                    }
                },
                {
                    '$project': {
                        'symbol': '$_id',
                        'position_size': {'$subtract': ['$total_bought', '$total_sold']},
                        'total_bought': 1,
                        'total_sold': 1,
                        'avg_buy_price': 1,
                        'trades': 1
                    }
                },
                {'$match': {'position_size': {'$gt': 0}}}  # Only open positions
            ]
            
            positions = await self.collection.aggregate(pipeline).to_list(None)
            return positions
            
        except Exception as e:
            logger.error(f"Error getting open positions: {str(e)}")
            raise
    
    async def calculate_pnl_24h(self, user_id: str) -> float:
        """Calculate PnL for the last 24 hours"""
        try:
            start_time = datetime.utcnow() - timedelta(hours=24)
            
            pipeline = [
                {
                    '$match': {
                        'user_id': ObjectId(user_id),
                        'timestamp': {'$gte': start_time},
                        'status': 'filled',
                        'mode': 'live'
                    }
                },
                {
                    '$group': {
                        '_id': None,
                        'total_pnl': {
                            '$sum': {
                                '$cond': [
                                    {'$eq': ['$side', 'sell']},
                                    {'$multiply': ['$filled_amount', '$price']},
                                    {'$multiply': ['$filled_amount', '$price', -1]}
                                ]
                            }
                        }
                    }
                }
            ]
            
            result = await self.collection.aggregate(pipeline).to_list(1)
            return result[0]['total_pnl'] if result else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating 24h PnL: {str(e)}")
            return 0.0
    
    async def calculate_total_pnl(self, user_id: str) -> float:
        """Calculate total PnL for a user"""
        try:
            pipeline = [
                {
                    '$match': {
                        'user_id': ObjectId(user_id),
                        'status': 'filled',
                        'mode': 'live'
                    }
                },
                {
                    '$group': {
                        '_id': None,
                        'total_pnl': {
                            '$sum': {
                                '$cond': [
                                    {'$eq': ['$side', 'sell']},
                                    {'$multiply': ['$filled_amount', '$price']},
                                    {'$multiply': ['$filled_amount', '$price', -1]}
                                ]
                            }
                        }
                    }
                }
            ]
            
            result = await self.collection.aggregate(pipeline).to_list(1)
            return result[0]['total_pnl'] if result else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating total PnL: {str(e)}")
            return 0.0
    
    async def get_performance_metrics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            pipeline = [
                {
                    '$match': {
                        'user_id': ObjectId(user_id),
                        'timestamp': {'$gte': start_date},
                        'status': 'filled',
                        'mode': 'live'
                    }
                },
                {
                    '$group': {
                        '_id': None,
                        'total_trades': {'$sum': 1},
                        'winning_trades': {
                            '$sum': {
                                '$cond': [
                                    {'$gt': ['$pnl', 0]},
                                    1,
                                    0
                                ]
                            }
                        },
                        'total_volume': {'$sum': {'$multiply': ['$filled_amount', '$price']}},
                        'total_fees': {'$sum': '$fee'},
                        'avg_trade_size': {'$avg': {'$multiply': ['$filled_amount', '$price']}},
                        'best_trade': {'$max': '$pnl'},
                        'worst_trade': {'$min': '$pnl'},
                        'total_pnl': {'$sum': '$pnl'}
                    }
                }
            ]
            
            result = await self.collection.aggregate(pipeline).to_list(1)
            
            if result:
                metrics = result[0]
                total_trades = metrics.get('total_trades', 0)
                winning_trades = metrics.get('winning_trades', 0)
                
                return {
                    'total_trades': total_trades,
                    'winning_trades': winning_trades,
                    'losing_trades': total_trades - winning_trades,
                    'win_rate': (winning_trades / total_trades * 100) if total_trades > 0 else 0,
                    'total_volume': metrics.get('total_volume', 0),
                    'total_fees': metrics.get('total_fees', 0),
                    'avg_trade_size': metrics.get('avg_trade_size', 0),
                    'best_trade': metrics.get('best_trade', 0),
                    'worst_trade': metrics.get('worst_trade', 0),
                    'total_pnl': metrics.get('total_pnl', 0),
                    'period_days': days
                }
            else:
                return {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0,
                    'total_volume': 0,
                    'total_fees': 0,
                    'avg_trade_size': 0,
                    'best_trade': 0,
                    'worst_trade': 0,
                    'total_pnl': 0,
                    'period_days': days
                }
                
        except Exception as e:
            logger.error(f"Error getting performance metrics: {str(e)}")
            raise
    
    async def update_by_order_id(self, order_id: str, update_data: Dict[str, Any]) -> bool:
        """Update trade by exchange order ID"""
        try:
            update_data['updated_at'] = datetime.utcnow()
            
            result = await self.collection.update_one(
                {'order_id': order_id},
                {'$set': update_data}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating trade by order ID: {str(e)}")
            return False
    
    async def get_trade_by_order_id(self, order_id: str) -> Optional[TradeModel]:
        """Get trade by exchange order ID"""
        try:
            trade = await self.collection.find_one({'order_id': order_id})
            return TradeModel(**trade) if trade else None
            
        except Exception as e:
            logger.error(f"Error getting trade by order ID: {str(e)}")
            return None
    
    async def get_trading_summary(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive trading summary for dashboard"""
        try:
            # Get today's trades
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Get open positions
            open_positions = await self.get_open_positions(user_id)
            
            # Get recent trades
            recent_trades = await self.get_user_trades(user_id, limit=10)
            
            # Get performance metrics
            performance = await self.get_performance_metrics(user_id, days=30)
            
            # Get today's activity
            today_pipeline = [
                {
                    '$match': {
                        'user_id': ObjectId(user_id),
                        'timestamp': {'$gte': today_start},
                        'status': 'filled'
                    }
                },
                {
                    '$group': {
                        '_id': None,
                        'trades_today': {'$sum': 1},
                        'volume_today': {'$sum': {'$multiply': ['$filled_amount', '$price']}},
                        'pnl_today': {'$sum': '$pnl'}
                    }
                }
            ]
            
            today_result = await self.collection.aggregate(today_pipeline).to_list(1)
            today_stats = today_result[0] if today_result else {
                'trades_today': 0,
                'volume_today': 0,
                'pnl_today': 0
            }
            
            return {
                'open_positions': len(open_positions),
                'recent_trades': [
                    {
                        'id': str(trade.id),
                        'symbol': trade.symbol,
                        'side': trade.side,
                        'amount': trade.amount,
                        'price': trade.price,
                        'timestamp': trade.timestamp,
                        'status': trade.status
                    }
                    for trade in recent_trades
                ],
                'performance': performance,
                'today': today_stats,
                'positions': [
                    {
                        'symbol': pos['symbol'],
                        'size': pos['position_size'],
                        'avg_price': pos['avg_buy_price'],
                        'total_value': pos['position_size'] * pos['avg_buy_price']
                    }
                    for pos in open_positions
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting trading summary: {str(e)}")
            raise

# Create singleton instance
trade_repository = TradeRepository()
