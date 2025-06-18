# src/database/models/user.py

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import Field, validator, EmailStr
from enum import Enum
import bcrypt
from src.database.models.base import BaseDBModel, BaseRepository, TimestampMixin, PyObjectId

class UserRole(str, Enum):
    """User roles"""
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"

class UserSettings(BaseDBModel):
    """User settings model"""
    timezone: str = Field(default="UTC", description="User timezone")
    currency: str = Field(default="USD", description="Preferred currency")
    theme: str = Field(default="dark", description="UI theme preference")
    language: str = Field(default="en", description="Language preference")
    notifications_enabled: bool = Field(default=True)
    email_notifications: bool = Field(default=True)
    telegram_notifications: bool = Field(default=True)
    
    @property
    def collection_name(self) -> str:
        return "user_settings"

class SocialAuth(BaseDBModel):
    """Social authentication details"""
    google_id: Optional[str] = None
    github_id: Optional[str] = None
    discord_id: Optional[str] = None
    
    @property
    def collection_name(self) -> str:
        return "social_auth"

class User(BaseDBModel, TimestampMixin):
    """User model for authentication and management"""
    
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    email: EmailStr = Field(..., description="User email address")
    password_hash: str = Field(..., description="Hashed password")
    role: UserRole = Field(default=UserRole.USER, description="User role")
    active: bool = Field(default=True, description="Account status")
    email_verified: bool = Field(default=False, description="Email verification status")
    last_login: Optional[datetime] = None
    login_attempts: int = Field(default=0, description="Failed login attempts")
    locked_until: Optional[datetime] = None
    
    # Profile information
    first_name: Optional[str] = Field(None, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)
    avatar_url: Optional[str] = None
    
    # Settings
    settings: UserSettings = Field(default_factory=UserSettings)
    social_auth: SocialAuth = Field(default_factory=SocialAuth)
    
    # Statistics
    total_trades: int = Field(default=0)
    total_profit: float = Field(default=0.0)
    last_activity: Optional[datetime] = None
    
    @property
    def collection_name(self) -> str:
        return "users"
    
    @validator('username')
    def validate_username(cls, v):
        if not v.isalnum() and '_' not in v and '-' not in v:
            raise ValueError('Username can only contain letters, numbers, underscore and dash')
        return v.lower()
    
    @validator('email')
    def validate_email(cls, v):
        return v.lower()
    
    @classmethod
    def hash_password(cls, password: str) -> str:
        """Hash password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, password: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def is_locked(self) -> bool:
        """Check if account is locked"""
        if not self.locked_until:
            return False
        return datetime.now(timezone.utc) < self.locked_until
    
    def can_login(self) -> bool:
        """Check if user can login"""
        return self.active and self.email_verified and not self.is_locked()
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.now(timezone.utc)
        self.last_activity = self.last_login
        self.login_attempts = 0  # Reset failed attempts on successful login
    
    def increment_login_attempts(self):
        """Increment failed login attempts"""
        self.login_attempts += 1
        if self.login_attempts >= 5:  # Lock account after 5 failed attempts
            self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
    
    def to_public_dict(self) -> Dict[str, Any]:
        """Return public user information (no sensitive data)"""
        return {
            "id": str(self.id),
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "active": self.active,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "avatar_url": self.avatar_url,
            "created_at": self.created_at,
            "last_login": self.last_login,
            "total_trades": self.total_trades,
            "total_profit": self.total_profit,
            "settings": self.settings.dict() if self.settings else {}
        }

class UserSession(BaseDBModel, TimestampMixin):
    """User session model for tracking active sessions"""
    
    user_id: PyObjectId = Field(..., description="User ID")
    session_token: str = Field(..., description="Session token")
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    expires_at: datetime = Field(..., description="Session expiration")
    active: bool = Field(default=True)
    last_activity: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def collection_name(self) -> str:
        return "user_sessions"
    
    def is_expired(self) -> bool:
        """Check if session is expired"""
        return datetime.now(timezone.utc) > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if session is valid"""
        return self.active and not self.is_expired()

class UserRepository(BaseRepository[User]):
    """Repository for User model operations"""
    
    def __init__(self):
        super().__init__(User)
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        return await self.get_one({"username": username.lower()})
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return await self.get_one({"email": email.lower()})
    
    async def create_user(self, username: str, email: str, password: str, **kwargs) -> User:
        """Create a new user"""
        user_data = {
            "username": username.lower(),
            "email": email.lower(),
            "password_hash": User.hash_password(password),
            **kwargs
        }
        return await self.create(user_data)
    
    async def authenticate(self, username_or_email: str, password: str) -> Optional[User]:
        """Authenticate user with username/email and password"""
        # Try to find user by username or email
        user = await self.get_by_username(username_or_email)
        if not user:
            user = await self.get_by_email(username_or_email)
        
        if not user:
            return None
        
        if not user.can_login():
            return None
        
        if user.verify_password(password):
            # Update last login
            await self.update(user.id, {
                "last_login": datetime.now(timezone.utc),
                "last_activity": datetime.now(timezone.utc),
                "login_attempts": 0
            })
            return user
        else:
            # Increment failed login attempts
            await self.update(user.id, {
                "login_attempts": user.login_attempts + 1,
                "locked_until": (
                    datetime.now(timezone.utc) + timedelta(minutes=30)
                    if user.login_attempts >= 4 else None
                )
            })
            return None
    
    async def update_password(self, user_id: str, new_password: str) -> bool:
        """Update user password"""
        password_hash = User.hash_password(new_password)
        result = await self.update(user_id, {"password_hash": password_hash})
        return result is not None
    
    async def update_settings(self, user_id: str, settings: Dict[str, Any]) -> Optional[User]:
        """Update user settings"""
        return await self.update(user_id, {"settings": settings})
    
    async def get_active_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get active users"""
        return await self.get_many(
            filter_dict={"active": True},
            skip=skip,
            limit=limit,
            sort=[("created_at", -1)]
        )
    
    async def search_users(self, query: str, skip: int = 0, limit: int = 20) -> List[User]:
        """Search users by username or email"""
        filter_dict = {
            "$or": [
                {"username": {"$regex": query, "$options": "i"}},
                {"email": {"$regex": query, "$options": "i"}}
            ]
        }
        return await self.get_many(filter_dict, skip=skip, limit=limit)

class UserSessionRepository(BaseRepository[UserSession]):
    """Repository for UserSession model operations"""
    
    def __init__(self):
        super().__init__(UserSession)
    
    async def create_session(self, user_id: str, session_token: str, 
                           expires_in_hours: int = 24, **kwargs) -> UserSession:
        """Create a new user session"""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
        session_data = {
            "user_id": ObjectId(user_id),
            "session_token": session_token,
            "expires_at": expires_at,
            **kwargs
        }
        return await self.create(session_data)
    
    async def get_by_token(self, session_token: str) -> Optional[UserSession]:
        """Get session by token"""
        return await self.get_one({"session_token": session_token})
    
    async def get_user_sessions(self, user_id: str, active_only: bool = True) -> List[UserSession]:
        """Get all sessions for a user"""
        filter_dict = {"user_id": ObjectId(user_id)}
        if active_only:
            filter_dict["active"] = True
        return await self.get_many(filter_dict, sort=[("created_at", -1)])
    
    async def invalidate_session(self, session_token: str) -> bool:
        """Invalidate a session"""
        collection = await self.get_collection()
        result = await collection.update_one(
            {"session_token": session_token},
            {"$set": {"active": False, "updated_at": datetime.now(timezone.utc)}}
        )
        return result.modified_count > 0
    
    async def invalidate_user_sessions(self, user_id: str) -> int:
        """Invalidate all sessions for a user"""
        collection = await self.get_collection()
        result = await collection.update_many(
            {"user_id": ObjectId(user_id)},
            {"$set": {"active": False, "updated_at": datetime.now(timezone.utc)}}
        )
        return result.modified_count
    
    async def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions"""
        collection = await self.get_collection()
        result = await collection.delete_many({
            "expires_at": {"$lt": datetime.now(timezone.utc)}
        })
        return result.deleted_count

# Repository instances
user_repository = UserRepository()
user_session_repository = UserSessionRepository()