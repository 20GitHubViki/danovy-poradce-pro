"""
Reports and dashboard API endpoints.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, extract

from app.database import get_db
from app.models.company import Company
from app.models.transaction import Transaction, TransactionType
from app.models.invoice import Invoice, InvoiceStatus
from app.schemas.report import (
    DashboardResponse,
    CashFlowEntry,
    TaxProjection,
    RecommendationItem,
    ProfitLossReport,
)

router = APIRouter()


@router.get("/dashboard/{company_id}", response_model=DashboardResponse)
async def get_dashboard(
    company_id: int,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    Get dashboard data for a company.

    Includes YTD figures, cash flow, and AI recommendations.
    """
    year = year or date.today().year

    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Get transactions for the year
    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.company_id == company_id,
            extract("year", Transaction.date) == year,
        )
        .all()
    )

    # Calculate YTD figures
    income_ytd = sum(t.amount_czk for t in transactions if t.is_income)
    expenses_ytd = sum(t.amount_czk for t in transactions if t.is_expense)
    profit_ytd = income_ytd - expenses_ytd

    # Get last year for growth calculation
    last_year_income = sum(
        t.amount_czk
        for t in db.query(Transaction)
        .filter(
            Transaction.company_id == company_id,
            extract("year", Transaction.date) == year - 1,
        )
        .all()
        if t.is_income
    )
    income_growth = (
        ((income_ytd - last_year_income) / last_year_income * 100)
        if last_year_income
        else 0
    )

    # Tax estimation (simplified)
    corporate_tax_rate = Decimal("0.21")
    estimated_tax = max(profit_ytd * corporate_tax_rate, Decimal("0"))

    # Calculate monthly cash flow
    cash_flow = []
    for month in range(1, 13):
        month_trans = [t for t in transactions if t.date.month == month]
        income = sum(t.amount_czk for t in month_trans if t.is_income)
        expenses = sum(t.amount_czk for t in month_trans if t.is_expense)
        cash_flow.append(
            CashFlowEntry(
                month=f"{year}-{month:02d}",
                income=income,
                expenses=expenses,
                balance=income - expenses,
            )
        )

    # Invoice stats
    pending_invoices = (
        db.query(Invoice)
        .filter(
            Invoice.company_id == company_id,
            Invoice.status.in_([InvoiceStatus.DRAFT, InvoiceStatus.SENT]),
        )
        .all()
    )
    overdue_invoices = (
        db.query(Invoice)
        .filter(
            Invoice.company_id == company_id,
            Invoice.status != InvoiceStatus.PAID,
            Invoice.due_date < date.today(),
        )
        .all()
    )

    # Generate recommendations (placeholder - AI will enhance this)
    recommendations = _generate_recommendations(
        income_ytd, expenses_ytd, profit_ytd, len(overdue_invoices)
    )

    return DashboardResponse(
        income_ytd=income_ytd,
        income_growth=float(income_growth),
        expenses_ytd=expenses_ytd,
        profit_ytd=profit_ytd,
        estimated_tax=estimated_tax,
        tax_deadline=date(year + 1, 4, 1),  # April 1st next year
        tax_paid_ytd=sum(
            t.amount_czk for t in transactions if t.type == TransactionType.TAX_PAYMENT
        ),
        cash_flow=cash_flow,
        current_balance=sum(cf.balance for cf in cash_flow),
        pending_invoices_count=len(pending_invoices),
        pending_invoices_amount=sum(i.total_amount for i in pending_invoices),
        overdue_invoices_count=len(overdue_invoices),
        overdue_invoices_amount=sum(i.total_amount for i in overdue_invoices),
        recommendations=recommendations,
    )


@router.get("/profit-loss/{company_id}", response_model=ProfitLossReport)
async def get_profit_loss(
    company_id: int,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Generate Profit & Loss report for a company."""
    year = year or date.today().year
    period_start = date(year, 1, 1)
    period_end = date(year, 12, 31)

    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.company_id == company_id,
            Transaction.date >= period_start,
            Transaction.date <= period_end,
        )
        .all()
    )

    # Group by category (simplified)
    revenue_sales = sum(
        t.amount_czk for t in transactions if t.category == "Prodej" and t.is_income
    )
    revenue_services = sum(
        t.amount_czk for t in transactions if t.category == "Služby" and t.is_income
    )
    revenue_other = sum(
        t.amount_czk
        for t in transactions
        if t.is_income and t.category not in ["Prodej", "Služby"]
    )
    revenue_total = revenue_sales + revenue_services + revenue_other

    expenses_materials = sum(
        t.amount_czk for t in transactions if t.category == "Materiál" and t.is_expense
    )
    expenses_services = sum(
        t.amount_czk
        for t in transactions
        if t.category == "Externí služby" and t.is_expense
    )
    expenses_personnel = sum(
        t.amount_czk for t in transactions if t.category == "Mzdy" and t.is_expense
    )
    expenses_depreciation = sum(
        t.amount_czk for t in transactions if t.category == "Odpisy" and t.is_expense
    )
    expenses_other = sum(
        t.amount_czk
        for t in transactions
        if t.is_expense
        and t.category not in ["Materiál", "Externí služby", "Mzdy", "Odpisy"]
    )
    expenses_total = (
        expenses_materials
        + expenses_services
        + expenses_personnel
        + expenses_depreciation
        + expenses_other
    )

    operating_profit = revenue_total - expenses_total
    profit_before_tax = operating_profit  # Simplified
    income_tax = max(profit_before_tax * Decimal("0.21"), Decimal("0"))
    net_profit = profit_before_tax - income_tax

    return ProfitLossReport(
        period_start=period_start,
        period_end=period_end,
        revenue_sales=revenue_sales,
        revenue_services=revenue_services,
        revenue_other=revenue_other,
        revenue_total=revenue_total,
        expenses_materials=expenses_materials,
        expenses_services=expenses_services,
        expenses_personnel=expenses_personnel,
        expenses_depreciation=expenses_depreciation,
        expenses_other=expenses_other,
        expenses_total=expenses_total,
        operating_profit=operating_profit,
        financial_income=Decimal("0"),
        financial_expenses=Decimal("0"),
        profit_before_tax=profit_before_tax,
        income_tax=income_tax,
        net_profit=net_profit,
    )


def _generate_recommendations(
    income: Decimal,
    expenses: Decimal,
    profit: Decimal,
    overdue_count: int,
) -> list[RecommendationItem]:
    """Generate basic recommendations based on financial data."""
    recommendations = []

    if overdue_count > 0:
        recommendations.append(
            RecommendationItem(
                category="accounting",
                priority="high",
                title="Nezaplacené faktury",
                message=f"Máte {overdue_count} faktur po splatnosti. Zkontrolujte platby.",
                action_required=True,
            )
        )

    if profit > 0:
        # Tax optimization recommendation
        potential_dividend = profit * Decimal("0.79")  # After 21% corporate tax
        net_after_dividend = potential_dividend * Decimal("0.85")  # After 15% withholding

        recommendations.append(
            RecommendationItem(
                category="tax",
                priority="medium",
                title="Daňová optimalizace",
                message=f"Při aktuálním zisku {profit:,.0f} Kč zvažte optimální formu výplaty.",
                potential_savings=profit * Decimal("0.05"),
            )
        )

    if income > 2_000_000:
        recommendations.append(
            RecommendationItem(
                category="compliance",
                priority="medium",
                title="Kontrola DPH",
                message="Blížíte se k hranici pro povinnou registraci k DPH (2M Kč).",
                action_required=True,
            )
        )

    return recommendations
