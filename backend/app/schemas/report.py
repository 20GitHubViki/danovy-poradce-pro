"""
Report schemas for dashboard and analytics.
"""

from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class CashFlowEntry(BaseModel):
    """Single entry in cash flow report."""

    month: str
    income: Decimal
    expenses: Decimal
    balance: Decimal


class TaxProjection(BaseModel):
    """Tax projection for the year."""

    year: int
    estimated_profit: Decimal
    corporate_tax: Decimal
    corporate_tax_rate: Decimal = Field(default=Decimal("0.21"))
    net_profit: Decimal
    dividend_withholding: Decimal
    dividend_withholding_rate: Decimal = Field(default=Decimal("0.15"))
    net_dividend: Decimal
    effective_tax_rate: Decimal
    notes: list[str] = Field(default_factory=list)


class RecommendationItem(BaseModel):
    """Single recommendation from AI advisor."""

    category: str  # tax, accounting, compliance, optimization
    priority: str  # high, medium, low
    title: str
    message: str
    potential_savings: Optional[Decimal] = None
    action_required: bool = False
    deadline: Optional[date] = None


class DashboardResponse(BaseModel):
    """Dashboard data for frontend."""

    # Summary numbers
    income_ytd: Decimal
    income_growth: float
    expenses_ytd: Decimal
    profit_ytd: Decimal

    # Tax info
    estimated_tax: Decimal
    tax_deadline: date
    tax_paid_ytd: Decimal

    # Cash flow
    cash_flow: list[CashFlowEntry]
    current_balance: Decimal

    # Invoices
    pending_invoices_count: int
    pending_invoices_amount: Decimal
    overdue_invoices_count: int
    overdue_invoices_amount: Decimal

    # AI Recommendations
    recommendations: list[RecommendationItem]


class ProfitLossReport(BaseModel):
    """Profit and Loss (Income Statement) report."""

    period_start: date
    period_end: date

    # Revenue
    revenue_sales: Decimal
    revenue_services: Decimal
    revenue_other: Decimal
    revenue_total: Decimal

    # Expenses
    expenses_materials: Decimal
    expenses_services: Decimal
    expenses_personnel: Decimal
    expenses_depreciation: Decimal
    expenses_other: Decimal
    expenses_total: Decimal

    # Results
    operating_profit: Decimal
    financial_income: Decimal
    financial_expenses: Decimal
    profit_before_tax: Decimal
    income_tax: Decimal
    net_profit: Decimal


class BalanceSheetReport(BaseModel):
    """Balance sheet report."""

    as_of_date: date

    # Assets
    assets_fixed: Decimal
    assets_current: Decimal
    assets_cash: Decimal
    assets_total: Decimal

    # Liabilities
    liabilities_equity: Decimal
    liabilities_long_term: Decimal
    liabilities_short_term: Decimal
    liabilities_total: Decimal


class DividendAnalysis(BaseModel):
    """Analysis of dividend vs salary payment options."""

    profit_before_tax: Decimal

    # Dividend scenario
    dividend_corporate_tax: Decimal
    dividend_withholding: Decimal
    dividend_net: Decimal
    dividend_total_tax: Decimal
    dividend_effective_rate: Decimal

    # Salary scenario (DPP/DPČ)
    salary_gross: Decimal
    salary_social_insurance: Decimal
    salary_health_insurance: Decimal
    salary_income_tax: Decimal
    salary_net: Decimal
    salary_total_cost: Decimal  # Including employer contributions
    salary_effective_rate: Decimal

    # Recommendation
    recommended: str  # "dividend" or "salary"
    reasoning: str
    potential_savings: Decimal
