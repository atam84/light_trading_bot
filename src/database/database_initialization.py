# src/database/init_database.py

"""
Database Initialization Script
Sets up MongoDB collections, indexes, and demo data for trading bot
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.database.connection import DatabaseConnection
from src.database.models.user import UserModel
from src.database.models.trade import TradeModel
from src.database.models.strategy import StrategyModel
from src.database.repositories.user_repository import UserRepository
from src.database.repositories.exchange_repository import ExchangeRepository
from src.database.repositories.strategy_repository import StrategyRepository
from src.database.repositories.trade_repository import TradeRepository
from src.interfaces.web.auth import get_password_hash

logger = logging.getLogger(__name__)

class DatabaseInitializer:
    """Initialize database with collections, indexes, and demo data"""
    
    def __init__(self):
        self.db = None
        
    async def initialize_database(self, create_demo_data: bool = True):
        """Initialize complete database setup"""
        try:
            logger.info("Starting database initialization...")
            
            # Connect to database
            self.db = DatabaseConnection()
            await self.db.connect()
            
            # Create collections and indexes
            await self.create_collections()
            await self.create_indexes()
            
            # Create demo data if requested
            if create_demo_data:
                await self.create_demo_data()
            
            logger.info("Database initialization completed successfully!")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            raise
    
    async def create_collections(self):
        """Create all required collections"""
        collections = [
            'users',
            'exchanges', 
            'strategies',
            'trades',
            'backtests',
            'chart_cache',
            'configurations',
            'logs',
            'strategy_marketplace',
            'strategy_ratings',
            'notifications',
            'telegram_configs'
        ]
        
        logger.info("Creating collections...")
        
        for collection_name in collections:
            try:
                await self.db.database.create_collection(collection_name)
                logger.info(f"Created collection: {collection_name}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.info(f"Collection already exists: {collection_name}")
                else:
                    logger.error(f"Error creating collection {collection_name}: {str(e)}")
    
    async def create_indexes(self):
        """Create database indexes for performance"""
        logger.info("Creating database indexes...")
        
        try:
            # Users collection indexes
            users = self.db.database.users
            await users.create_index("username", unique=True)
            await users.create_index("email", unique=True)
            await users.create_index("created_at")
            
            # Exchanges collection indexes
            exchanges = self.db.database.exchanges
            await exchanges.create_index([("user_id", 1), ("exchange_name", 1)], unique=True)
            await exchanges.create_index("user_id")
            
            # Strategies collection indexes
            strategies = self.db.database.strategies
            await strategies.create_index("user_id")
            await strategies.create_index("active")
            await strategies.create_index([("user_id", 1), ("active", 1)])
            await strategies.create_index("public")
            
            # Trades collection indexes
            trades = self.db.database.trades
            await trades.create_index("user_id")
            await trades.create_index([("user_id", 1), ("symbol", 1)])
            await trades.create_index([("user_id", 1), ("timestamp", -1)])
            await trades.create_index("timestamp")
            await trades.create_index("status")
            await trades.create_index("mode")
            await trades.create_index("order_id")
            
            # Backtests collection indexes
            backtests = self.db.database.backtests
            await backtests.create_index("user_id")
            await backtests.create_index([("user_id", 1), ("strategy_id", 1)])
            await backtests.create_index("created_at")
            
            # Chart cache collection indexes with TTL
            chart_cache = self.db.database.chart_cache
            await chart_cache.create_index([("symbol", 1), ("interval", 1), ("exchange", 1)], unique=True)
            await chart_cache.create_index("expires_at", expireAfterSeconds=0)  # TTL index
            
            # Configurations collection indexes
            configurations = self.db.database.configurations
            await configurations.create_index([("user_id", 1), ("category", 1), ("key", 1)], unique=True)
            
            # Logs collection indexes with TTL
            logs = self.db.database.logs
            await logs.create_index("timestamp")
            await logs.create_index("level")
            await logs.create_index("user_id")
            await logs.create_index("timestamp", expireAfterSeconds=2592000)  # 30 days TTL
            
            # Strategy marketplace indexes
            marketplace = self.db.database.strategy_marketplace
            await marketplace.create_index("author_id")
            await marketplace.create_index("category")
            await marketplace.create_index("rating")
            await marketplace.create_index("downloads")
            await marketplace.create_index("created_at")
            
            # Notifications indexes
            notifications = self.db.database.notifications
            await notifications.create_index([("user_id", 1), ("timestamp", -1)])
            await notifications.create_index("sent_at")
            
            logger.info("Database indexes created successfully!")
            
        except Exception as e:
            logger.error(f"Error creating indexes: {str(e)}")
            raise
    
    async def create_demo_data(self):
        """Create demo user and sample data"""
        logger.info("Creating demo data...")
        
        try:
            # Create demo user
            demo_user = await self.create_demo_user()
            
            # Create demo exchange configuration
            await self.create_demo_exchange(demo_user['_id'])
            
            # Create demo strategies
            strategy_ids = await self.create_demo_strategies(demo_user['_id'])
            
            # Create demo trades
            await self.create_demo_trades(demo_user['_id'], strategy_ids[0] if strategy_ids else None)
            
            logger.info("Demo data created successfully!")
            
        except Exception as e:
            logger.error(f"Error creating demo data: {str(e)}")
            raise
    
    async def create_demo_user(self) -> Dict[str, Any]:
        """Create demo user account"""
        user_repo = UserRepository()
        
        # Check if demo user already exists
        existing_user = await user_repo.get_by_username("demo")
        if existing_user:
            logger.info("Demo user already exists")
            return {"_id": existing_user.id}
        
        # Create demo user
        demo_user_data = {
            "username": "demo",
            "email": "demo@tradingbot.com",
            "password_hash": get_password_hash("demo123"),
            "created_at": datetime.utcnow(),
            "last_login": None,
            "settings": {
                "timezone": "UTC",
                "currency": "USD", 
                "theme": "dark"
            },
            "social_auth": {}
        }
        
        demo_user = await user_repo.create(demo_user_data)
        logger.info(f"Created demo user with ID: {demo_user.id}")
        
        return {"_id": demo_user.id}
    
    async def create_demo_exchange(self, user_id: str):
        """Create demo exchange configuration"""
        exchange_repo = ExchangeRepository()
        
        # Check if demo exchange already exists
        existing_exchange = await exchange_repo.get_by_user_and_name(str(user_id), "kucoin")
        if existing_exchange:
            logger.info("Demo exchange configuration already exists")
            return
        
        # Create demo exchange (with fake API keys for demo)
        exchange_data = {
            "user_id": user_id,
            "exchange_name": "kucoin",
            "display_name": "KuCoin Demo",
            "api_key_encrypted": "demo_api_key_encrypted",
            "api_secret_encrypted": "demo_api_secret_encrypted", 
            "passphrase_encrypted": "demo_passphrase_encrypted",
            "testnet": True,
            "active": True,
            "created_at": datetime.utcnow()
        }
        
        await exchange_repo.create(exchange_data)
        logger.info("Created demo exchange configuration")
    
    async def create_demo_strategies(self, user_id: str) -> list:
        """Create demo trading strategies"""
        strategy_repo = StrategyRepository()
        strategy_ids = []
        
        # Demo strategies
        strategies = [
            {
                "name": "RSI Mean Reversion",
                "description": "Buy when RSI < 30, sell when RSI > 70",
                "strategy_type": "indicator_based",
                "config": {
                    "timeframe": "1h",
                    "indicators_chain": [
                        {
                            "type": "entry",
                            "indicator": "RSI",
                            "params": {"period": 14, "oversold": 30},
                            "condition": "below_threshold"
                        },
                        {
                            "type": "exit",
                            "indicator": "RSI", 
                            "params": {"period": 14, "overbought": 70},
                            "condition": "above_threshold"
                        }
                    ],
                    "entry_conditions": {"rsi_below": 30},
                    "exit_conditions": {"rsi_above": 70},
                    "risk_management": {
                        "stop_loss": 5,
                        "take_profit": 10,
                        "position_size": 100
                    }
                },
                "active": True,
                "public": False
            },
            {
                "name": "Simple Grid Trading",
                "description": "Grid trading strategy with 5% spacing",
                "strategy_type": "grid",
                "config": {
                    "grid_levels": 10,
                    "grid_spacing": 5,
                    "base_amount": 100,
                    "upper_limit": 50000,
                    "lower_limit": 40000,
                    "timeframe": "1h"
                },
                "active": False,
                "public": False
            },
            {
                "name": "MA Crossover",
                "description": "Moving average crossover strategy",
                "strategy_type": "indicator_based",
                "config": {
                    "timeframe": "4h",
                    "indicators_chain": [
                        {
                            "type": "entry",
                            "indicator": "MA_Cross",
                            "params": {"fast": 12, "slow": 26},
                            "condition": "golden_cross"
                        },
                        {
                            "type": "exit",
                            "indicator": "MA_Cross",
                            "params": {"fast": 12, "slow": 26},
                            "condition": "death_cross"
                        }
                    ],
                    "risk_management": {
                        "stop_loss": 3,
                        "take_profit": 8,
                        "position_size": 200
                    }
                },
                "active": False,
                "public": True
            }
        ]
        
        for strategy_data in strategies:
            # Check if strategy already exists
            existing_strategies = await strategy_repo.get_user_strategies(str(user_id))
            if any(s.name == strategy_data["name"] for s in existing_strategies):
                logger.info(f"Demo strategy '{strategy_data['name']}' already exists")
                continue
            
            strategy_data.update({
                "user_id": user_id,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })
            
            strategy = await strategy_repo.create(strategy_data)
            strategy_ids.append(strategy.id)
            logger.info(f"Created demo strategy: {strategy_data['name']}")
        
        return strategy_ids
    
    async def create_demo_trades(self, user_id: str, strategy_id: str = None):
        """Create demo trade history"""
        trade_repo = TradeRepository()
        
        # Check if demo trades already exist
        existing_trades = await trade_repo.get_user_trades(str(user_id), limit=1)
        if existing_trades:
            logger.info("Demo trades already exist")
            return
        
        # Create sample trades
        base_time = datetime.utcnow() - timedelta(days=7)
        
        demo_trades = [
            {
                "symbol": "BTC/USDT",
                "side": "buy",
                "type": "market",
                "amount": 0.001,
                "price": 42000,
                "filled_amount": 0.001,
                "status": "filled",
                "exchange": "kucoin",
                "mode": "paper",
                "fee": 0.21,
                "pnl": 0,
                "timestamp": base_time
            },
            {
                "symbol": "BTC/USDT", 
                "side": "sell",
                "type": "limit",
                "amount": 0.001,
                "price": 43500,
                "filled_amount": 0.001,
                "status": "filled",
                "exchange": "kucoin",
                "mode": "paper",
                "fee": 0.22,
                "pnl": 1.28,  # $1500 profit - fees
                "timestamp": base_time + timedelta(hours=6)
            },
            {
                "symbol": "ETH/USDT",
                "side": "buy", 
                "type": "market",
                "amount": 0.1,
                "price": 2500,
                "filled_amount": 0.1,
                "status": "filled",
                "exchange": "kucoin",
                "mode": "paper",
                "fee": 0.125,
                "pnl": 0,
                "timestamp": base_time + timedelta(days=1)
            },
            {
                "symbol": "ETH/USDT",
                "side": "sell",
                "type": "market", 
                "amount": 0.1,
                "price": 2600,
                "filled_amount": 0.1,
                "status": "filled",
                "exchange": "kucoin",
                "mode": "paper",
                "fee": 0.13,
                "pnl": 9.75,  # $10 profit - fees
                "timestamp": base_time + timedelta(days=2)
            }
        ]
        
        for trade_data in demo_trades:
            trade_data.update({
                "user_id": user_id,
                "strategy_id": strategy_id,
                "order_id": f"demo_{trade_data['symbol'].replace('/', '')}_{int(trade_data['timestamp'].timestamp())}",
                "created_at": trade_data["timestamp"],
                "updated_at": trade_data["timestamp"]
            })
            
            await trade_repo.create_trade(trade_data)
        
        logger.info(f"Created {len(demo_trades)} demo trades")

async def main():
    """Main initialization function"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🚀 Initializing Trading Bot Database...")
    print("=" * 50)
    
    try:
        initializer = DatabaseInitializer()
        await initializer.initialize_database(create_demo_data=True)
        
        print("=" * 50)
        print("✅ Database initialization completed successfully!")
        print("\n📊 Demo Account Created:")
        print("   Username: demo")
        print("   Password: demo123")
        print("\n🔗 You can now start the web application and login!")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
