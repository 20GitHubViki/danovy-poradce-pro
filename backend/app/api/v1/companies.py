"""
Company API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.company import Company
from app.models.transaction import Transaction
from app.models.invoice import Invoice, InvoiceStatus
from app.models.asset import Asset
from app.schemas.company import (
    CompanyCreate,
    CompanyUpdate,
    CompanyResponse,
    CompanyStats,
)

router = APIRouter()


@router.get("", response_model=list[CompanyResponse])
async def list_companies(
    db: Session = Depends(get_db),
):
    """List all companies."""
    return db.query(Company).all()


@router.post("", response_model=CompanyResponse, status_code=201)
async def create_company(
    data: CompanyCreate,
    db: Session = Depends(get_db),
):
    """Create a new company."""
    # Check if ICO already exists
    existing = db.query(Company).filter(Company.ico == data.ico).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Company with ICO {data.ico} already exists",
        )

    company = Company(**data.model_dump())
    db.add(company)
    db.commit()
    db.refresh(company)

    return company


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: int,
    db: Session = Depends(get_db),
):
    """Get a single company by ID."""
    company = db.query(Company).filter(Company.id == company_id).first()

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    return company


@router.put("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: int,
    data: CompanyUpdate,
    db: Session = Depends(get_db),
):
    """Update an existing company."""
    company = db.query(Company).filter(Company.id == company_id).first()

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(company, field, value)

    db.commit()
    db.refresh(company)

    return company


@router.delete("/{company_id}", status_code=204)
async def delete_company(
    company_id: int,
    db: Session = Depends(get_db),
):
    """Delete a company and all related data."""
    company = db.query(Company).filter(Company.id == company_id).first()

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    db.delete(company)
    db.commit()


@router.get("/{company_id}/stats", response_model=CompanyStats)
async def get_company_stats(
    company_id: int,
    db: Session = Depends(get_db),
):
    """Get statistics for a company."""
    company = db.query(Company).filter(Company.id == company_id).first()

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Calculate totals
    transactions = db.query(Transaction).filter(Transaction.company_id == company_id).all()
    total_income = sum(t.amount_czk for t in transactions if t.is_income)
    total_expenses = sum(t.amount_czk for t in transactions if t.is_expense)

    # Assets
    assets = db.query(Asset).filter(Asset.company_id == company_id, Asset.is_active).all()
    total_assets = sum(a.current_value for a in assets)

    # Invoices
    pending = (
        db.query(Invoice)
        .filter(
            Invoice.company_id == company_id,
            Invoice.status.in_([InvoiceStatus.DRAFT, InvoiceStatus.SENT]),
        )
        .count()
    )
    overdue = (
        db.query(Invoice)
        .filter(
            Invoice.company_id == company_id,
            Invoice.status == InvoiceStatus.OVERDUE,
        )
        .count()
    )

    return CompanyStats(
        total_income=float(total_income),
        total_expenses=float(total_expenses),
        total_assets=float(total_assets),
        pending_invoices=pending,
        overdue_invoices=overdue,
    )
