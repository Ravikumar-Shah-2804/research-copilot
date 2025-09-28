"""
Authentication router
"""
import logging
from datetime import timedelta, datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from jwt.exceptions import PyJWTError

try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)

from ..database import get_db
from ..services.auth import (
    authenticate_user,
    get_current_active_user,
    create_refresh_token_for_user,
    refresh_access_token,
    revoke_refresh_token,
    revoke_all_user_tokens,
    get_current_user,
    get_password_hash
)
from ..services.refresh_token import refresh_token_service
from ..models import User
from sqlalchemy import select
from ..schemas.auth import (
    Token,
    RefreshTokenRequest,
    RevokeTokenRequest,
    TokenInfo,
    UserCreate,
    UserResponse
)
from ..config import settings
from ..utils.security_logging import security_logger, audit_logger
from ..utils.exceptions import AuthenticationError

router = APIRouter()


@router.post("/register", response_model=UserResponse)
async def register_user(
    request: Request,
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user"""
    client_ip = getattr(request.client, 'host', None) if request.client else None
    user_agent = request.headers.get("User-Agent")
    registration_time = datetime.utcnow().isoformat()

    # Input validation
    if not user_data.username or not user_data.username.strip():
        logger.warning("Registration attempt with empty username", ip_address=client_ip, user_agent=user_agent)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username cannot be empty"
        )

    if not user_data.email or not user_data.email.strip():
        logger.warning("Registration attempt with empty email", ip_address=client_ip, user_agent=user_agent)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email cannot be empty"
        )

    if not user_data.password or not user_data.password.strip():
        logger.warning("Registration attempt with empty password", username=user_data.username, email=user_data.email, ip_address=client_ip)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password cannot be empty"
        )

    # Basic validation
    if len(user_data.username) > 50 or len(user_data.username) < 3:
        logger.warning("Registration attempt with invalid username length", username=user_data.username[:20], ip_address=client_ip)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must be between 3 and 50 characters"
        )

    if len(user_data.password) < 8:
        logger.warning("Registration attempt with weak password", username=user_data.username, ip_address=client_ip)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )

    logger.info("User registration attempt", username=user_data.username, email=user_data.email, ip_address=client_ip, user_agent=user_agent, registration_time=registration_time)

    try:
        # Check if user already exists
        result = await db.execute(
            select(User).where(
                (User.username == user_data.username) | (User.email == user_data.email)
            )
        )
        existing_user = result.scalar_one_or_none()
        if existing_user:
            logger.warning("Registration failed: user already exists", username=user_data.username, email=user_data.email, ip_address=client_ip)
            audit_logger.log_audit_event(
                action="user_registration_failed",
                resource_type="user",
                success=False,
                error_message="User already exists",
                metadata={"username": user_data.username, "email": user_data.email, "ip_address": client_ip}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already registered"
            )

        # Create user
        hashed_password = get_password_hash(user_data.password)
        user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            is_active=True,
            is_superuser=False
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info("User registered successfully", user_id=user.id, username=user.username, email=user.email, ip_address=client_ip, registration_time=registration_time)
        audit_logger.log_audit_event(
            action="user_registered",
            resource_type="user",
            resource_id=str(user.id),
            user_id=str(user.id),
            success=True,
            metadata={"username": user.username, "email": user.email, "ip_address": client_ip}
        )
        return user

    except HTTPException:
        raise
    except SQLAlchemyError as db_error:
        logger.error("Database error during user registration", username=user_data.username, email=user_data.email, error=str(db_error), ip_address=client_ip)
        await db.rollback()
        audit_logger.log_audit_event(
            action="user_registration_failed",
            resource_type="user",
            success=False,
            error_message="Database error",
            metadata={"username": user_data.username, "email": user_data.email, "error_type": "database_error", "ip_address": client_ip}
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable"
        )
    except Exception as e:
        logger.error("Unexpected error during user registration", username=user_data.username, email=user_data.email, error=str(e), ip_address=client_ip, exc_info=True)
        await db.rollback()
        audit_logger.log_audit_event(
            action="user_registration_failed",
            resource_type="user",
            success=False,
            error_message=str(e),
            metadata={"username": user_data.username, "email": user_data.email, "error_type": "unexpected_error", "ip_address": client_ip}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/token", response_model=Token)
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Login endpoint - OAuth2 compatible token endpoint"""
    client_ip = getattr(request.client, 'host', None) if request.client else None
    user_agent = request.headers.get("User-Agent")
    attempt_time = datetime.utcnow().isoformat()

    # Input validation
    if not form_data.username or not form_data.username.strip():
        security_logger.log_auth_failure(
            identifier="empty_username",
            reason="empty_username",
            ip_address=client_ip,
            user_agent=user_agent
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username cannot be empty"
        )

    if not form_data.password or not form_data.password.strip():
        security_logger.log_auth_failure(
            identifier=form_data.username,
            reason="empty_password",
            ip_address=client_ip,
            user_agent=user_agent
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password cannot be empty"
        )

    # Basic length checks to prevent malformed inputs
    if len(form_data.username) > 254:  # RFC 5321 limit for email
        security_logger.log_auth_failure(
            identifier=form_data.username[:50] + "...",
            reason="username_too_long",
            ip_address=client_ip,
            user_agent=user_agent
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username too long"
        )

    if len(form_data.password) > 128:  # Reasonable password length limit
        security_logger.log_auth_failure(
            identifier=form_data.username,
            reason="password_too_long",
            ip_address=client_ip,
            user_agent=user_agent
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password too long"
        )

    logger.info("Login attempt", username=form_data.username, ip_address=client_ip, user_agent=user_agent, attempt_time=attempt_time)

    try:
        # Authenticate user
        user = await authenticate_user(db, form_data.username, form_data.password)
        if not user:
            security_logger.log_auth_failure(
                identifier=form_data.username,
                reason="invalid_credentials",
                ip_address=client_ip,
                user_agent=user_agent
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Get full user object
        result = await db.execute(
            select(User).where(User.username == user["username"])
        )
        user_obj = result.scalar_one_or_none()
        if not user_obj:
            security_logger.log_auth_failure(
                identifier=form_data.username,
                reason="user_not_found",
                ip_address=client_ip,
                user_agent=user_agent
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create tokens with specific exception handling
        try:
            access_token, refresh_token = await create_refresh_token_for_user(
                db=db,
                user=user_obj,
                device_info=user_agent,
                ip_address=client_ip,
                user_agent=user_agent
            )
        except SQLAlchemyError as db_error:
            logger.error("Database error during token creation", user_id=user_obj.id, username=user_obj.username, error=str(db_error), ip_address=client_ip)
            audit_logger.log_audit_event(
                action="token_creation_failed",
                resource_type="auth_token",
                user_id=str(user_obj.id),
                success=False,
                error_message="Database error during token creation",
                metadata={"error_type": "database_error", "ip_address": client_ip}
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable"
            )
        except PyJWTError as jwt_error:
            logger.error("JWT error during token creation", user_id=user_obj.id, username=user_obj.username, error=str(jwt_error), ip_address=client_ip)
            audit_logger.log_audit_event(
                action="token_creation_failed",
                resource_type="auth_token",
                user_id=str(user_obj.id),
                success=False,
                error_message="JWT encoding error",
                metadata={"error_type": "jwt_error", "ip_address": client_ip}
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Token generation failed"
            )
        except Exception as token_error:
            logger.error("Unexpected error during token creation", user_id=user_obj.id, username=user_obj.username, error=str(token_error), ip_address=client_ip)
            audit_logger.log_audit_event(
                action="token_creation_failed",
                resource_type="auth_token",
                user_id=str(user_obj.id),
                success=False,
                error_message=str(token_error),
                metadata={"error_type": "unexpected_error", "ip_address": client_ip}
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Token generation failed"
            )

        # Log successful authentication
        security_logger.log_auth_success(
            user_id=str(user_obj.id),
            method="password",
            ip_address=client_ip,
            user_agent=user_agent
        )

        logger.info("Login successful", user_id=user_obj.id, username=user_obj.username, ip_address=client_ip, attempt_time=attempt_time)

        return Token(
            access_token=access_token,
            token_type="bearer",
            refresh_token=refresh_token,
            expires_in=settings.jwt_access_token_expire_minutes * 60
        )

    except HTTPException:
        raise
    except AuthenticationError as auth_error:
        logger.warning("Authentication error", error=str(auth_error), ip_address=client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except SQLAlchemyError as db_error:
        logger.error("Database error during login", error=str(db_error), ip_address=client_ip)
        audit_logger.log_audit_event(
            action="login_failed",
            resource_type="auth",
            success=False,
            error_message="Database error",
            metadata={"error_type": "database_error", "ip_address": client_ip}
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable"
        )
    except Exception as e:
        logger.error("Unexpected error during login", error=str(e), ip_address=client_ip, exc_info=True)
        audit_logger.log_audit_event(
            action="login_failed",
            resource_type="auth",
            success=False,
            error_message=str(e),
            metadata={"error_type": "unexpected_error", "ip_address": client_ip}
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    logger.info("User profile accessed", user_id=current_user.id, username=current_user.username)
    return current_user


@router.get("/tokens", response_model=List[TokenInfo])
async def get_user_tokens(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all refresh tokens for current user"""
    tokens = await refresh_token_service.get_user_tokens(db, current_user.id)
    return tokens


@router.post("/refresh", response_model=Token)
async def refresh_access_token_endpoint(
    request: Request,
    refresh_request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token"""
    client_ip = getattr(request.client, 'host', None) if request.client else None
    user_agent = request.headers.get("User-Agent")
    refresh_time = datetime.utcnow().isoformat()

    # Input validation
    if not refresh_request.refresh_token or not refresh_request.refresh_token.strip():
        logger.warning("Token refresh attempt with empty refresh token", ip_address=client_ip, user_agent=user_agent)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token cannot be empty"
        )

    logger.info("Token refresh attempt", ip_address=client_ip, user_agent=user_agent, refresh_time=refresh_time)

    try:
        access_token, refresh_token = await refresh_access_token(
            db, refresh_request.refresh_token
        )

        logger.info("Token refresh successful", ip_address=client_ip, refresh_time=refresh_time)

        return Token(
            access_token=access_token,
            token_type="bearer",
            refresh_token=refresh_token,
            expires_in=settings.jwt_access_token_expire_minutes * 60
        )

    except AuthenticationError as auth_error:
        logger.warning("Token refresh failed: authentication error", error=str(auth_error), ip_address=client_ip)
        audit_logger.log_audit_event(
            action="token_refresh_failed",
            resource_type="auth_token",
            success=False,
            error_message="Invalid refresh token",
            metadata={"error_type": "authentication_error", "ip_address": client_ip}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    except SQLAlchemyError as db_error:
        logger.error("Database error during token refresh", error=str(db_error), ip_address=client_ip)
        audit_logger.log_audit_event(
            action="token_refresh_failed",
            resource_type="auth_token",
            success=False,
            error_message="Database error",
            metadata={"error_type": "database_error", "ip_address": client_ip}
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable"
        )
    except PyJWTError as jwt_error:
        logger.warning("JWT error during token refresh", error=str(jwt_error), ip_address=client_ip)
        audit_logger.log_audit_event(
            action="token_refresh_failed",
            resource_type="auth_token",
            success=False,
            error_message="JWT error",
            metadata={"error_type": "jwt_error", "ip_address": client_ip}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    except Exception as e:
        logger.error("Unexpected error during token refresh", error=str(e), ip_address=client_ip, exc_info=True)
        audit_logger.log_audit_event(
            action="token_refresh_failed",
            resource_type="auth_token",
            success=False,
            error_message=str(e),
            metadata={"error_type": "unexpected_error", "ip_address": client_ip}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post("/logout")
async def logout(
    request: Request,
    refresh_request: RefreshTokenRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Logout by revoking refresh token"""
    client_ip = getattr(request.client, 'host', None) if request.client else None
    user_agent = request.headers.get("User-Agent")
    logout_time = datetime.utcnow().isoformat()

    # Input validation
    if not refresh_request.refresh_token or not refresh_request.refresh_token.strip():
        logger.warning("Logout attempt with empty refresh token", user_id=current_user.id, username=current_user.username, ip_address=client_ip)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token cannot be empty"
        )

    logger.info("Logout attempt", user_id=current_user.id, username=current_user.username, ip_address=client_ip, user_agent=user_agent, logout_time=logout_time)

    try:
        await revoke_refresh_token(
            db, refresh_request.refresh_token, "User logout"
        )

        logger.info("Logout successful", user_id=current_user.id, username=current_user.username, ip_address=client_ip, logout_time=logout_time)
        audit_logger.log_audit_event(
            action="user_logout",
            resource_type="auth_session",
            user_id=str(current_user.id),
            success=True,
            metadata={"ip_address": client_ip, "user_agent": user_agent}
        )

        return {"message": "Successfully logged out"}

    except SQLAlchemyError as db_error:
        logger.error("Database error during logout", user_id=current_user.id, username=current_user.username, error=str(db_error), ip_address=client_ip)
        audit_logger.log_audit_event(
            action="user_logout_failed",
            resource_type="auth_session",
            user_id=str(current_user.id),
            success=False,
            error_message="Database error",
            metadata={"error_type": "database_error", "ip_address": client_ip}
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable"
        )
    except Exception as e:
        logger.error("Unexpected error during logout", user_id=current_user.id, username=current_user.username, error=str(e), ip_address=client_ip, exc_info=True)
        audit_logger.log_audit_event(
            action="user_logout_failed",
            resource_type="auth_session",
            user_id=str(current_user.id),
            success=False,
            error_message=str(e),
            metadata={"error_type": "unexpected_error", "ip_address": client_ip}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.post("/logout-all")
async def logout_all_devices(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Logout from all devices by revoking all refresh tokens"""
    client_ip = getattr(request.client, 'host', None) if request.client else None
    user_agent = request.headers.get("User-Agent")
    logout_time = datetime.utcnow().isoformat()

    logger.info("Logout all devices attempt", user_id=current_user.id, username=current_user.username, ip_address=client_ip, user_agent=user_agent, logout_time=logout_time)

    try:
        await revoke_all_user_tokens(
            db, current_user.id, "User logout from all devices"
        )

        logger.info("Logout all devices successful", user_id=current_user.id, username=current_user.username, ip_address=client_ip, logout_time=logout_time)
        audit_logger.log_audit_event(
            action="user_logout_all",
            resource_type="auth_session",
            user_id=str(current_user.id),
            success=True,
            metadata={"ip_address": client_ip, "user_agent": user_agent}
        )

        return {"message": "Successfully logged out from all devices"}

    except SQLAlchemyError as db_error:
        logger.error("Database error during logout all devices", user_id=current_user.id, username=current_user.username, error=str(db_error), ip_address=client_ip)
        audit_logger.log_audit_event(
            action="user_logout_all_failed",
            resource_type="auth_session",
            user_id=str(current_user.id),
            success=False,
            error_message="Database error",
            metadata={"error_type": "database_error", "ip_address": client_ip}
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable"
        )
    except Exception as e:
        logger.error("Unexpected error during logout all devices", user_id=current_user.id, username=current_user.username, error=str(e), ip_address=client_ip, exc_info=True)
        audit_logger.log_audit_event(
            action="user_logout_all_failed",
            resource_type="auth_session",
            user_id=str(current_user.id),
            success=False,
            error_message=str(e),
            metadata={"error_type": "unexpected_error", "ip_address": client_ip}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )