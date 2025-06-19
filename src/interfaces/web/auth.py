# src/interfaces/web/auth.py

"""
Authentication System for Web Interface
Handles user login, sessions, and security
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel
import bcrypt

from ...database import UserRepository
from ...database.models.user import UserModel
from ...core import ConfigManager

logger = logging.getLogger(__name__)

# Configuration
SECRET_KEY = "your_secret_key_here"  # In production, use environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security scheme
security = HTTPBearer()

# Create router
auth_router = APIRouter()

# Pydantic models
class UserLogin(BaseModel):
    username: str
    password: str

class UserRegister(BaseModel):
    username: str
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    created_at: datetime
    last_login: Optional[datetime] = None

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Error verifying password: {str(e)}")
        return False

def get_password_hash(password: str) -> str:
    """Hash a password"""
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Error hashing password: {str(e)}")
        raise

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserModel:
    """Get current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
    
    user_repo = UserRepository()
    user = await user_repo.get_by_username(username)
    if user is None:
        raise credentials_exception
        
    return user

async def get_optional_user(request: Request) -> Optional[UserModel]:
    """Get current user if authenticated, otherwise return None"""
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
            
        token = auth_header.split(" ")[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        
        if username is None:
            return None
            
        user_repo = UserRepository()
        user = await user_repo.get_by_username(username)
        return user
        
    except:
        return None

@auth_router.post("/register", response_model=UserResponse)
async def register_user(user_data: UserRegister):
    """Register a new user"""
    try:
        user_repo = UserRepository()
        
        # Check if user already exists
        existing_user = await user_repo.get_by_username(user_data.username)
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Username already registered"
            )
        
        existing_email = await user_repo.get_by_email(user_data.email)
        if existing_email:
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )
        
        # Hash password
        hashed_password = get_password_hash(user_data.password)
        
        # Create user
        user_dict = {
            "username": user_data.username,
            "email": user_data.email,
            "password_hash": hashed_password,
            "created_at": datetime.utcnow(),
            "settings": {
                "timezone": "UTC",
                "currency": "USD",
                "theme": "dark"
            }
        }
        
        user = await user_repo.create(user_dict)
        
        logger.info(f"New user registered: {user_data.username}")
        
        return UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            created_at=user.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering user: {str(e)}")
        raise HTTPException(status_code=500, detail="Registration failed")

@auth_router.post("/login", response_model=Token)
async def login_user(user_data: UserLogin):
    """Login user and return JWT token"""
    try:
        user_repo = UserRepository()
        
        # Get user by username
        user = await user_repo.get_by_username(user_data.username)
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password"
            )
        
        # Verify password
        if not verify_password(user_data.password, user.password_hash):
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password"
            )
        
        # Update last login
        await user_repo.update(str(user.id), {"last_login": datetime.utcnow()})
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username},
            expires_delta=access_token_expires
        )
        
        logger.info(f"User logged in: {user_data.username}")
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60  # seconds
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        raise HTTPException(status_code=500, detail="Login failed")

@auth_router.post("/logout")
async def logout_user(current_user: UserModel = Depends(get_current_user)):
    """Logout user (token will be invalidated on client side)"""
    try:
        logger.info(f"User logged out: {current_user.username}")
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        logger.error(f"Error during logout: {str(e)}")
        raise HTTPException(status_code=500, detail="Logout failed")

@auth_router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: UserModel = Depends(get_current_user)):
    """Get current user information"""
    try:
        return UserResponse(
            id=str(current_user.id),
            username=current_user.username,
            email=current_user.email,
            created_at=current_user.created_at,
            last_login=current_user.last_login
        )
        
    except Exception as e:
        logger.error(f"Error getting user info: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get user information")

@auth_router.put("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Change user password"""
    try:
        # Verify current password
        if not verify_password(current_password, current_user.password_hash):
            raise HTTPException(
                status_code=400,
                detail="Current password is incorrect"
            )
        
        # Hash new password
        new_password_hash = get_password_hash(new_password)
        
        # Update user
        user_repo = UserRepository()
        await user_repo.update(str(current_user.id), {
            "password_hash": new_password_hash,
            "updated_at": datetime.utcnow()
        })
        
        logger.info(f"Password changed for user: {current_user.username}")
        
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing password: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to change password")

@auth_router.get("/validate-token")
async def validate_token(current_user: UserModel = Depends(get_current_user)):
    """Validate JWT token"""
    return {
        "valid": True,
        "username": current_user.username,
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

# Simple session-based authentication for HTML pages
@auth_router.get("/session")
async def get_session_info(request: Request):
    """Get session information for HTML pages"""
    try:
        user = await get_optional_user(request)
        if user:
            return {
                "authenticated": True,
                "username": user.username,
                "user_id": str(user.id)
            }
        else:
            return {
                "authenticated": False,
                "username": None,
                "user_id": None
            }
            
    except Exception as e:
        logger.error(f"Error getting session info: {str(e)}")
        return {
            "authenticated": False,
            "username": None,
            "user_id": None
        }

# Demo user creation for testing
@auth_router.post("/create-demo-user")
async def create_demo_user():
    """Create a demo user for testing (remove in production)"""
    try:
        user_repo = UserRepository()
        
        # Check if demo user already exists
        demo_user = await user_repo.get_by_username("demo")
        if demo_user:
            return {"message": "Demo user already exists"}
        
        # Create demo user
        demo_data = {
            "username": "demo",
            "email": "demo@tradingbot.com",
            "password_hash": get_password_hash("demo123"),
            "created_at": datetime.utcnow(),
            "settings": {
                "timezone": "UTC",
                "currency": "USD",
                "theme": "dark"
            }
        }
        
        user = await user_repo.create(demo_data)
        
        return {
            "message": "Demo user created successfully",
            "username": "demo",
            "password": "demo123"
        }
        
    except Exception as e:
        logger.error(f"Error creating demo user: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create demo user")
