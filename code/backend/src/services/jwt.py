"""
JWT service for token management
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from jwt.exceptions import DecodeError as JWTError
import jwt
from fastapi import HTTPException

from ..config import settings

logger = logging.getLogger(__name__)


class JWTService:
    """Service for JWT token operations"""

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create access token"""
        to_encode = data.copy()
        expire = datetime.now() + timedelta(hours=1)
        to_encode.update({"exp": int(expire.timestamp())})
        encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
        return encoded_jwt

    @staticmethod
    def decode_token(token: str) -> dict:
        """Decode and validate JWT token"""
        try:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            return payload
        except JWTError as e:
            logger.error(f"JWT decode error: {e}")
            raise HTTPException(status_code=401, detail="Invalid token")

    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        """Verify JWT token and return payload"""
        try:
            return JWTService.decode_token(token)
        except JWTError:
            return None


# Global JWT service instance
jwt_service = JWTService()