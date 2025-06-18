# src/database/operations.py

"""
Database Operations and Testing Utilities

This module provides high-level database operations, health checks,
and testing utilities for the trading bot application.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from src.database.connection import db_manager, get_database
from src.database.models import repositories, log_repo
from src.utils.logger import get_logger

logger = get_logger(__name__)

class DatabaseOperations:
    """High-level database operations"""
    
    def __init__(self):
        self.repos = repositories
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive database health check"""
        try:
            # Basic connection test
            db_healthy = await db_manager.health_check()
            
            if not db_healthy:
                return {
                    "status": "unhealthy",
                    "connection": False,
                    "error": "Database connection failed"
                }
            
            # Get database statistics
            db_stats = await db_manager.get_stats()
            
            # Test basic operations
            test_results = await self._test_basic_operations()
            
            # Check collection counts
            collection_counts = await self._get_collection_counts()
            
            # Check for expired cache entries
            cache_stats = await self._get_cache_statistics()
            
            return {
                "status": "healthy",
                "connection": True,
                "database_stats": db_stats,
                "test_results": test_results,
                "collection_counts": collection_counts,
                "cache_stats": cache_stats,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "connection": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def _test_basic_operations(self) -> Dict[str, bool]:
        """Test basic CRUD operations"""
        try:
            # Test log creation (safe operation)
            test_log = await log_repo.log(
                level="info",
                message="Database health check test",
                component="database"
            )
            
            # Test read operation
            retrieved_log = await log_repo.get_by_id(str(test_log.id))
            
            # Test update operation
            updated_log = await log_repo.update(
                str(test_log.id),
                {"message": "Database health check test - updated"}
            )
            
            # Test delete operation
            deleted = await log_repo.delete(str(test_log.id))
            
            return {
                "create": test_log is not None,
                "read": retrieved_log is not None,
                "update": updated_log is not None,
                "delete": deleted
            }
            
        except Exception as e:
            logger.error(f"Basic operations test failed: {e}")
            return {
                "create": False,
                "read": False,
                "update": False,
                "delete": False
            }
    
    async def _get_collection_counts(self) -> Dict[str, int]:
        """Get document counts for all collections"""
        try:
            counts = {}
            
            # User management
            counts["users"] = await self.repos.user.count()
            counts["user_sessions"] = await self.repos.user_session.count()
            
            # Exchange management
            counts["exchanges"] = await self.repos.exchange.count()
            counts["exchange_balances"] = await self.repos.exchange_balance.count()
            
            # Strategy management
            counts["strategies"] = await self.repos.strategy.count()
            counts["strategy_templates"] = await self.repos.strategy_template.count()
            
            # Trade management
            counts["trades"] = await self.repos.trade.count()
            counts["positions"] = await self.repos.position.count()
            
            # Backtesting
            counts["backtests"] = await self.repos.backtest.count()
            
            # System
            counts["configurations"] = await self.repos.config.count()
            counts["logs"] = await self.repos.log.count()
            counts["notifications"] = await self.repos.notification.count()
            
            # Community
            counts["marketplace_strategies"] = await self.repos.marketplace.count()
            counts["strategy_ratings"] = await self.repos.rating.count()
            
            return counts
            
        except Exception as e:
            logger.error(f"Failed to get collection counts: {e}")
            return {}
    
    async def _get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            chart_stats = await self.repos.chart_cache.get_cache_statistics()
            
            # Count expired cache entries
            expired_charts = await self.repos.chart_cache.cleanup_expired()
            expired_api_cache = await self.repos.api_cache.cleanup_expired()
            
            return {
                "chart_cache": chart_stats,
                "expired_cleaned": {
                    "chart_cache": expired_charts,
                    "api_cache": expired_api_cache
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get cache statistics: {e}")
            return {}
    
    async def cleanup_expired_data(self) -> Dict[str, int]:
        """Clean up expired data across all collections"""
        cleanup_results = {}
        
        try:
            # Clean up expired cache entries
            cleanup_results["chart_cache"] = await self.repos.chart_cache.cleanup_expired()
            cleanup_results["api_cache"] = await self.repos.api_cache.cleanup_expired()
            
            # Clean up expired logs
            cleanup_results["logs"] = await self.repos.log.cleanup_expired_logs()
            
            # Clean up expired user sessions
            cleanup_results["user_sessions"] = await self.repos.user_session.cleanup_expired_sessions()
            
            logger.info(f"Cleanup completed: {cleanup_results}")
            return cleanup_results
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return cleanup_results
    
    async def get_user_dashboard_data(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive dashboard data for user"""
        try:
            # User strategies
            strategies = await self.repos.strategy.get_user_strategies(user_id)
            active_strategies = [s for s in strategies if s.is_running]
            
            # User trades (last 30 days)
            trades = await self.repos.trade.get_user_trades(user_id, limit=100)
            recent_trades = [t for t in trades 
                           if t.submitted_at > datetime.now(timezone.utc) - timedelta(days=30)]
            
            # User positions
            positions = await self.repos.position.get_user_positions(user_id)
            
            # User backtests
            backtests = await self.repos.backtest.get_user_backtests(user_id, limit=10)
            
            # User exchanges
            exchanges = await self.repos.exchange.get_user_exchanges(user_id)
            
            # User notifications (unread)
            notifications = await self.repos.notification.get_user_notifications(
                user_id, unread_only=True, limit=20
            )
            
            # Calculate summary statistics
            total_trades = len(trades)
            winning_trades = len([t for t in trades if t.status == "filled" and 
                                getattr(t, 'pnl', 0) > 0])
            
            return {
                "user_id": user_id,
                "strategies": {
                    "total": len(strategies),
                    "active": len(active_strategies),
                    "strategies": [s.dict() for s in strategies[:5]]  # Latest 5
                },
                "trades": {
                    "total": total_trades,
                    "recent": len(recent_trades),
                    "winning": winning_trades,
                    "win_rate": (winning_trades / total_trades * 100) if total_trades > 0 else 0,
                    "latest": [t.to_summary_dict() for t in trades[:10]]
                },
                "positions": {
                    "open": len(positions),
                    "positions": [p.dict() for p in positions]
                },
                "backtests": {
                    "total": len(backtests),
                    "latest": [bt.to_summary_dict() for bt in backtests[:5]]
                },
                "exchanges": {
                    "configured": len(exchanges),
                    "active": len([ex for ex in exchanges if ex.active]),
                    "exchanges": [ex.to_safe_dict() for ex in exchanges]
                },
                "notifications": {
                    "unread": len(notifications),
                    "notifications": [n.dict() for n in notifications]
                },
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get user dashboard data: {e}")
            return {"error": str(e)}
    
    async def get_system_overview(self) -> Dict[str, Any]:
        """Get system-wide overview and statistics"""
        try:
            # Get collection counts
            collection_counts = await self._get_collection_counts()
            
            # Get recent activity
            recent_logs = await self.repos.log.get_logs(hours=24, limit=50)
            recent_trades = await self.repos.trade.get_many(
                filter_dict={}, limit=20, sort=[("submitted_at", -1)]
            )
            
            # Get marketplace stats
            marketplace_stats = await self.repos.marketplace.get_marketplace_statistics()
            
            # Get log statistics
            log_stats = await self.repos.log.get_log_statistics(hours=24)
            
            # Calculate system health metrics
            error_logs = len([log for log in recent_logs if log.level in ["error", "critical"]])
            health_score = max(0, 100 - (error_logs * 10))  # Simple health scoring
            
            return {
                "overview": {
                    "total_users": collection_counts.get("users", 0),
                    "active_strategies": len([]),  # Would need to query active strategies
                    "total_trades": collection_counts.get("trades", 0),
                    "health_score": health_score
                },
                "collection_counts": collection_counts,
                "recent_activity": {
                    "logs": [{"level": log.level, "message": log.message, 
                            "component": log.component, "timestamp": log.created_at} 
                           for log in recent_logs[:10]],
                    "trades": [t.to_summary_dict() for t in recent_trades[:10]]
                },
                "marketplace": marketplace_stats,
                "log_statistics": log_stats,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get system overview: {e}")
            return {"error": str(e)}

class DatabaseTestSuite:
    """Database testing utilities"""
    
    def __init__(self):
        self.repos = repositories
        self.test_results = []
    
    async def run_full_test_suite(self) -> Dict[str, Any]:
        """Run comprehensive database test suite"""
        self.test_results = []
        
        # Test database connection
        await self._test_connection()
        
        # Test user management
        await self._test_user_operations()
        
        # Test strategy management
        await self._test_strategy_operations()
        
        # Test trade management
        await self._test_trade_operations()
        
        # Test caching
        await self._test_cache_operations()
        
        # Test system operations
        await self._test_system_operations()
        
        # Calculate overall results
        passed_tests = len([r for r in self.test_results if r["passed"]])
        total_tests = len(self.test_results)
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        return {
            "overall": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": total_tests - passed_tests,
                "success_rate": success_rate
            },
            "test_results": self.test_results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def _test_connection(self):
        """Test database connection"""
        try:
            healthy = await db_manager.health_check()
            self._add_test_result("Database Connection", healthy, 
                                "Database connection successful" if healthy else "Connection failed")
        except Exception as e:
            self._add_test_result("Database Connection", False, str(e))
    
    async def _test_user_operations(self):
        """Test user management operations"""
        try:
            # Create test user
            test_user = await self.repos.user.create_user(
                username="test_user_db_test",
                email="test@example.com",
                password="test_password"
            )
            
            self._add_test_result("User Creation", test_user is not None, 
                                "User created successfully")
            
            # Test user authentication
            auth_user = await self.repos.user.authenticate("test_user_db_test", "test_password")
            self._add_test_result("User Authentication", auth_user is not None,
                                "User authentication successful")
            
            # Cleanup
            await self.repos.user.delete(str(test_user.id))
            
        except Exception as e:
            self._add_test_result("User Operations", False, str(e))
    
    async def _test_strategy_operations(self):
        """Test strategy management operations"""
        try:
            # Would need a test user first
            # For now, just test strategy template operations
            templates = await self.repos.strategy_template.get_many(limit=1)
            self._add_test_result("Strategy Template Query", True, 
                                "Strategy templates queried successfully")
            
        except Exception as e:
            self._add_test_result("Strategy Operations", False, str(e))
    
    async def _test_trade_operations(self):
        """Test trade management operations"""
        try:
            # Test trade statistics (safe operation)
            trades = await self.repos.trade.get_many(limit=1)
            self._add_test_result("Trade Query", True, "Trade query successful")
            
        except Exception as e:
            self._add_test_result("Trade Operations", False, str(e))
    
    async def _test_cache_operations(self):
        """Test cache operations"""
        try:
            # Test cache statistics
            cache_stats = await self.repos.chart_cache.get_cache_statistics()
            self._add_test_result("Cache Statistics", True, "Cache statistics retrieved")
            
        except Exception as e:
            self._add_test_result("Cache Operations", False, str(e))
    
    async def _test_system_operations(self):
        """Test system operations"""
        try:
            # Test log creation
            test_log = await self.repos.log.log(
                level="info",
                message="Database test log",
                component="database"
            )
            
            self._add_test_result("Log Creation", test_log is not None, "Log created successfully")
            
            # Cleanup
            if test_log:
                await self.repos.log.delete(str(test_log.id))
            
        except Exception as e:
            self._add_test_result("System Operations", False, str(e))
    
    def _add_test_result(self, test_name: str, passed: bool, message: str):
        """Add test result to results list"""
        self.test_results.append({
            "test_name": test_name,
            "passed": passed,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

# Global instances
db_ops = DatabaseOperations()
db_test_suite = DatabaseTestSuite()

# Convenience functions
async def health_check() -> Dict[str, Any]:
    """Quick health check"""
    return await db_ops.health_check()

async def cleanup_expired() -> Dict[str, int]:
    """Quick cleanup of expired data"""
    return await db_ops.cleanup_expired_data()

async def get_user_dashboard(user_id: str) -> Dict[str, Any]:
    """Get user dashboard data"""
    return await db_ops.get_user_dashboard_data(user_id)

async def get_system_overview() -> Dict[str, Any]:
    """Get system overview"""
    return await db_ops.get_system_overview()

async def run_database_tests() -> Dict[str, Any]:
    """Run database test suite"""
    return await db_test_suite.run_full_test_suite()

__all__ = [
    'DatabaseOperations', 'DatabaseTestSuite',
    'db_ops', 'db_test_suite',
    'health_check', 'cleanup_expired', 'get_user_dashboard', 
    'get_system_overview', 'run_database_tests'
]