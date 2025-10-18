"""
Authentication Module
Handles JWT tokens, password hashing, and user verification
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings
from app.database import get_db, Database

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token scheme
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token

    Args:
        data: Dictionary with user data (must include 'sub' key with user email)
        expires_delta: Optional expiration time delta

    Returns:
        JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    return encoded_jwt


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Database = Depends(get_db)
):
    """
    FastAPI dependency to get current authenticated user

    Raises:
        HTTPException: If token is invalid or user not found

    Returns:
        User record from database
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")

        if email is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    # Get user from database
    user = await db.fetchrow(
        "SELECT * FROM promo_users WHERE email = $1 AND is_active = TRUE",
        email
    )

    if user is None:
        raise credentials_exception

    return user


async def authenticate_user(email: str, password: str, db: Database) -> Optional[dict]:
    """
    Authenticate a user by email and password

    Args:
        email: User email
        password: Plain text password
        db: Database instance

    Returns:
        User record if authentication successful, None otherwise
    """
    user = await db.fetchrow(
        "SELECT * FROM promo_users WHERE email = $1 AND is_active = TRUE",
        email
    )

    if not user:
        return None

    if not verify_password(password, user['password_hash']):
        return None

    return dict(user)
