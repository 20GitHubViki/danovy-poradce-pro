"""
Company model for s.r.o. entity.
"""

from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.transaction import Transaction
    from app.models.invoice import Invoice
    from app.models.asset import Asset
    from app.models.user import UserCompany


class Company(Base, TimestampMixin):
    """
    Represents a company (s.r.o.) entity.

    Attributes:
        name: Company name
        ico: Company identification number (IČO) - 8 digits
        dic: Tax identification number (DIČ) - optional
        address: Full company address
        bank_account: Primary bank account number
    """

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    ico: Mapped[str] = mapped_column(String(8), unique=True, nullable=False, index=True)
    dic: Mapped[Optional[str]] = mapped_column(String(12), nullable=True)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    bank_account: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Additional info
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Tax settings
    is_vat_payer: Mapped[bool] = mapped_column(default=False)
    accounting_type: Mapped[str] = mapped_column(String(50), default="podvojne")

    # Relationships
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
    )
    invoices: Mapped[list["Invoice"]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
    )
    assets: Mapped[list["Asset"]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
    )
    users: Mapped[list["UserCompany"]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Company(id={self.id}, name='{self.name}', ico='{self.ico}')>"
