"""
Transaction API endpoints.
"""

from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.transaction import Transaction, TransactionType
from app.schemas.transaction import (
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    TransactionList,
)

router = APIRouter()


@router.get("", response_model=TransactionList)
async def list_transactions(
    company_id: int,
    type: Optional[TransactionType] = None,
    category: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    List transactions with filtering and pagination.
    """
    query = db.query(Transaction).filter(Transaction.company_id == company_id)

    if type:
        query = query.filter(Transaction.type == type)
    if category:
        query = query.filter(Transaction.category == category)
    if date_from:
        query = query.filter(Transaction.date >= date_from)
    if date_to:
        query = query.filter(Transaction.date <= date_to)

    total = query.count()
    pages = (total + page_size - 1) // page_size

    items = (
        query.order_by(Transaction.date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return TransactionList(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("", response_model=TransactionResponse, status_code=201)
async def create_transaction(
    data: TransactionCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new transaction.

    Automatically calculates amount_czk based on exchange rate.
    """
    # Calculate CZK amount
    if data.currency == "CZK":
        amount_czk = data.amount
    elif data.exchange_rate:
        amount_czk = data.amount * data.exchange_rate
    else:
        raise HTTPException(
            status_code=400,
            detail="Exchange rate required for non-CZK currency",
        )

    # Calculate VAT if rate provided
    vat_amount = None
    if data.vat_rate:
        vat_amount = amount_czk * data.vat_rate / 100

    transaction = Transaction(
        **data.model_dump(exclude={"vat_rate"}),
        amount_czk=amount_czk,
        vat_amount=vat_amount,
    )

    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    return transaction


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
):
    """Get a single transaction by ID."""
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return transaction


@router.put("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: int,
    data: TransactionUpdate,
    db: Session = Depends(get_db),
):
    """Update an existing transaction."""
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    update_data = data.model_dump(exclude_unset=True)

    # Recalculate CZK amount if amount or exchange rate changed
    if "amount" in update_data or "exchange_rate" in update_data:
        amount = update_data.get("amount", transaction.amount)
        currency = update_data.get("currency", transaction.currency)
        exchange_rate = update_data.get("exchange_rate", transaction.exchange_rate)

        if currency == "CZK":
            update_data["amount_czk"] = amount
        elif exchange_rate:
            update_data["amount_czk"] = amount * exchange_rate

    for field, value in update_data.items():
        setattr(transaction, field, value)

    db.commit()
    db.refresh(transaction)

    return transaction


@router.delete("/{transaction_id}", status_code=204)
async def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
):
    """Delete a transaction."""
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    db.delete(transaction)
    db.commit()


@router.get("/summary/{company_id}")
async def get_transaction_summary(
    company_id: int,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Get transaction summary for a company."""
    query = db.query(Transaction).filter(Transaction.company_id == company_id)

    if year:
        query = query.filter(func.extract("year", Transaction.date) == year)

    transactions = query.all()

    income = sum(t.amount_czk for t in transactions if t.is_income)
    expenses = sum(t.amount_czk for t in transactions if t.is_expense)

    # Group by category
    by_category = {}
    for t in transactions:
        if t.category not in by_category:
            by_category[t.category] = 0
        by_category[t.category] += float(t.amount_czk)

    return {
        "total_income": float(income),
        "total_expenses": float(expenses),
        "net": float(income - expenses),
        "by_category": by_category,
        "transaction_count": len(transactions),
    }
