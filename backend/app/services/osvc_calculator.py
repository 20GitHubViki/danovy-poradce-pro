"""
OSVČ Tax Calculator Service.

Provides calculations for:
- DPFO (Daňové přiznání fyzické osoby) - Personal Income Tax
- VZP (Zdravotní pojištění) - Health Insurance
- ČSSZ (Sociální pojištění) - Social Security
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List
from datetime import date

from app.models.osvc import TaxYear, IncomeEntry, TaxRuleset, ComputationResult, ExpenseMode


@dataclass
class DPFOResult:
    """Income tax calculation result."""

    total_income: Decimal
    expenses: Decimal
    profit: Decimal  # Základ daně
    tax_base: Decimal  # Upravený základ daně
    tax_before_credits: Decimal
    tax_credits: Decimal
    tax_due: Decimal
    effective_rate: Decimal  # Efektivní sazba


@dataclass
class VZPResult:
    """Health insurance calculation result."""

    profit: Decimal
    assessment_base: Decimal  # Vyměřovací základ
    contribution: Decimal  # Pojistné
    monthly_advance: Decimal  # Měsíční záloha


@dataclass
class CSSZResult:
    """Social security calculation result."""

    profit: Decimal
    threshold: Decimal  # Rozhodná částka
    above_threshold: bool
    assessment_base: Decimal  # Vyměřovací základ
    contribution: Decimal  # Pojistné
    monthly_advance: Decimal  # Měsíční záloha


@dataclass
class FullCalculationResult:
    """Complete tax calculation result."""

    # Income
    total_income: Decimal
    total_expenses: Decimal
    profit: Decimal

    # Individual results
    dpfo: DPFOResult
    vzp: VZPResult
    cssz: CSSZResult

    # Totals
    total_tax_due: Decimal
    total_insurance_due: Decimal
    total_due: Decimal

    # Metadata
    ruleset_version: str
    included_entries: int


class OSVCCalculator:
    """
    Calculator for OSVČ tax obligations.

    Supports:
    - Paušální výdaje (flat-rate expenses)
    - OSVČ vedlejší (secondary self-employment)
    - OSVČ hlavní (primary self-employment)
    """

    def __init__(self, ruleset: TaxRuleset):
        """Initialize calculator with tax ruleset."""
        self.ruleset = ruleset

    def _get_expense_rate_and_cap(self, mode: ExpenseMode) -> tuple[Decimal, Decimal]:
        """Get expense rate and cap for given mode."""
        rates = {
            ExpenseMode.PAUSAL_60: (self.ruleset.expense_rate_60, self.ruleset.expense_cap_60),
            ExpenseMode.PAUSAL_40: (self.ruleset.expense_rate_40, self.ruleset.expense_cap_40),
            ExpenseMode.PAUSAL_30: (self.ruleset.expense_rate_30, self.ruleset.expense_cap_30),
            ExpenseMode.PAUSAL_80: (self.ruleset.expense_rate_80, self.ruleset.expense_cap_80),
            ExpenseMode.ACTUAL: (Decimal("0"), Decimal("0")),  # Actual expenses - no rate
        }
        return rates.get(mode, (Decimal("0.60"), Decimal("2000000")))

    def _round_czk(self, amount: Decimal) -> Decimal:
        """Round to whole CZK."""
        return amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)

    def calculate_expenses(
        self,
        total_income: Decimal,
        mode: ExpenseMode,
        actual_expenses: Optional[Decimal] = None,
    ) -> Decimal:
        """
        Calculate expenses based on mode.

        For paušální výdaje: min(income × rate, cap)
        For actual: provided actual_expenses
        """
        if mode == ExpenseMode.ACTUAL:
            return actual_expenses or Decimal("0")

        rate, cap = self._get_expense_rate_and_cap(mode)
        calculated = total_income * rate
        return min(calculated, cap)

    def calculate_dpfo(
        self,
        total_income: Decimal,
        expenses: Decimal,
        apply_basic_credit: bool = True,
    ) -> DPFOResult:
        """
        Calculate personal income tax (DPFO).

        Args:
            total_income: Total income in CZK
            expenses: Total expenses in CZK
            apply_basic_credit: Apply basic tax credit (sleva na poplatníka)

        Returns:
            DPFOResult with all tax details
        """
        # Základ daně (profit)
        profit = total_income - expenses
        profit = max(profit, Decimal("0"))

        # Upravený základ daně (rounded down to 100 CZK)
        tax_base = (profit // 100) * 100

        # Calculate tax
        threshold = self.ruleset.income_tax_threshold
        base_rate = self.ruleset.income_tax_rate
        high_rate = self.ruleset.income_tax_rate_high

        if tax_base <= threshold:
            tax_before_credits = tax_base * base_rate
        else:
            # Progressive taxation
            tax_below = threshold * base_rate
            tax_above = (tax_base - threshold) * high_rate
            tax_before_credits = tax_below + tax_above

        tax_before_credits = self._round_czk(tax_before_credits)

        # Apply credits
        tax_credits = Decimal("0")
        if apply_basic_credit:
            tax_credits = self.ruleset.tax_credit_basic

        tax_due = max(tax_before_credits - tax_credits, Decimal("0"))

        # Effective rate
        effective_rate = (tax_due / profit * 100) if profit > 0 else Decimal("0")

        return DPFOResult(
            total_income=total_income,
            expenses=expenses,
            profit=profit,
            tax_base=tax_base,
            tax_before_credits=tax_before_credits,
            tax_credits=tax_credits,
            tax_due=tax_due,
            effective_rate=effective_rate.quantize(Decimal("0.01")),
        )

    def calculate_vzp(self, profit: Decimal) -> VZPResult:
        """
        Calculate health insurance (VZP) contribution.

        Vyměřovací základ = 50% of profit
        Pojistné = 13.5% of assessment base

        Args:
            profit: Taxable profit (základ daně)

        Returns:
            VZPResult with health insurance details
        """
        # Assessment base = 50% of profit
        assessment_base = profit * self.ruleset.health_base_rate
        assessment_base = self._round_czk(assessment_base)

        # Apply minimum if set
        if self.ruleset.health_min_base and assessment_base < self.ruleset.health_min_base:
            assessment_base = self.ruleset.health_min_base

        # Contribution = 13.5% of assessment base
        contribution = assessment_base * self.ruleset.health_contrib_rate
        contribution = self._round_czk(contribution)

        # Monthly advance
        monthly_advance = self._round_czk(contribution / 12)

        return VZPResult(
            profit=profit,
            assessment_base=assessment_base,
            contribution=contribution,
            monthly_advance=monthly_advance,
        )

    def calculate_cssz(
        self,
        profit: Decimal,
        is_secondary: bool = True,
    ) -> CSSZResult:
        """
        Calculate social security (ČSSZ) contribution.

        For OSVČ vedlejší:
        - Only pay if profit > rozhodná částka (threshold)
        - Vyměřovací základ = 55% of profit
        - Pojistné = 29.2% of assessment base

        Args:
            profit: Taxable profit (základ daně)
            is_secondary: True for OSVČ vedlejší

        Returns:
            CSSZResult with social security details
        """
        threshold = self.ruleset.social_secondary_threshold
        above_threshold = profit > threshold if is_secondary else True

        if not above_threshold:
            # Below threshold - no social security for secondary activity
            return CSSZResult(
                profit=profit,
                threshold=threshold,
                above_threshold=False,
                assessment_base=Decimal("0"),
                contribution=Decimal("0"),
                monthly_advance=Decimal("0"),
            )

        # Assessment base = 55% of profit
        assessment_base = profit * self.ruleset.social_base_rate
        assessment_base = self._round_czk(assessment_base)

        # Apply minimum if set
        if self.ruleset.social_min_base and assessment_base < self.ruleset.social_min_base:
            assessment_base = self.ruleset.social_min_base

        # Contribution = 29.2% of assessment base
        contribution = assessment_base * self.ruleset.social_contrib_rate
        contribution = self._round_czk(contribution)

        # Monthly advance
        monthly_advance = self._round_czk(contribution / 12)

        return CSSZResult(
            profit=profit,
            threshold=threshold,
            above_threshold=True,
            assessment_base=assessment_base,
            contribution=contribution,
            monthly_advance=monthly_advance,
        )

    def calculate_full(
        self,
        tax_year: TaxYear,
        income_entries: List[IncomeEntry],
        actual_expenses: Optional[Decimal] = None,
    ) -> FullCalculationResult:
        """
        Perform full tax calculation for a tax year.

        Args:
            tax_year: Tax year configuration
            income_entries: List of income entries
            actual_expenses: Total actual expenses (if using ACTUAL mode)

        Returns:
            FullCalculationResult with all calculations
        """
        # Sum all income
        total_income = sum(
            entry.amount_czk for entry in income_entries
        )
        total_income = Decimal(str(total_income)) if total_income else Decimal("0")

        # Calculate expenses
        expenses = self.calculate_expenses(
            total_income,
            tax_year.expenses_mode,
            actual_expenses,
        )

        # Profit
        profit = total_income - expenses

        # Calculate individual components
        dpfo = self.calculate_dpfo(total_income, expenses)
        vzp = self.calculate_vzp(profit)
        cssz = self.calculate_cssz(profit, tax_year.is_osvc_secondary)

        # Totals
        total_tax_due = dpfo.tax_due
        total_insurance_due = vzp.contribution + cssz.contribution
        total_due = total_tax_due + total_insurance_due

        return FullCalculationResult(
            total_income=total_income,
            total_expenses=expenses,
            profit=profit,
            dpfo=dpfo,
            vzp=vzp,
            cssz=cssz,
            total_tax_due=total_tax_due,
            total_insurance_due=total_insurance_due,
            total_due=total_due,
            ruleset_version=self.ruleset.version,
            included_entries=len(income_entries),
        )


def get_default_ruleset(year: int) -> TaxRuleset:
    """
    Get default tax ruleset for a given year.

    Creates an in-memory ruleset with standard Czech tax parameters.
    """
    # 2025 default values
    ruleset = TaxRuleset(
        year=year,
        version="1.0",
        # Expense rates
        expense_rate_60=Decimal("0.60"),
        expense_cap_60=Decimal("2000000"),
        expense_rate_40=Decimal("0.40"),
        expense_cap_40=Decimal("800000"),
        expense_rate_30=Decimal("0.30"),
        expense_cap_30=Decimal("600000"),
        expense_rate_80=Decimal("0.80"),
        expense_cap_80=Decimal("1600000"),
        # Health insurance
        health_base_rate=Decimal("0.50"),
        health_contrib_rate=Decimal("0.135"),
        # Social insurance
        social_base_rate=Decimal("0.55"),
        social_contrib_rate=Decimal("0.292"),
        social_secondary_threshold=Decimal("105520"),  # 2025 value
        # Income tax
        income_tax_rate=Decimal("0.15"),
        income_tax_rate_high=Decimal("0.23"),
        income_tax_threshold=Decimal("1582812"),  # 36× average wage
        tax_credit_basic=Decimal("30840"),  # Basic credit for taxpayer
        effective_from=date(year, 1, 1),
    )
    return ruleset


def create_computation_result(
    tax_year: TaxYear,
    ruleset: TaxRuleset,
    result: FullCalculationResult,
) -> ComputationResult:
    """
    Create a ComputationResult model from calculation result.

    Args:
        tax_year: Tax year being calculated
        ruleset: Ruleset used for calculation
        result: Calculation result

    Returns:
        ComputationResult ready for database storage
    """
    return ComputationResult(
        tax_year_id=tax_year.id,
        ruleset_id=ruleset.id,
        total_income=result.total_income,
        total_expenses=result.total_expenses,
        profit=result.profit,
        health_base=result.vzp.assessment_base,
        health_due=result.vzp.contribution,
        social_threshold_hit=result.cssz.above_threshold,
        social_base=result.cssz.assessment_base,
        social_due=result.cssz.contribution,
        income_tax_base=result.dpfo.tax_base,
        income_tax_before_credits=result.dpfo.tax_before_credits,
        income_tax_credits=result.dpfo.tax_credits,
        income_tax_due=result.dpfo.tax_due,
        total_due=result.total_due,
        included_entries=result.included_entries,
    )
