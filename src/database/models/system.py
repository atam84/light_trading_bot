# src/database/models/system.py

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Union
from pydantic import Field, validator
from enum import Enum
from src.database.models.base import (
    BaseDBModel, BaseRepository, TimestampMixin, 
    UserOwnershipMixin, PyObjectId, EncryptionMixin
)

class LogLevel(str, Enum):
    """Log levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class ComponentType(str, Enum):
    """System components"""
    TRADING_ENGINE = "trading_engine"
    STRATEGY_MANAGER = "strategy_manager"
    RISK_MANAGER = "risk_manager"
    API_CLIENT = "api_client"
    WEB_UI = "web_ui"
    TELEGRAM_BOT = "telegram_bot"
    CLI = "cli"
    DATABASE = "database"
    CACHE = "cache"
    BACKTEST_ENGINE = "backtest_engine"
    NOTIFICATION_SYSTEM = "notification_system"
    SYSTEM = "system"

class NotificationType(str, Enum):
    """Notification types"""
    TRADE_SIGNAL = "trade_signal"
    TRADE_EXECUTION = "trade_execution"
    BACKTEST_RESULT = "backtest_result"
    SYSTEM_ALERT = "system_alert"
    BALANCE_UPDATE = "balance_update"
    STRATEGY_STATUS = "strategy_status"
    RISK_ALERT = "risk_alert"
    MARKET_ALERT = "market_alert"
    PERFORMANCE_REPORT = "performance_report"

class NotificationChannel(str, Enum):
    """Notification channels"""
    TELEGRAM = "telegram"
    EMAIL = "email"
    WEB = "web"
    WEBHOOK = "webhook"
    SMS = "sms"

class ConfigurationCategory(str, Enum):
    """Configuration categories"""
    TRADING = "trading"
    UI = "ui"
    NOTIFICATIONS = "notifications"
    SECURITY = "security"
    SYSTEM = "system"
    API = "api"
    CACHE = "cache"

class SystemConfiguration(BaseDBModel, TimestampMixin, UserOwnershipMixin):
    """System configuration storage"""
    
    category: ConfigurationCategory = Field(..., description="Configuration category")
    key: str = Field(..., description="Configuration key")
    value: Union[str, int, float, bool, Dict[str, Any], List[Any]] = Field(..., description="Configuration value")
    
    # Metadata
    description: Optional[str] = Field(None, description="Configuration description")
    is_encrypted: bool = Field(default=False, description="Whether value is encrypted")
    is_global: bool = Field(default=False, description="Global configuration (not user-specific)")
    environment: str = Field(default="production", description="Environment (production, development, test)")
    
    # Validation
    data_type: str = Field(..., description="Expected data type")
    validation_rules: Dict[str, Any] = Field(default={}, description="Validation rules")
    
    @property
    def collection_name(self) -> str:
        return "configurations"
    
    @validator('key')
    def validate_key(cls, v):
        # Ensure key is lowercase with underscores
        return v.lower().replace(' ', '_').replace('-', '_')
    
    def get_value(self, decrypt: bool = True) -> Any:
        """Get configuration value, optionally decrypting"""
        if self.is_encrypted and decrypt and isinstance(self.value, str):
            return EncryptionMixin.decrypt_value(self.value)
        return self.value
    
    def set_value(self, value: Any, encrypt: bool = None):
        """Set configuration value, optionally encrypting"""
        if encrypt is None:
            encrypt = self.is_encrypted
        
        if encrypt and isinstance(value, str):
            self.value = EncryptionMixin.encrypt_value(value)
            self.is_encrypted = True
        else:
            self.value = value
            self.is_encrypted = False
    
    @classmethod
    def create_config_key(cls, category: str, key: str, user_id: str = None) -> str:
        """Create unique configuration key"""
        if user_id:
            return f"{category}:{key}:{user_id}"
        return f"{category}:{key}"

class SystemLog(BaseDBModel, TimestampMixin):
    """System logging model"""
    
    level: LogLevel = Field(..., description="Log level")
    message: str = Field(..., description="Log message")
    component: ComponentType = Field(..., description="System component")
    
    # Optional user context
    user_id: Optional[PyObjectId] = Field(None, description="User ID if applicable")
    
    # Request context
    request_id: Optional[str] = Field(None, description="Request ID for tracing")
    session_id: Optional[str] = Field(None, description="Session ID")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default={}, description="Additional log metadata")
    stack_trace: Optional[str] = Field(None, description="Stack trace for errors")
    
    # Performance metrics
    execution_time: Optional[float] = Field(None, description="Execution time in seconds")
    memory_usage: Optional[int] = Field(None, description="Memory usage in bytes")
    
    # TTL for log retention
    expires_at: Optional[datetime] = Field(None, description="Log expiration time")
    
    @property
    def collection_name(self) -> str:
        return "logs"
    
    @classmethod
    def create_log(cls, level: LogLevel, message: str, component: ComponentType,
                   user_id: str = None, retention_days: int = 30, **kwargs) -> 'SystemLog':
        """Create a new log entry"""
        expires_at = datetime.now(timezone.utc) + timedelta(days=retention_days)
        
        return cls(
            level=level,
            message=message,
            component=component,
            user_id=PyObjectId(user_id) if user_id else None,
            expires_at=expires_at,
            **kwargs
        )

class Notification(BaseDBModel, TimestampMixin, UserOwnershipMixin):
    """User notifications"""
    
    type: NotificationType = Field(..., description="Notification type")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    
    # Delivery channels
    channels: List[NotificationChannel] = Field(..., description="Delivery channels")
    
    # Status tracking
    sent_at: Optional[datetime] = None
    read: bool = Field(default=False, description="Whether notification was read")
    read_at: Optional[datetime] = None
    
    # Delivery status per channel
    delivery_status: Dict[str, Dict[str, Any]] = Field(default={}, description="Delivery status per channel")
    
    # Priority and urgency
    priority: str = Field(default="normal", description="Priority: low, normal, high, urgent")
    urgent: bool = Field(default=False, description="Urgent notification")
    
    # Related objects
    related_object_type: Optional[str] = Field(None, description="Related object type (trade, strategy, etc.)")
    related_object_id: Optional[PyObjectId] = Field(None, description="Related object ID")
    
    # Rich content
    metadata: Dict[str, Any] = Field(default={}, description="Additional notification data")
    action_buttons: List[Dict[str, str]] = Field(default=[], description="Action buttons for interactive notifications")
    
    # Expiration
    expires_at: Optional[datetime] = Field(None, description="Notification expiration")
    
    @property
    def collection_name(self) -> str:
        return "notifications"
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.read = True
        self.read_at = datetime.now(timezone.utc)
    
    def mark_as_sent(self, channel: str = None):
        """Mark notification as sent"""
        self.sent_at = datetime.now(timezone.utc)
        
        if channel:
            if channel not in self.delivery_status:
                self.delivery_status[channel] = {}
            self.delivery_status[channel].update({
                "status": "sent",
                "sent_at": self.sent_at.isoformat()
            })
    
    def mark_delivery_failed(self, channel: str, error: str):
        """Mark delivery as failed for specific channel"""
        if channel not in self.delivery_status:
            self.delivery_status[channel] = {}
        
        self.delivery_status[channel].update({
            "status": "failed",
            "error": error,
            "failed_at": datetime.now(timezone.utc).isoformat()
        })
    
    def is_expired(self) -> bool:
        """Check if notification is expired"""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at

class TelegramConfig(BaseDBModel, TimestampMixin, UserOwnershipMixin, EncryptionMixin):
    """Telegram bot configuration"""
    
    config_name: str = Field(..., description="Configuration name")
    bot_token_encrypted: str = Field(..., description="Encrypted bot token")
    
    # Channels and users
    channels: List[str] = Field(default=[], description="Channel IDs")
    users: List[str] = Field(default=[], description="Authorized user IDs")
    chat_rooms: List[str] = Field(default=[], description="Chat room IDs")
    
    # Permissions
    permissions: List[str] = Field(default=[], description="Bot permissions")
    notification_types: List[NotificationType] = Field(default=[], description="Enabled notification types")
    
    # Settings
    active: bool = Field(default=True, description="Configuration active status")
    rate_limit_commands: int = Field(default=10, description="Commands per minute limit")
    rate_limit_notifications: int = Field(default=20, description="Notifications per hour limit")
    
    # Statistics
    messages_sent: int = Field(default=0, description="Total messages sent")
    commands_processed: int = Field(default=0, description="Total commands processed")
    last_used: Optional[datetime] = None
    
    @property
    def collection_name(self) -> str:
        return "telegram_configs"
    
    def get_decrypted_token(self) -> str:
        """Get decrypted bot token"""
        return self.decrypt_value(self.bot_token_encrypted)
    
    def update_token(self, new_token: str):
        """Update bot token"""
        self.bot_token_encrypted = self.encrypt_value(new_token)
    
    def has_permission(self, permission: str) -> bool:
        """Check if configuration has specific permission"""
        return permission in self.permissions
    
    def can_send_notification(self, notification_type: NotificationType) -> bool:
        """Check if can send specific notification type"""
        return notification_type in self.notification_types

class SystemConfigRepository(BaseRepository[SystemConfiguration]):
    """Repository for SystemConfiguration operations"""
    
    def __init__(self):
        super().__init__(SystemConfiguration)
    
    async def get_config(self, category: str, key: str, user_id: str = None) -> Optional[SystemConfiguration]:
        """Get configuration value"""
        filter_dict = {"category": category, "key": key}
        
        if user_id:
            filter_dict["user_id"] = PyObjectId(user_id)
        else:
            filter_dict["is_global"] = True
        
        return await self.get_one(filter_dict)
    
    async def set_config(self, category: str, key: str, value: Any, 
                        user_id: str = None, description: str = None,
                        encrypt: bool = False, **kwargs) -> SystemConfiguration:
        """Set configuration value"""
        existing = await self.get_config(category, key, user_id)
        
        config_data = {
            "category": category,
            "key": key,
            "value": value,
            "data_type": type(value).__name__,
            "is_global": user_id is None,
            "description": description,
            **kwargs
        }
        
        if user_id:
            config_data["user_id"] = PyObjectId(user_id)
        
        if existing:
            if encrypt:
                existing.set_value(value, encrypt=True)
                config_data["value"] = existing.value
                config_data["is_encrypted"] = True
            
            return await self.update(str(existing.id), config_data)
        else:
            config = SystemConfiguration(**config_data)
            if encrypt:
                config.set_value(value, encrypt=True)
            return await self.create(config)
    
    async def get_user_configs(self, user_id: str, category: str = None) -> List[SystemConfiguration]:
        """Get all configurations for user"""
        filter_dict = {"user_id": PyObjectId(user_id)}
        if category:
            filter_dict["category"] = category
        
        return await self.get_many(filter_dict, sort=[("category", 1), ("key", 1)])
    
    async def get_global_configs(self, category: str = None) -> List[SystemConfiguration]:
        """Get global configurations"""
        filter_dict = {"is_global": True}
        if category:
            filter_dict["category"] = category
        
        return await self.get_many(filter_dict, sort=[("category", 1), ("key", 1)])

class SystemLogRepository(BaseRepository[SystemLog]):
    """Repository for SystemLog operations"""
    
    def __init__(self):
        super().__init__(SystemLog)
    
    async def log(self, level: LogLevel, message: str, component: ComponentType,
                 user_id: str = None, **kwargs) -> SystemLog:
        """Create a log entry"""
        log_entry = SystemLog.create_log(
            level=level,
            message=message,
            component=component,
            user_id=user_id,
            **kwargs
        )
        
        return await self.create(log_entry)
    
    async def get_logs(self, level: LogLevel = None, component: ComponentType = None,
                      user_id: str = None, hours: int = 24, 
                      skip: int = 0, limit: int = 100) -> List[SystemLog]:
        """Get logs with filters"""
        from_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        filter_dict = {"created_at": {"$gte": from_time}}
        
        if level:
            filter_dict["level"] = level
        if component:
            filter_dict["component"] = component
        if user_id:
            filter_dict["user_id"] = PyObjectId(user_id)
        
        return await self.get_many(
            filter_dict=filter_dict,
            skip=skip,
            limit=limit,
            sort=[("created_at", -1)]
        )
    
    async def cleanup_expired_logs(self) -> int:
        """Remove expired log entries"""
        collection = await self.get_collection()
        result = await collection.delete_many({
            "expires_at": {"$lt": datetime.now(timezone.utc)}
        })
        return result.deleted_count
    
    async def get_log_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get log statistics"""
        from_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        collection = await self.get_collection()
        
        # Count by level
        level_pipeline = [
            {"$match": {"created_at": {"$gte": from_time}}},
            {"$group": {"_id": "$level", "count": {"$sum": 1}}}
        ]
        
        level_counts = {doc["_id"]: doc["count"] 
                       for doc in await collection.aggregate(level_pipeline).to_list(length=10)}
        
        # Count by component
        component_pipeline = [
            {"$match": {"created_at": {"$gte": from_time}}},
            {"$group": {"_id": "$component", "count": {"$sum": 1}}}
        ]
        
        component_counts = {doc["_id"]: doc["count"] 
                          for doc in await collection.aggregate(component_pipeline).to_list(length=20)}
        
        return {
            "total_logs": sum(level_counts.values()),
            "level_counts": level_counts,
            "component_counts": component_counts,
            "error_count": level_counts.get("error", 0) + level_counts.get("critical", 0)
        }

class NotificationRepository(BaseRepository[Notification]):
    """Repository for Notification operations"""
    
    def __init__(self):
        super().__init__(Notification)
    
    async def create_notification(self, user_id: str, notification_type: NotificationType,
                                title: str, message: str, channels: List[NotificationChannel],
                                **kwargs) -> Notification:
        """Create a new notification"""
        notification_data = {
            "user_id": PyObjectId(user_id),
            "type": notification_type,
            "title": title,
            "message": message,
            "channels": channels,
            **kwargs
        }
        
        return await self.create(notification_data)
    
    async def get_user_notifications(self, user_id: str, unread_only: bool = False,
                                   skip: int = 0, limit: int = 50) -> List[Notification]:
        """Get user notifications"""
        filter_dict = {"user_id": PyObjectId(user_id)}
        
        if unread_only:
            filter_dict["read"] = False
        
        return await self.get_many(
            filter_dict=filter_dict,
            skip=skip,
            limit=limit,
            sort=[("created_at", -1)]
        )
    
    async def mark_as_read(self, notification_id: str) -> bool:
        """Mark notification as read"""
        update_data = {
            "read": True,
            "read_at": datetime.now(timezone.utc)
        }
        
        result = await self.update(notification_id, update_data)
        return result is not None
    
    async def mark_all_as_read(self, user_id: str) -> int:
        """Mark all user notifications as read"""
        collection = await self.get_collection()
        result = await collection.update_many(
            {"user_id": PyObjectId(user_id), "read": False},
            {"$set": {
                "read": True,
                "read_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        return result.modified_count
    
    async def get_pending_notifications(self, channels: List[NotificationChannel] = None) -> List[Notification]:
        """Get notifications pending delivery"""
        filter_dict = {"sent_at": None}
        
        if channels:
            filter_dict["channels"] = {"$in": channels}
        
        return await self.get_many(filter_dict, sort=[("created_at", 1)])

class TelegramConfigRepository(BaseRepository[TelegramConfig]):
    """Repository for TelegramConfig operations"""
    
    def __init__(self):
        super().__init__(TelegramConfig)
    
    async def get_user_configs(self, user_id: str, active_only: bool = True) -> List[TelegramConfig]:
        """Get user telegram configurations"""
        filter_dict = {"user_id": PyObjectId(user_id)}
        if active_only:
            filter_dict["active"] = True
        
        return await self.get_many(filter_dict, sort=[("created_at", -1)])
    
    async def get_by_name(self, user_id: str, config_name: str) -> Optional[TelegramConfig]:
        """Get configuration by name"""
        return await self.get_one({
            "user_id": PyObjectId(user_id),
            "config_name": config_name
        })
    
    async def create_config(self, user_id: str, config_name: str, bot_token: str,
                          **kwargs) -> TelegramConfig:
        """Create telegram configuration"""
        config_data = {
            "user_id": PyObjectId(user_id),
            "config_name": config_name,
            "bot_token_encrypted": TelegramConfig.encrypt_value(bot_token),
            **kwargs
        }
        
        return await self.create(config_data)

# Repository instances
system_config_repository = SystemConfigRepository()
system_log_repository = SystemLogRepository()
notification_repository = NotificationRepository()
telegram_config_repository = TelegramConfigRepository()