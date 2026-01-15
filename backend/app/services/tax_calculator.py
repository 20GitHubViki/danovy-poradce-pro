"""
Tax calculation service.

Provides accurate tax calculations based on Czech tax law.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional


@dataclass
class TaxRates:
    """Tax rates for a specific year."""

    corporate_tax: Decimal
    dividend_withholding: Decimal
    personal_tax_base: Decimal
    personal_tax_solidarity: Decimal
    solidarity_threshold: Decimal
    social_insurance_employee: Decimal
    social_insurance_employer: Decimal
    health_insurance_employee: Decimal
    health_insurance_employer: Decimal
    social_insurance_max_base: Decimal


# Tax rates by year
RATES_BY_YEAR = {
    2025: TaxRates(
        corporate_tax=Decimal("0.21"),
        dividend_withholding=Decimal("0.15"),
        personal_tax_base=Decimal("0.15"),
        personal_tax_solidarity=Decimal("0.23"),
        solidarity_threshold=Decimal("1935552"),
        social_insurance_employee=Decimal("0.065"),
        social_insurance_employer=Decimal("0.248"),
        health_insurance_employee=Decimal("0.045"),
        health_insurance_employer=Decimal("0.09"),
        social_insurance_max_base=Decimal("2110416"),
    ),
    2026: TaxRates(
        corporate_tax=Decimal("0.21"),
        dividend_withholding=Decimal("0.15"),
        personal_tax_base=Decimal("0.15"),
        personal_tax_solidarity=Decimal("0.23"),
        solidarity_threshold=Decimal("2000000"),
        social_insurance_employee=Decimal("0.065"),
        social_insurance_employer=Decimal("0.248"),
        health_insurance_employee=Decimal("0.045"),
        health_insurance_employer=Decimal("0.09"),
        social_insurance_max_base=Decimal("2200000"),
    ),
}


@dataclass
class CorporateTaxResult:
    """Result of corporate tax calculation."""

    profit_before_tax: Decimal
    corporate_tax: Decimal
    profit_after_tax: Decimal
    effective_rate: Decimal


@dataclass
class DividendTaxResult:
    """Result of dividend tax calculation."""

    gross_dividend: Decimal
    withholding_tax: Decimal
    net_dividend: Decimal


@dataclass
class FullCycleResult:
    """Result of full profit cycle calculation (corporate + dividend)."""

    profit_before_tax: Decimal
    corporate_tax: Decimal
    profit_after_tax: Decimal
    dividend_withholding: Decimal
    net_dividend: Decimal
    total_tax: Decimal
    effective_rate: Decimal


@dataclass
class SalaryTaxResult:
    """Result of salary tax calculation."""

    gross_salary: Decimal
    social_insurance: Decimal
    health_insurance: Decimal
    income_tax: Decimal
    solidarity_tax: Decimal
    net_salary: Decimal
    employer_cost: Decimal
    effective_rate: Decimal


class TaxCalculator:
    """
    Tax calculator for Czech taxes.

    Supports:
    - Corporate tax (DPPO)
    - Dividend withholding tax
    - Personal income tax (DPFO)
    - Social and health insurance
    """

    def __init__(self, year: int = 2025):
        """
        Initialize calculator for specific tax year.

        Args:
            year: Tax year for rate lookup
        """
        self.year = year
        self.rates = RATES_BY_YEAR.get(year, RATES_BY_YEAR[2025])

    def _round_czk(self, amount: Decimal) -> Decimal:
        """Round to whole CZK (standard Czech tax rounding)."""
        return amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)

    def calculate_corporate_tax(self, profit_before_tax: Decimal) -> CorporateTaxResult:
        """
        Calculate corporate income tax (DPPO).

        Args:
            profit_before_tax: Taxable profit before tax

        Returns:
            CorporateTaxResult with calculated values
        """
        if profit_before_tax <= 0:
            return CorporateTaxResult(
                profit_before_tax=profit_before_tax,
                corporate_tax=Decimal("0"),
                profit_after_tax=profit_before_tax,
                effective_rate=Decimal("0"),
            )

        tax = self._round_czk(profit_before_tax * self.rates.corporate_tax)
        after_tax = profit_before_tax - tax
        effective = tax / profit_before_tax

        return CorporateTaxResult(
            profit_before_tax=profit_before_tax,
            corporate_tax=tax,
            profit_after_tax=after_tax,
            effective_rate=effective,
        )

    def calculate_dividend_tax(self, gross_dividend: Decimal) -> DividendTaxResult:
        """
        Calculate dividend withholding tax.

        Args:
            gross_dividend: Dividend amount before withholding

        Returns:
            DividendTaxResult with calculated values
        """
        if gross_dividend <= 0:
            return DividendTaxResult(
                gross_dividend=gross_dividend,
                withholding_tax=Decimal("0"),
                net_dividend=gross_dividend,
            )

        withholding = self._round_czk(gross_dividend * self.rates.dividend_withholding)
        net = gross_dividend - withholding

        return DividendTaxResult(
            gross_dividend=gross_dividend,
            withholding_tax=withholding,
            net_dividend=net,
        )

    def calculate_full_cycle(self, profit_before_tax: Decimal) -> FullCycleResult:
        """
        Calculate full profit cycle: corporate tax -> dividend.

        This represents the total tax burden when extracting profit
        from a company as a dividend.

        Args:
            profit_before_tax: Company profit before corporate tax

        Returns:
            FullCycleResult with complete breakdown
        """
        corporate = self.calculate_corporate_tax(profit_before_tax)
        dividend = self.calculate_dividend_tax(corporate.profit_after_tax)

        total_tax = corporate.corporate_tax + dividend.withholding_tax
        effective = total_tax / profit_before_tax if profit_before_tax > 0 else Decimal("0")

        return FullCycleResult(
            profit_before_tax=profit_before_tax,
            corporate_tax=corporate.corporate_tax,
            profit_after_tax=corporate.profit_after_tax,
            dividend_withholding=dividend.withholding_tax,
            net_dividend=dividend.net_dividend,
            total_tax=total_tax,
            effective_rate=effective,
        )

    def calculate_salary_tax(
        self,
        gross_salary: Decimal,
        other_income: Decimal = Decimal("0"),
    ) -> SalaryTaxResult:
        """
        Calculate personal income tax on salary.

        Args:
            gross_salary: Gross salary amount
            other_income: Other taxable income (for solidarity tax threshold)

        Returns:
            SalaryTaxResult with complete breakdown
        """
        if gross_salary <= 0:
            return SalaryTaxResult(
                gross_salary=gross_salary,
                social_insurance=Decimal("0"),
                health_insurance=Decimal("0"),
                income_tax=Decimal("0"),
                solidarity_tax=Decimal("0"),
                net_salary=gross_salary,
                employer_cost=gross_salary,
                effective_rate=Decimal("0"),
            )

        # Employee insurance contributions
        social_base = min(gross_salary, self.rates.social_insurance_max_base)
        social = self._round_czk(social_base * self.rates.social_insurance_employee)
        health = self._round_czk(gross_salary * self.rates.health_insurance_employee)

        # Tax base (gross salary)
        tax_base = gross_salary

        # Base income tax (15%)
        income_tax = self._round_czk(tax_base * self.rates.personal_tax_base)

        # Solidarity tax (additional 8% above threshold)
        total_income = gross_salary + other_income
        solidarity_tax = Decimal("0")
        if total_income > self.rates.solidarity_threshold:
            excess = total_income - self.rates.solidarity_threshold
            # Only apply to portion of this salary above threshold
            taxable_excess = min(excess, gross_salary)
            solidarity_rate = self.rates.personal_tax_solidarity - self.rates.personal_tax_base
            solidarity_tax = self._round_czk(taxable_excess * solidarity_rate)

        total_tax = income_tax + solidarity_tax

        # Net salary
        net = gross_salary - social - health - total_tax

        # Employer cost
        employer_social = self._round_czk(social_base * self.rates.social_insurance_employer)
        employer_health = self._round_czk(gross_salary * self.rates.health_insurance_employer)
        employer_cost = gross_salary + employer_social + employer_health

        # Effective rate
        effective = (social + health + total_tax) / gross_salary

        return SalaryTaxResult(
            gross_salary=gross_salary,
            social_insurance=social,
            health_insurance=health,
            income_tax=income_tax,
            solidarity_tax=solidarity_tax,
            net_salary=net,
            employer_cost=employer_cost,
            effective_rate=effective,
        )

    def compare_dividend_vs_salary(
        self,
        available_profit: Decimal,
        other_income: Decimal = Decimal("0"),
    ) -> dict:
        """
        Compare dividend vs salary payout options.

        Args:
            available_profit: Profit available for distribution
            other_income: Other personal income (affects solidarity tax)

        Returns:
            Dictionary with comparison of both scenarios
        """
        # Dividend scenario
        dividend_result = self.calculate_full_cycle(available_profit)

        # Salary scenario - what gross salary equals the same employer cost?
        # Simplified: assume profit = employer cost budget
        # In reality, need to solve for gross that results in same cost
        salary_result = self.calculate_salary_tax(available_profit, other_income)

        # Determine better option
        if dividend_result.net_dividend > salary_result.net_salary:
            better = "dividend"
            savings = dividend_result.net_dividend - salary_result.net_salary
        else:
            better = "salary"
            savings = salary_result.net_salary - dividend_result.net_dividend

        return {
            "dividend": {
                "net_amount": dividend_result.net_dividend,
                "total_tax": dividend_result.total_tax,
                "effective_rate": float(dividend_result.effective_rate),
            },
            "salary": {
                "net_amount": salary_result.net_salary,
                "total_tax": (
                    salary_result.social_insurance
                    + salary_result.health_insurance
                    + salary_result.income_tax
                    + salary_result.solidarity_tax
                ),
                "effective_rate": float(salary_result.effective_rate),
                "employer_cost": salary_result.employer_cost,
            },
            "recommendation": {
                "better_option": better,
                "savings": savings,
                "reasoning": (
                    f"Při zisku {available_profit:,.0f} Kč je výhodnější "
                    f"{'dividenda' if better == 'dividend' else 'mzda'}. "
                    f"Úspora: {savings:,.0f} Kč."
                ),
            },
        }
