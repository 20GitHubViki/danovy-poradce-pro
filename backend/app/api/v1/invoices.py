"""
Invoice API endpoints.
"""

from datetime import date
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.invoice import Invoice, InvoiceItem, InvoiceType, InvoiceStatus
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceResponse,
    InvoiceList,
)

router = APIRouter()


@router.get("", response_model=InvoiceList)
async def list_invoices(
    company_id: int,
    type: Optional[InvoiceType] = None,
    status: Optional[InvoiceStatus] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List invoices with filtering and pagination."""
    query = db.query(Invoice).filter(Invoice.company_id == company_id)

    if type:
        query = query.filter(Invoice.type == type)
    if status:
        query = query.filter(Invoice.status == status)
    if date_from:
        query = query.filter(Invoice.issue_date >= date_from)
    if date_to:
        query = query.filter(Invoice.issue_date <= date_to)

    total = query.count()
    pages = (total + page_size - 1) // page_size

    items = (
        query.order_by(Invoice.issue_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return InvoiceList(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("", response_model=InvoiceResponse, status_code=201)
async def create_invoice(
    data: InvoiceCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new invoice with items.

    Automatically calculates subtotal, VAT, and total.
    """
    # Create invoice items and calculate totals
    items = []
    subtotal = Decimal("0")

    for item_data in data.items:
        total_price = item_data.quantity * item_data.unit_price
        item = InvoiceItem(
            **item_data.model_dump(),
            total_price=total_price,
        )
        items.append(item)
        subtotal += total_price

    # Calculate VAT (simplified - assumes single rate)
    vat_rate = data.items[0].vat_rate if data.items else Decimal("21")
    vat_amount = subtotal * vat_rate / 100
    total_amount = subtotal + vat_amount

    # Create invoice
    invoice = Invoice(
        **data.model_dump(exclude={"items"}),
        subtotal=subtotal,
        vat_amount=vat_amount,
        total_amount=total_amount,
        items=items,
    )

    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    return invoice


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
):
    """Get a single invoice by ID."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return invoice


@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: int,
    data: InvoiceUpdate,
    db: Session = Depends(get_db),
):
    """Update an existing invoice."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(invoice, field, value)

    db.commit()
    db.refresh(invoice)

    return invoice


@router.delete("/{invoice_id}", status_code=204)
async def delete_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
):
    """Delete an invoice."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    db.delete(invoice)
    db.commit()


@router.post("/{invoice_id}/mark-paid", response_model=InvoiceResponse)
async def mark_invoice_paid(
    invoice_id: int,
    payment_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    """Mark an invoice as paid."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice.status = InvoiceStatus.PAID
    invoice.payment_date = payment_date or date.today()

    db.commit()
    db.refresh(invoice)

    return invoice


@router.get("/overdue/{company_id}")
async def get_overdue_invoices(
    company_id: int,
    db: Session = Depends(get_db),
):
    """Get all overdue invoices for a company."""
    invoices = (
        db.query(Invoice)
        .filter(
            Invoice.company_id == company_id,
            Invoice.status != InvoiceStatus.PAID,
            Invoice.due_date < date.today(),
        )
        .all()
    )

    return {
        "count": len(invoices),
        "total_amount": sum(i.total_amount for i in invoices),
        "invoices": invoices,
    }
