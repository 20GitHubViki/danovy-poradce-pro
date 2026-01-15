"""
Invoice model for issued and received invoices.
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


class InvoiceType(enum.Enum):
    """Type of invoice."""

    ISSUED = "issued"  # Vydaná faktura
    RECEIVED = "received"  # Přijatá faktura


class InvoiceStatus(enum.Enum):
    """Status of invoice."""

    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class Invoice(Base, TimestampMixin):
    """
    Represents an invoice (issued or received).

    Attributes:
        type: Invoice type (issued/received)
        number: Invoice number
        partner_name: Business partner name
        partner_ico: Partner ICO
        issue_date: Date of issue
        due_date: Due date for payment
        total_amount: Total amount including VAT
    """

    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)

    # Invoice identification
    type: Mapped[InvoiceType] = mapped_column(Enum(InvoiceType), nullable=False)
    number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    variable_symbol: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Partner details
    partner_name: Mapped[str] = mapped_column(String(255), nullable=False)
    partner_ico: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    partner_dic: Mapped[Optional[str]] = mapped_column(String(12), nullable=True)
    partner_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Dates
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    taxable_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    payment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Amounts
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    vat_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="CZK")

    # Status
    status: Mapped[InvoiceStatus] = mapped_column(Enum(InvoiceStatus), default=InvoiceStatus.DRAFT)

    # Description
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Import metadata
    import_source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    company: Mapped["Company"] = relationship(back_populates="invoices")
    items: Mapped[list["InvoiceItem"]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
    )
    document_id: Mapped[Optional[int]] = mapped_column(ForeignKey("documents.id"), nullable=True)
    document: Mapped[Optional["Document"]] = relationship(back_populates="invoices")

    def __repr__(self) -> str:
        return f"<Invoice(id={self.id}, number='{self.number}', total={self.total_amount})>"

    @property
    def is_overdue(self) -> bool:
        """Check if invoice is overdue."""
        if self.status == InvoiceStatus.PAID:
            return False
        return date.today() > self.due_date


class InvoiceItem(Base):
    """Individual item on an invoice."""

    __tablename__ = "invoice_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False)

    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("1"))
    unit: Mapped[str] = mapped_column(String(20), default="ks")
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("21"))
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Relationships
    invoice: Mapped["Invoice"] = relationship(back_populates="items")

    def __repr__(self) -> str:
        return f"<InvoiceItem(id={self.id}, description='{self.description[:30]}...')>"
