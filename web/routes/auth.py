# web/routes/auth.py

"""
Authentication Routes
Login, logout, registration, and user management
"""

from fastapi import APIRouter, Request, Form, HTTPException, status, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel, EmailStr, validator
from typing import Optional
import logging

from web.auth import auth_manager, get_current_user, rate_limiter, generate_csrf_token
from database.repositories import UserRepository
from database.models.users import User, UserCreate

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")

# Pydantic models
class LoginRequest(BaseModel):
    username: str
    password: str
    remember_me: bool = False

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    confirm_password: str
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v

# Repository
user_repo = UserRepository()

@router.get("/login")
async def login_page(request: Request):
    """Display login page"""
    # Generate CSRF token
    csrf_token = generate_csrf_token()
    request.session["csrf_token"] = csrf_token
    
    return templates.TemplateResponse("auth/login.html", {
        "request": request,
        "csrf_token": csrf_token,
        "page_title": "Login"
    })

@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    remember_me: bool = Form(False),
    csrf_token: str = Form(...)
):
    """Process login form"""
    # Verify CSRF token
    session_token = request.session.get("csrf_token")
    if not session_token or csrf_token != session_token:
        raise HTTPException(status_code=400, detail="Invalid CSRF token")
    
    # Rate limiting
    client_ip = request.client.host
    if not rate_limiter.is_allowed(client_ip):
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "error": "Too many login attempts. Please try again later.",
            "csrf_token": generate_csrf_token(),
            "page_title": "Login"
        }, status_code=429)
    
    # Authenticate user
    user = await auth_manager.authenticate_user(username, password)
    
    if not user:
        rate_limiter.record_attempt(client_ip)
        csrf_token = generate_csrf_token()
        request.session["csrf_token"] = csrf_token
        
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "error": "Invalid username or password",
            "csrf_token": csrf_token,
            "username": username,
            "page_title": "Login"
        }, status_code=400)
    
    # Create session
    request.session["user_id"] = str(user.id)
    request.session["username"] = user.username
    
    if remember_me:
        # Extend session for remember me
        request.session.permanent = True
    
    # Redirect to dashboard
    return RedirectResponse(url="/", status_code=302)

@router.get("/register")
async def register_page(request: Request):
    """Display registration page"""
    csrf_token = generate_csrf_token()
    request.session["csrf_token"] = csrf_token
    
    return templates.TemplateResponse("auth/register.html", {
        "request": request,
        "csrf_token": csrf_token,
        "page_title": "Register"
    })

@router.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    csrf_token: str = Form(...)
):
    """Process registration form"""
    # Verify CSRF token
    session_token = request.session.get("csrf_token")
    if not session_token or csrf_token != session_token:
        raise HTTPException(status_code=400, detail="Invalid CSRF token")
    
    errors = []
    
    # Validate passwords match
    if password != confirm_password:
        errors.append("Passwords do not match")
    
    # Validate password strength
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    
    # Check if username exists
    existing_user = await user_repo.get_by_username(username)
    if existing_user:
        errors.append("Username already exists")
    
    # Check if email exists
    existing_email = await user_repo.get_by_email(email)
    if existing_email:
        errors.append("Email already registered")
    
    if errors:
        csrf_token = generate_csrf_token()
        request.session["csrf_token"] = csrf_token
        
        return templates.TemplateResponse("auth/register.html", {
            "request": request,
            "errors": errors,
            "csrf_token": csrf_token,
            "username": username,
            "email": email,
            "page_title": "Register"
        }, status_code=400)
    
    try:
        # Create user
        user_data = UserCreate(
            username=username,
            email=email,
            password=password
        )
        
        user = await user_repo.create(user_data)
        
        # Auto-login after registration
        request.session["user_id"] = str(user.id)
        request.session["username"] = user.username
        
        return RedirectResponse(url="/", status_code=302)
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        csrf_token = generate_csrf_token()
        request.session["csrf_token"] = csrf_token
        
        return templates.TemplateResponse("auth/register.html", {
            "request": request,
            "error": "Registration failed. Please try again.",
            "csrf_token": csrf_token,
            "username": username,
            "email": email,
            "page_title": "Register"
        }, status_code=500)

@router.get("/logout")
async def logout(request: Request):
    """Logout user"""
    request.session.clear()
    return RedirectResponse(url="/auth/login", status_code=302)

@router.get("/profile")
async def profile_page(request: Request, user: User = Depends(get_current_user)):
    """Display user profile page"""
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    csrf_token = generate_csrf_token()
    request.session["csrf_token"] = csrf_token
    
    return templates.TemplateResponse("auth/profile.html", {
        "request": request,
        "user": user,
        "csrf_token": csrf_token,
        "page_title": "Profile"
    })

@router.post("/change-password")
async def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    csrf_token: str = Form(...),
    user: User = Depends(get_current_user)
):
    """Change user password"""
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Verify CSRF token
    session_token = request.session.get("csrf_token")
    if not session_token or csrf_token != session_token:
        raise HTTPException(status_code=400, detail="Invalid CSRF token")
    
    errors = []
    
    # Verify current password
    if not auth_manager.verify_password(current_password, user.password_hash):
        errors.append("Current password is incorrect")
    
    # Validate new password
    if len(new_password) < 8:
        errors.append("New password must be at least 8 characters long")
    
    if new_password != confirm_password:
        errors.append("New passwords do not match")
    
    if errors:
        csrf_token = generate_csrf_token()
        request.session["csrf_token"] = csrf_token
        
        return templates.TemplateResponse("auth/profile.html", {
            "request": request,
            "user": user,
            "errors": errors,
            "csrf_token": csrf_token,
            "page_title": "Profile"
        }, status_code=400)
    
    try:
        # Update password
        new_hash = auth_manager.get_password_hash(new_password)
        await user_repo.update_password(user.id, new_hash)
        
        csrf_token = generate_csrf_token()
        request.session["csrf_token"] = csrf_token
        
        return templates.TemplateResponse("auth/profile.html", {
            "request": request,
            "user": user,
            "success": "Password changed successfully",
            "csrf_token": csrf_token,
            "page_title": "Profile"
        })
        
    except Exception as e:
        logger.error(f"Password change error: {e}")
        csrf_token = generate_csrf_token()
        request.session["csrf_token"] = csrf_token
        
        return templates.TemplateResponse("auth/profile.html", {
            "request": request,
            "user": user,
            "error": "Failed to change password. Please try again.",
            "csrf_token": csrf_token,
            "page_title": "Profile"
        }, status_code=500)

# API endpoints for AJAX requests
@router.post("/api/login")
async def api_login(request: Request, login_data: LoginRequest):
    """API login endpoint"""
    client_ip = request.client.host
    if not rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts"
        )
    
    user = await auth_manager.authenticate_user(login_data.username, login_data.password)
    
    if not user:
        rate_limiter.record_attempt(client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Create tokens
    access_token = auth_manager.create_access_token({"sub": str(user.id)})
    refresh_token = auth_manager.create_refresh_token({"sub": str(user.id)})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email
        }
    }

@router.post("/api/refresh")
async def api_refresh(refresh_token: str):
    """Refresh access token"""
    payload = auth_manager.verify_token(refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    user = await user_repo.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    # Create new access token
    access_token = auth_manager.create_access_token({"sub": str(user.id)})
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
