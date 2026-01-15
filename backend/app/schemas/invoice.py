"""
Invoice schemas for API validation.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field

from app.models.invoice import InvoiceType, InvoiceStatus


class InvoiceItemBase(BaseModel):
    """Base schema for invoice item."""

    description: str = Field(..., min_length=1)
    quantity: Decimal = Field(default=Decimal("1"), gt=0)
    unit: str = Field(default="ks", max_length=20)
    unit_price: Decimal = Field(..., gt=0)
    vat_rate: Decimal = Field(default=Decimal("21"), ge=0, le=100)


class InvoiceItemCreate(InvoiceItemBase):
    """Schema for creating invoice item."""

    pass


class InvoiceItemResponse(InvoiceItemBase):
    """Schema for invoice item response."""

    id: int
    invoice_id: int
    total_price: Decimal

    class Config:
        from_attributes = True


class InvoiceBase(BaseModel):
    """Base schema for invoice."""

    type: InvoiceType
    number: str = Field(..., min_length=1, max_length=50)
    variable_symbol: Optional[str] = Field(None, max_length=20)
    partner_name: str = Field(..., min_length=1, max_length=255)
    partner_ico: Optional[str] = Field(None, pattern="^[0-9]{8}$")
    partner_dic: Optional[str] = Field(None, max_length=12)
    partner_address: Optional[str] = None
    issue_date: date
    due_date: date
    taxable_date: Optional[date] = None
    description: Optional[str] = None
    note: Optional[str] = None
    currency: str = Field(default="CZK", pattern="^[A-Z]{3}$")


class InvoiceCreate(InvoiceBase):
    """Schema for creating an invoice."""

    company_id: int
    items: list[InvoiceItemCreate] = Field(default_factory=list)
    import_source: Optional[str] = None
    external_id: Optional[str] = None


class InvoiceUpdate(BaseModel):
    """Schema for updating an invoice."""

    number: Optional[str] = Field(None, min_length=1, max_length=50)
    variable_symbol: Optional[str] = Field(None, max_length=20)
    partner_name: Optional[str] = Field(None, min_length=1, max_length=255)
    partner_ico: Optional[str] = Field(None, pattern="^[0-9]{8}$")
    partner_dic: Optional[str] = Field(None, max_length=12)
    partner_address: Optional[str] = None
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    taxable_date: Optional[date] = None
    payment_date: Optional[date] = None
    status: Optional[InvoiceStatus] = None
    description: Optional[str] = None
    note: Optional[str] = None


class InvoiceResponse(InvoiceBase):
    """Schema for invoice response."""

    id: int
    company_id: int
    subtotal: Decimal
    vat_amount: Decimal
    total_amount: Decimal
    status: InvoiceStatus
    payment_date: Optional[date]
    import_source: Optional[str]
    external_id: Optional[str]
    document_id: Optional[int]
    items: list[InvoiceItemResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InvoiceList(BaseModel):
    """Schema for paginated invoice list."""

    items: list[InvoiceResponse]
    total: int
    page: int
    page_size: int
    pages: int
