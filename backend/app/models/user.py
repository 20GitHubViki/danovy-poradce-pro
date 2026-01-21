"""
User model for authentication and authorization.
"""

import enum
import secrets
from datetime import datetime
from typing import Optional

from passlib.context import CryptContext
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.models.base import Base

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserRole(enum.Enum):
    """User roles for authorization."""

    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class User(Base):
    """User account model."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    # Profile
    full_name = Column(String(255), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)

    # Tokens
    verification_token = Column(String(64), nullable=True)
    reset_token = Column(String(64), nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    companies = relationship("UserCompany", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        """Set the user's password using bcrypt hashing."""
        self.password_hash = pwd_context.hash(password)

    def verify_password(self, password: str) -> bool:
        """Verify a password against the stored hash."""
        return pwd_context.verify(password, self.password_hash)

    def generate_verification_token(self) -> str:
        """Generate a token for email verification."""
        self.verification_token = secrets.token_urlsafe(32)
        return self.verification_token

    def generate_reset_token(self) -> str:
        """Generate a token for password reset."""
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expires = datetime.utcnow()
        return self.reset_token

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}')>"


class UserCompany(Base):
    """Association table for User-Company many-to-many relationship with roles."""

    __tablename__ = "user_companies"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)

    # Role within the company
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="companies")
    company = relationship("Company", back_populates="users")

    def __repr__(self) -> str:
        return f"<UserCompany(user_id={self.user_id}, company_id={self.company_id}, role='{self.role.value}')>"
