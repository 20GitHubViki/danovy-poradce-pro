"""
Tax calculation and optimization API endpoints.
"""

from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.report import TaxProjection, DividendAnalysis

router = APIRouter()


class TaxCalculationRequest(BaseModel):
    """Request for tax calculation."""

    profit_before_tax: Decimal = Field(..., ge=0)
    year: int = Field(default=2025)
    include_dividend: bool = True


class DividendVsSalaryRequest(BaseModel):
    """Request for dividend vs salary analysis."""

    available_profit: Decimal = Field(..., ge=0)
    other_income: Decimal = Field(default=Decimal("0"), ge=0)
    year: int = Field(default=2025)


# Tax rates for different years
TAX_RATES = {
    2025: {
        "corporate_tax": Decimal("0.21"),
        "dividend_withholding": Decimal("0.15"),
        "personal_tax_base": Decimal("0.15"),
        "personal_tax_solidarity": Decimal("0.23"),
        "solidarity_threshold": Decimal("1935552"),  # 4x average wage
        "social_insurance_rate": Decimal("0.065"),
        "health_insurance_rate": Decimal("0.045"),
        "social_insurance_max": Decimal("2110416"),
    },
    2026: {
        "corporate_tax": Decimal("0.21"),
        "dividend_withholding": Decimal("0.15"),
        "personal_tax_base": Decimal("0.15"),
        "personal_tax_solidarity": Decimal("0.23"),
        "solidarity_threshold": Decimal("2000000"),
        "social_insurance_rate": Decimal("0.065"),
        "health_insurance_rate": Decimal("0.045"),
        "social_insurance_max": Decimal("2200000"),
    },
}


@router.post("/calculate", response_model=TaxProjection)
async def calculate_tax(request: TaxCalculationRequest):
    """
    Calculate corporate tax and dividend distribution.

    Returns detailed breakdown of taxes and net amounts.
    """
    rates = TAX_RATES.get(request.year, TAX_RATES[2025])

    # Corporate tax
    corporate_tax = request.profit_before_tax * rates["corporate_tax"]
    net_profit = request.profit_before_tax - corporate_tax

    # Dividend withholding
    if request.include_dividend:
        dividend_withholding = net_profit * rates["dividend_withholding"]
        net_dividend = net_profit - dividend_withholding
    else:
        dividend_withholding = Decimal("0")
        net_dividend = net_profit

    # Calculate effective rate
    total_tax = corporate_tax + dividend_withholding
    effective_rate = (
        total_tax / request.profit_before_tax if request.profit_before_tax else Decimal("0")
    )

    notes = []
    if effective_rate > Decimal("0.30"):
        notes.append(
            "Efektivní sazba je vysoká. Zvažte optimalizaci pomocí DPP/DPČ."
        )
    if net_profit > Decimal("500000"):
        notes.append("Při vyšším zisku zvažte rezervy na budoucí investice.")

    return TaxProjection(
        year=request.year,
        estimated_profit=request.profit_before_tax,
        corporate_tax=corporate_tax,
        corporate_tax_rate=rates["corporate_tax"],
        net_profit=net_profit,
        dividend_withholding=dividend_withholding,
        dividend_withholding_rate=rates["dividend_withholding"],
        net_dividend=net_dividend,
        effective_tax_rate=effective_rate,
        notes=notes,
    )


@router.post("/dividend-vs-salary", response_model=DividendAnalysis)
async def analyze_dividend_vs_salary(request: DividendVsSalaryRequest):
    """
    Analyze optimal payout: dividend vs salary (DPP/DPČ).

    Compares total tax burden for both scenarios.
    """
    rates = TAX_RATES.get(request.year, TAX_RATES[2025])
    profit = request.available_profit

    # === DIVIDEND SCENARIO ===
    # Corporate tax already paid, calculate withholding only
    div_corporate_tax = profit * rates["corporate_tax"]
    div_after_corporate = profit - div_corporate_tax
    div_withholding = div_after_corporate * rates["dividend_withholding"]
    div_net = div_after_corporate - div_withholding
    div_total_tax = div_corporate_tax + div_withholding
    div_effective = div_total_tax / profit if profit else Decimal("0")

    # === SALARY SCENARIO (DPP - Dohoda o provedení práce) ===
    # Simplified - assumes under 10k/month limit for DPP
    # Above that, use DPČ which has different rules

    # For simplicity, calculate as if paying out as salary
    # Employee portion
    salary_gross = profit  # Assume all profit goes to salary

    # Social and health insurance (employee portion)
    salary_social = salary_gross * rates["social_insurance_rate"]
    salary_health = salary_gross * rates["health_insurance_rate"]

    # Tax base
    tax_base = salary_gross

    # Income tax (simplified - 15% base rate)
    salary_income_tax = tax_base * rates["personal_tax_base"]

    # Check solidarity tax
    if tax_base > rates["solidarity_threshold"]:
        excess = tax_base - rates["solidarity_threshold"]
        salary_income_tax += excess * (
            rates["personal_tax_solidarity"] - rates["personal_tax_base"]
        )

    # Net salary
    salary_net = salary_gross - salary_social - salary_health - salary_income_tax

    # Employer cost (simplified)
    employer_social = salary_gross * Decimal("0.248")  # 24.8%
    employer_health = salary_gross * Decimal("0.09")  # 9%
    salary_total_cost = salary_gross + employer_social + employer_health

    # Effective rate for salary
    salary_total_tax = salary_income_tax + salary_social + salary_health
    salary_effective = salary_total_tax / salary_gross if salary_gross else Decimal("0")

    # === RECOMMENDATION ===
    if div_effective < salary_effective:
        recommended = "dividend"
        reasoning = (
            f"Dividenda je výhodnější. Efektivní sazba {div_effective:.1%} vs "
            f"{salary_effective:.1%} u výplaty mzdy."
        )
        savings = (salary_total_tax - div_total_tax)
    else:
        recommended = "salary"
        reasoning = (
            f"Výplata mzdy je výhodnější. Efektivní sazba {salary_effective:.1%} vs "
            f"{div_effective:.1%} u dividendy."
        )
        savings = (div_total_tax - salary_total_tax)

    # Consider other income
    if request.other_income > rates["solidarity_threshold"]:
        reasoning += (
            " Pozor: máte další příjmy překračující hranici pro solidární daň."
        )

    return DividendAnalysis(
        profit_before_tax=profit,
        dividend_corporate_tax=div_corporate_tax,
        dividend_withholding=div_withholding,
        dividend_net=div_net,
        dividend_total_tax=div_total_tax,
        dividend_effective_rate=div_effective,
        salary_gross=salary_gross,
        salary_social_insurance=salary_social,
        salary_health_insurance=salary_health,
        salary_income_tax=salary_income_tax,
        salary_net=salary_net,
        salary_total_cost=salary_total_cost,
        salary_effective_rate=salary_effective,
        recommended=recommended,
        reasoning=reasoning,
        potential_savings=savings,
    )


@router.get("/deadlines")
async def get_tax_deadlines(year: Optional[int] = None):
    """Get important tax deadlines for the year."""
    from datetime import date

    year = year or date.today().year

    deadlines = [
        {
            "name": "Přiznání k dani z příjmů PO",
            "date": f"{year + 1}-04-01",
            "description": "Termín pro podání přiznání k dani z příjmů právnických osob",
        },
        {
            "name": "Přiznání k dani z příjmů PO (daňový poradce)",
            "date": f"{year + 1}-07-01",
            "description": "Prodloužený termín při zpracování daňovým poradcem",
        },
        {
            "name": "Záloha na daň z příjmů - Q1",
            "date": f"{year}-03-15",
            "description": "Čtvrtletní záloha na daň z příjmů",
        },
        {
            "name": "Záloha na daň z příjmů - Q2",
            "date": f"{year}-06-15",
            "description": "Čtvrtletní záloha na daň z příjmů",
        },
        {
            "name": "Záloha na daň z příjmů - Q3",
            "date": f"{year}-09-15",
            "description": "Čtvrtletní záloha na daň z příjmů",
        },
        {
            "name": "Záloha na daň z příjmů - Q4",
            "date": f"{year}-12-15",
            "description": "Čtvrtletní záloha na daň z příjmů",
        },
        {
            "name": "Přiznání k DPH (měsíční)",
            "date": "25. den následujícího měsíce",
            "description": "Měsíční přiznání k DPH pro plátce",
        },
    ]

    return {"year": year, "deadlines": deadlines}


@router.get("/rates/{year}")
async def get_tax_rates(year: int):
    """Get tax rates for a specific year."""
    rates = TAX_RATES.get(year)

    if not rates:
        raise HTTPException(
            status_code=404,
            detail=f"Tax rates for year {year} not available",
        )

    return {
        "year": year,
        "rates": {k: float(v) for k, v in rates.items()},
    }
