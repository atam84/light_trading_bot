# web/auth.py

"""
Web Authentication System
JWT-based authentication with session management
"""

from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import secrets
import logging

from database.repositories import UserRepository
from database.models.users import User
from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security
security = HTTPBearer(auto_error=False)

class AuthManager:
    """Authentication and authorization manager"""
    
    def __init__(self):
        self.config = ConfigManager()
        self.user_repo = UserRepository()
        self.secret_key = self.config.get("security.secret_key")
        self.algorithm = "HS256"
        self.access_token_expire = self.config.get("security.access_token_expire_minutes", 30)
        self.refresh_token_expire = self.config.get("security.refresh_token_expire_days", 7)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Hash password"""
        return pwd_context.hash(password)
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire)
        
        to_encode.update({"exp": expire, "type": "access"})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire)
        to_encode.update({"exp": expire, "type": "refresh"})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            return None
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username/password"""
        try:
            user = await self.user_repo.get_by_username(username)
            if not user:
                return None
            
            if not self.verify_password(password, user.password_hash):
                return None
            
            # Update last login
            await self.user_repo.update_last_login(user.id)
            return user
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
    
    async def get_user_by_token(self, token: str) -> Optional[User]:
        """Get user from JWT token"""
        payload = self.verify_token(token)
        if not payload:
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        try:
            return await self.user_repo.get_by_id(user_id)
        except Exception as e:
            logger.error(f"Error getting user by token: {e}")
            return None

# Global auth manager instance
auth_manager = AuthManager()

# Dependency functions
async def get_current_user(request: Request) -> Optional[User]:
    """Get current user from session or token"""
    # Try session first
    user_id = request.session.get("user_id")
    if user_id:
        try:
            return await auth_manager.user_repo.get_by_id(user_id)
        except Exception:
            pass
    
    # Try Authorization header
    authorization = request.headers.get("Authorization")
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        return await auth_manager.get_user_by_token(token)
    
    return None

async def require_auth(request: Request) -> User:
    """Require authentication, raise exception if not authenticated"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return user

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[Dict[str, Any]]:
    """Verify JWT token from Authorization header"""
    if not credentials:
        return None
    
    return auth_manager.verify_token(credentials.credentials)

def generate_csrf_token() -> str:
    """Generate CSRF token"""
    return secrets.token_urlsafe(32)

def verify_csrf_token(request: Request, token: str) -> bool:
    """Verify CSRF token"""
    session_token = request.session.get("csrf_token")
    return session_token and secrets.compare_digest(session_token, token)

# Rate limiting (simple in-memory implementation)
class RateLimiter:
    """Simple rate limiter for authentication attempts"""
    
    def __init__(self):
        self.attempts = {}
        self.max_attempts = 5
        self.window_minutes = 15
    
    def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed"""
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=self.window_minutes)
        
        # Clean old attempts
        if identifier in self.attempts:
            self.attempts[identifier] = [
                attempt for attempt in self.attempts[identifier]
                if attempt > window_start
            ]
        
        # Check current attempts
        current_attempts = len(self.attempts.get(identifier, []))
        return current_attempts < self.max_attempts
    
    def record_attempt(self, identifier: str):
        """Record failed attempt"""
        if identifier not in self.attempts:
            self.attempts[identifier] = []
        self.attempts[identifier].append(datetime.utcnow())

# Global rate limiter
rate_limiter = RateLimiter()

# Security headers middleware
async def add_security_headers(request: Request, call_next):
    """Add security headers to responses"""
    response = await call_next(request)
    
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' data: https:; "
        "connect-src 'self' ws: wss:;"
    )
    
    return response
