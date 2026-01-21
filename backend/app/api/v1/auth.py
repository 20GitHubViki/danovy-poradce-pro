"""
Authentication API endpoints.

Provides user registration, login, token refresh, and logout functionality.
"""

from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User, UserRole

router = APIRouter()
security = HTTPBearer()


# --- Pydantic Schemas ---


class UserRegister(BaseModel):
    """User registration request."""

    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    """User login request."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    """User data response."""

    id: int
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PasswordChange(BaseModel):
    """Password change request."""

    current_password: str
    new_password: str = Field(..., min_length=8)


class PasswordReset(BaseModel):
    """Password reset request."""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation."""

    token: str
    new_password: str = Field(..., min_length=8)


# --- Token Functions ---


def create_access_token(user_id: int, email: str, role: str) -> str:
    """Create a JWT access token."""
    expires = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "type": "access",
        "exp": expires,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: int) -> str:
    """Create a JWT refresh token."""
    expires = datetime.utcnow() + timedelta(days=settings.jwt_refresh_expire_days)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": expires,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def verify_token(token: str, token_type: str = "access") -> dict:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Neplatný typ tokenu",
            )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token vypršel",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Neplatný token",
        )


# --- Dependencies ---


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Get the current authenticated user from JWT token."""
    payload = verify_token(credentials.credentials, "access")
    user_id = int(payload.get("sub"))

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Uživatel nenalezen",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Účet je deaktivován",
        )

    return user


def get_current_active_user(user: User = Depends(get_current_user)) -> User:
    """Get current user and verify they are active."""
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Neaktivní uživatel",
        )
    return user


def get_admin_user(user: User = Depends(get_current_user)) -> User:
    """Get current user and verify they are admin."""
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Přístup pouze pro administrátory",
        )
    return user


# --- API Endpoints ---


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user account.

    Creates a new user with the provided email and password.
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email je již registrován",
        )

    # Create new user
    user = User(
        email=data.email,
        full_name=data.full_name,
        role=UserRole.USER,
        is_active=True,
        is_verified=False,
    )
    user.set_password(data.password)
    user.generate_verification_token()

    db.add(user)
    db.commit()
    db.refresh(user)

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT tokens.

    Returns access token and refresh token on successful authentication.
    """
    # Find user by email
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Neplatné přihlašovací údaje",
        )

    # Verify password
    if not user.verify_password(data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Neplatné přihlašovací údaje",
        )

    # Check if account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Účet je deaktivován",
        )

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()

    # Create tokens
    access_token = create_access_token(user.id, user.email, user.role.value)
    refresh_token = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """
    Refresh access token using a valid refresh token.
    """
    payload = verify_token(credentials.credentials, "refresh")
    user_id = int(payload.get("sub"))

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Neplatný uživatel",
        )

    # Create new tokens
    access_token = create_access_token(user.id, user.email, user.role.value)
    new_refresh_token = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.jwt_expire_minutes * 60,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    """
    Get current user profile.
    """
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
    )


@router.put("/me", response_model=UserResponse)
async def update_me(
    full_name: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update current user profile.
    """
    if full_name is not None:
        user.full_name = full_name

    db.commit()
    db.refresh(user)

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
    )


@router.post("/change-password")
async def change_password(
    data: PasswordChange,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Change user password.

    Requires current password for verification.
    """
    if not user.verify_password(data.current_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Neplatné současné heslo",
        )

    user.set_password(data.new_password)
    db.commit()

    return {"message": "Heslo bylo úspěšně změněno"}


@router.post("/forgot-password")
async def forgot_password(data: PasswordReset, db: Session = Depends(get_db)):
    """
    Request password reset.

    Generates a reset token (in production, send via email).
    """
    user = db.query(User).filter(User.email == data.email).first()

    # Always return success to prevent email enumeration
    if user:
        token = user.generate_reset_token()
        db.commit()
        # In production: send email with reset link
        # For now, just log it
        print(f"Password reset token for {user.email}: {token}")

    return {"message": "Pokud email existuje, byl odeslán odkaz pro reset hesla"}


@router.post("/reset-password")
async def reset_password(data: PasswordResetConfirm, db: Session = Depends(get_db)):
    """
    Reset password using reset token.
    """
    user = db.query(User).filter(User.reset_token == data.token).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Neplatný nebo expirovaný token",
        )

    # Check if token is expired (24 hours)
    if user.reset_token_expires:
        expires_at = user.reset_token_expires + timedelta(hours=24)
        if datetime.utcnow() > expires_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token vypršel",
            )

    user.set_password(data.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()

    return {"message": "Heslo bylo úspěšně resetováno"}


@router.post("/logout")
async def logout(user: User = Depends(get_current_user)):
    """
    Logout current user.

    Note: With JWT, actual logout is handled client-side by removing the token.
    This endpoint can be used for logging or token blacklisting if implemented.
    """
    # In production, you might want to blacklist the token
    return {"message": "Odhlášení úspěšné"}
