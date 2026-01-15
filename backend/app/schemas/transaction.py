"""
Transaction schemas for API validation.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator

from app.models.transaction import TransactionType


class TransactionBase(BaseModel):
    """Base schema for transaction data."""

    type: TransactionType
    category: str = Field(..., min_length=1, max_length=100)
    subcategory: Optional[str] = Field(None, max_length=100)
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="CZK", pattern="^[A-Z]{3}$")
    exchange_rate: Optional[Decimal] = Field(None, gt=0)
    date: date
    description: str = Field(..., min_length=1)
    note: Optional[str] = None
    debit_account: str = Field(..., pattern="^[0-9]{3}$")
    credit_account: str = Field(..., pattern="^[0-9]{3}$")
    is_tax_deductible: bool = True
    vat_rate: Optional[Decimal] = Field(None, ge=0, le=100)


class TransactionCreate(TransactionBase):
    """Schema for creating a new transaction."""

    company_id: int
    source: str = Field(default="manual", max_length=50)
    external_id: Optional[str] = Field(None, max_length=100)

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Ensure amount has max 2 decimal places."""
        return round(v, 2)


class TransactionUpdate(BaseModel):
    """Schema for updating a transaction."""

    type: Optional[TransactionType] = None
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    subcategory: Optional[str] = Field(None, max_length=100)
    amount: Optional[Decimal] = Field(None, gt=0)
    currency: Optional[str] = Field(None, pattern="^[A-Z]{3}$")
    exchange_rate: Optional[Decimal] = Field(None, gt=0)
    date: Optional[date] = None
    description: Optional[str] = Field(None, min_length=1)
    note: Optional[str] = None
    is_tax_deductible: Optional[bool] = None
    vat_rate: Optional[Decimal] = Field(None, ge=0, le=100)


class TransactionResponse(TransactionBase):
    """Schema for transaction response."""

    id: int
    company_id: int
    amount_czk: Decimal
    source: str
    external_id: Optional[str]
    vat_amount: Optional[Decimal]
    document_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TransactionList(BaseModel):
    """Schema for paginated transaction list."""

    items: list[TransactionResponse]
    total: int
    page: int
    page_size: int
    pages: int


class TransactionSummary(BaseModel):
    """Summary of transactions for reporting."""

    total_income: Decimal
    total_expenses: Decimal
    net: Decimal
    by_category: dict[str, Decimal]
    by_month: dict[str, Decimal]
