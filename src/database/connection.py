# src/database/connection.py

import os
import asyncio
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from src.utils.logger import get_logger

logger = get_logger(__name__)

class DatabaseManager:
    """MongoDB connection and database management"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
        self.db_name: str = "trading_bot"
        
    async def connect(self, connection_string: Optional[str] = None) -> bool:
        """Connect to MongoDB database"""
        try:
            if not connection_string:
                connection_string = os.getenv(
                    "MONGODB_URL", 
                    "mongodb://localhost:27017/trading_bot"
                )
            
            self.client = AsyncIOMotorClient(
                connection_string,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                maxPoolSize=10,
                minPoolSize=1,
                maxIdleTimeMS=30000
            )
            
            # Test connection
            await self.client.admin.command('ping')
            
            # Extract database name from connection string or use default
            if '/' in connection_string:
                self.db_name = connection_string.split('/')[-1].split('?')[0]
            
            self.database = self.client[self.db_name]
            
            logger.info(f"Connected to MongoDB database: {self.db_name}")
            
            # Create indexes
            await self._create_indexes()
            
            return True
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to database: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    async def _create_indexes(self):
        """Create database indexes for performance optimization"""
        try:
            # Users collection indexes
            await self.database.users.create_index("username", unique=True)
            await self.database.users.create_index("email", unique=True)
            await self.database.users.create_index("created_at")
            
            # Exchanges collection indexes
            await self.database.exchanges.create_index([("user_id", 1), ("exchange_name", 1)])
            await self.database.exchanges.create_index("active")
            
            # Strategies collection indexes
            await self.database.strategies.create_index([("user_id", 1), ("name", 1)])
            await self.database.strategies.create_index("active")
            await self.database.strategies.create_index("public")
            await self.database.strategies.create_index("created_at")
            
            # Trades collection indexes
            await self.database.trades.create_index([("user_id", 1), ("timestamp", -1)])
            await self.database.trades.create_index([("symbol", 1), ("timestamp", -1)])
            await self.database.trades.create_index("status")
            await self.database.trades.create_index("mode")
            await self.database.trades.create_index("order_id")
            
            # Backtests collection indexes
            await self.database.backtests.create_index([("user_id", 1), ("created_at", -1)])
            await self.database.backtests.create_index([("strategy_id", 1), ("created_at", -1)])
            await self.database.backtests.create_index("symbol")
            
            # Chart cache with TTL index
            await self.database.chart_cache.create_index("expires_at", expireAfterSeconds=0)
            await self.database.chart_cache.create_index([("symbol", 1), ("interval", 1), ("exchange", 1)], unique=True)
            
            # Logs collection indexes
            await self.database.logs.create_index([("timestamp", -1)])
            await self.database.logs.create_index("level")
            await self.database.logs.create_index("component")
            await self.database.logs.create_index("user_id")
            
            # Strategy marketplace indexes
            await self.database.strategy_marketplace.create_index("rating")
            await self.database.strategy_marketplace.create_index("downloads")
            await self.database.strategy_marketplace.create_index("category")
            await self.database.strategy_marketplace.create_index("created_at")
            await self.database.strategy_marketplace.create_index("tags")
            
            # Notifications indexes
            await self.database.notifications.create_index([("user_id", 1), ("sent_at", -1)])
            await self.database.notifications.create_index("read")
            await self.database.notifications.create_index("type")
            
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"Error creating database indexes: {e}")
    
    async def health_check(self) -> bool:
        """Check database connection health"""
        try:
            if not self.client:
                return False
            await self.client.admin.command('ping')
            return True
        except Exception:
            return False
    
    async def get_stats(self) -> dict:
        """Get database statistics"""
        try:
            if not self.database:
                return {}
            
            stats = await self.database.command("dbstats")
            collections = await self.database.list_collection_names()
            
            return {
                "database_name": self.db_name,
                "collections_count": len(collections),
                "data_size": stats.get("dataSize", 0),
                "storage_size": stats.get("storageSize", 0),
                "indexes": stats.get("indexes", 0),
                "collections": collections
            }
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}

# Global database manager instance
db_manager = DatabaseManager()

async def get_database() -> AsyncIOMotorDatabase:
    """Get database instance"""
    if not db_manager.database:
        await db_manager.connect()
    return db_manager.database

async def init_database() -> bool:
    """Initialize database connection"""
    return await db_manager.connect()

async def close_database():
    """Close database connection"""
    await db_manager.disconnect()