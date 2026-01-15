"""
Transaction model for financial operations.
"""

import enum
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.document import Document


class TransactionType(enum.Enum):
    """Type of financial transaction."""

    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    DIVIDEND = "dividend"
    TAX_PAYMENT = "tax_payment"
    SALARY = "salary"


class Transaction(Base, TimestampMixin):
    """
    Represents a financial transaction.

    Supports multi-currency with automatic CZK conversion.

    Attributes:
        type: Transaction type (income, expense, etc.)
        category: Category for reporting
        amount: Original amount in original currency
        currency: Original currency code (USD, EUR, CZK)
        exchange_rate: Exchange rate to CZK (if applicable)
        amount_czk: Amount converted to CZK
        date: Transaction date
        description: Transaction description
        debit_account: Debit account code (MD)
        credit_account: Credit account code (D)
        source: Source of transaction (manual, appstore, ocr)
    """

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)

    # Transaction details
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    subcategory: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Amounts
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="CZK", nullable=False)
    exchange_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    amount_czk: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Date and description
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Accounting
    debit_account: Mapped[str] = mapped_column(String(10), nullable=False)
    credit_account: Mapped[str] = mapped_column(String(10), nullable=False)

    # Metadata
    source: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)
    external_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Tax related
    is_tax_deductible: Mapped[bool] = mapped_column(default=True)
    vat_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 2), nullable=True)
    vat_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)

    # Relationships
    company: Mapped["Company"] = relationship(back_populates="transactions")
    document_id: Mapped[Optional[int]] = mapped_column(ForeignKey("documents.id"), nullable=True)
    document: Mapped[Optional["Document"]] = relationship(back_populates="transactions")

    def __repr__(self) -> str:
        return f"<Transaction(id={self.id}, type={self.type.value}, amount={self.amount_czk} CZK)>"

    @property
    def is_income(self) -> bool:
        """Check if transaction is income."""
        return self.type in (TransactionType.INCOME, TransactionType.DIVIDEND)

    @property
    def is_expense(self) -> bool:
        """Check if transaction is expense."""
        return self.type in (TransactionType.EXPENSE, TransactionType.TAX_PAYMENT, TransactionType.SALARY)
