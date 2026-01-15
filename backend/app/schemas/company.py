"""
Company schemas for API validation.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class CompanyBase(BaseModel):
    """Base schema for company data."""

    name: str = Field(..., min_length=1, max_length=255)
    ico: str = Field(..., pattern="^[0-9]{8}$")
    dic: Optional[str] = Field(None, max_length=12)
    address: str = Field(..., min_length=1)
    bank_account: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    website: Optional[str] = Field(None, max_length=255)
    is_vat_payer: bool = False
    accounting_type: str = Field(default="podvojne", pattern="^(podvojne|danove_evidence)$")

    @field_validator("ico")
    @classmethod
    def validate_ico(cls, v: str) -> str:
        """Validate Czech ICO checksum."""
        if len(v) != 8:
            raise ValueError("IČO musí mít 8 číslic")
        # ICO checksum validation
        weights = [8, 7, 6, 5, 4, 3, 2]
        checksum = sum(int(v[i]) * weights[i] for i in range(7))
        remainder = checksum % 11
        expected = (11 - remainder) % 10
        if int(v[7]) != expected:
            raise ValueError("Neplatné IČO - kontrolní součet nesouhlasí")
        return v


class CompanyCreate(CompanyBase):
    """Schema for creating a company."""

    pass


class CompanyUpdate(BaseModel):
    """Schema for updating a company."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    dic: Optional[str] = Field(None, max_length=12)
    address: Optional[str] = Field(None, min_length=1)
    bank_account: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    website: Optional[str] = Field(None, max_length=255)
    is_vat_payer: Optional[bool] = None
    accounting_type: Optional[str] = Field(None, pattern="^(podvojne|danove_evidence)$")


class CompanyResponse(CompanyBase):
    """Schema for company response."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CompanyStats(BaseModel):
    """Company statistics summary."""

    total_income: float
    total_expenses: float
    total_assets: float
    pending_invoices: int
    overdue_invoices: int
