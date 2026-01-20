"""
Depreciation Calculator Service.

Calculates tax depreciation according to Czech tax law (zákon o daních z příjmů).
Supports linear (rovnoměrné) and accelerated (zrychlené) depreciation methods.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Optional


class DepreciationGroup(Enum):
    """Czech tax depreciation groups (odpisové skupiny)."""

    GROUP_1 = 1  # 3 years
    GROUP_2 = 2  # 5 years
    GROUP_3 = 3  # 10 years
    GROUP_4 = 4  # 20 years
    GROUP_5 = 5  # 30 years
    GROUP_6 = 6  # 50 years


class DepreciationMethod(Enum):
    """Depreciation method types."""

    LINEAR = "linear"  # Rovnoměrné odpisy (§31)
    ACCELERATED = "accelerated"  # Zrychlené odpisy (§32)


# Czech tax depreciation rates (2025)
# Source: Zákon č. 586/1992 Sb., o daních z příjmů

# Linear depreciation rates (§31 odst. 1)
# Format: (first_year_rate, subsequent_years_rate)
LINEAR_RATES = {
    DepreciationGroup.GROUP_1: (Decimal("20"), Decimal("40")),  # 3 years
    DepreciationGroup.GROUP_2: (Decimal("11"), Decimal("22.25")),  # 5 years
    DepreciationGroup.GROUP_3: (Decimal("5.5"), Decimal("10.5")),  # 10 years
    DepreciationGroup.GROUP_4: (Decimal("2.15"), Decimal("5.15")),  # 20 years
    DepreciationGroup.GROUP_5: (Decimal("1.4"), Decimal("3.4")),  # 30 years
    DepreciationGroup.GROUP_6: (Decimal("1.02"), Decimal("2.02")),  # 50 years
}

# Accelerated depreciation coefficients (§32 odst. 1)
# Format: (first_year_coef, subsequent_years_coef)
ACCELERATED_COEFFICIENTS = {
    DepreciationGroup.GROUP_1: (3, 4),
    DepreciationGroup.GROUP_2: (5, 6),
    DepreciationGroup.GROUP_3: (10, 11),
    DepreciationGroup.GROUP_4: (20, 21),
    DepreciationGroup.GROUP_5: (30, 31),
    DepreciationGroup.GROUP_6: (50, 51),
}

# Depreciation period in years
DEPRECIATION_YEARS = {
    DepreciationGroup.GROUP_1: 3,
    DepreciationGroup.GROUP_2: 5,
    DepreciationGroup.GROUP_3: 10,
    DepreciationGroup.GROUP_4: 20,
    DepreciationGroup.GROUP_5: 30,
    DepreciationGroup.GROUP_6: 50,
}

# Asset types by category (examples)
ASSET_TYPE_CATEGORIES = {
    "computer": DepreciationGroup.GROUP_1,
    "laptop": DepreciationGroup.GROUP_1,
    "phone": DepreciationGroup.GROUP_1,
    "printer": DepreciationGroup.GROUP_1,
    "car": DepreciationGroup.GROUP_2,
    "furniture": DepreciationGroup.GROUP_2,
    "machinery": DepreciationGroup.GROUP_2,
    "building": DepreciationGroup.GROUP_5,
    "land": None,  # Not depreciable
}


@dataclass
class YearlyDepreciation:
    """Single year depreciation result."""

    year: int
    depreciation_amount: Decimal
    rate_or_coefficient: Decimal
    accumulated_depreciation: Decimal
    remaining_value: Decimal
    is_first_year: bool = False
    is_final_year: bool = False


@dataclass
class DepreciationSchedule:
    """Complete depreciation schedule for an asset."""

    acquisition_value: Decimal
    residual_value: Decimal
    depreciation_group: DepreciationGroup
    method: DepreciationMethod
    start_year: int
    yearly_depreciation: list[YearlyDepreciation] = field(default_factory=list)
    total_depreciation: Decimal = Decimal("0")
    total_years: int = 0

    @property
    def is_complete(self) -> bool:
        """Check if depreciation schedule is complete."""
        return self.total_depreciation >= (self.acquisition_value - self.residual_value)


class DepreciationCalculator:
    """
    Calculator for Czech tax depreciation.

    Supports both linear (rovnoměrné) and accelerated (zrychlené) methods
    according to Czech Income Tax Act (zákon o daních z příjmů).
    """

    # Minimum value for depreciation (lower values can be expensed immediately)
    DEPRECIATION_THRESHOLD = Decimal("80000")  # 80,000 CZK

    def calculate_schedule(
        self,
        acquisition_value: Decimal,
        depreciation_group: DepreciationGroup,
        method: DepreciationMethod,
        start_year: int,
        residual_value: Decimal = Decimal("0"),
        acquisition_month: int = 1,
    ) -> DepreciationSchedule:
        """
        Calculate complete depreciation schedule.

        Args:
            acquisition_value: Original asset value
            depreciation_group: Tax depreciation group (1-6)
            method: LINEAR or ACCELERATED
            start_year: Year depreciation starts
            residual_value: Expected value at end of depreciation
            acquisition_month: Month of acquisition (for half-year convention)

        Returns:
            Complete depreciation schedule
        """
        schedule = DepreciationSchedule(
            acquisition_value=acquisition_value,
            residual_value=residual_value,
            depreciation_group=depreciation_group,
            method=method,
            start_year=start_year,
        )

        depreciable_base = acquisition_value - residual_value
        remaining = depreciable_base
        accumulated = Decimal("0")
        year = start_year
        years_depreciated = 0
        max_years = DEPRECIATION_YEARS[depreciation_group]

        while remaining > 0 and years_depreciated < max_years + 2:
            is_first = years_depreciated == 0

            if method == DepreciationMethod.LINEAR:
                amount, rate = self._calculate_linear(
                    acquisition_value, depreciation_group, is_first
                )
            else:
                amount, rate = self._calculate_accelerated(
                    acquisition_value, remaining, depreciation_group,
                    is_first, years_depreciated
                )

            # Ensure we don't depreciate below residual value
            if amount > remaining:
                amount = remaining

            # Round to 2 decimal places (standard Czech rounding)
            amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            accumulated += amount
            remaining = depreciable_base - accumulated

            yearly = YearlyDepreciation(
                year=year,
                depreciation_amount=amount,
                rate_or_coefficient=rate,
                accumulated_depreciation=accumulated,
                remaining_value=remaining if remaining > 0 else Decimal("0"),
                is_first_year=is_first,
                is_final_year=remaining <= 0,
            )
            schedule.yearly_depreciation.append(yearly)

            year += 1
            years_depreciated += 1

            if remaining <= 0:
                break

        schedule.total_depreciation = accumulated
        schedule.total_years = years_depreciated

        return schedule

    def _calculate_linear(
        self,
        acquisition_value: Decimal,
        group: DepreciationGroup,
        is_first_year: bool,
    ) -> tuple[Decimal, Decimal]:
        """
        Calculate linear depreciation amount.

        Formula: acquisition_value * rate / 100
        """
        rates = LINEAR_RATES[group]
        rate = rates[0] if is_first_year else rates[1]
        amount = acquisition_value * rate / 100
        return amount, rate

    def _calculate_accelerated(
        self,
        acquisition_value: Decimal,
        remaining_value: Decimal,
        group: DepreciationGroup,
        is_first_year: bool,
        years_depreciated: int,
    ) -> tuple[Decimal, Decimal]:
        """
        Calculate accelerated depreciation amount.

        First year formula: acquisition_value / first_year_coefficient
        Subsequent years: 2 * remaining_value / (subsequent_coef - years_depreciated)
        """
        coefficients = ACCELERATED_COEFFICIENTS[group]

        if is_first_year:
            coef = Decimal(str(coefficients[0]))
            amount = acquisition_value / coef
        else:
            coef = Decimal(str(coefficients[1]))
            divisor = coef - years_depreciated
            if divisor <= 0:
                divisor = Decimal("1")
            amount = (2 * remaining_value) / divisor

        return amount, coef

    def calculate_yearly_depreciation(
        self,
        acquisition_value: Decimal,
        depreciation_group: DepreciationGroup,
        method: DepreciationMethod,
        year_number: int,
        remaining_value: Optional[Decimal] = None,
    ) -> YearlyDepreciation:
        """
        Calculate depreciation for a single year.

        Args:
            acquisition_value: Original asset value
            depreciation_group: Tax depreciation group
            method: LINEAR or ACCELERATED
            year_number: Which year of depreciation (1-based)
            remaining_value: Current remaining value (required for accelerated)

        Returns:
            Single year depreciation result
        """
        is_first = year_number == 1

        if remaining_value is None:
            # Estimate remaining value for accelerated
            if method == DepreciationMethod.ACCELERATED:
                # Simple estimate - actual would need accumulated depreciation
                remaining_value = acquisition_value

        if method == DepreciationMethod.LINEAR:
            amount, rate = self._calculate_linear(
                acquisition_value, depreciation_group, is_first
            )
        else:
            amount, rate = self._calculate_accelerated(
                acquisition_value, remaining_value, depreciation_group,
                is_first, year_number - 1
            )

        amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return YearlyDepreciation(
            year=year_number,
            depreciation_amount=amount,
            rate_or_coefficient=rate,
            accumulated_depreciation=Decimal("0"),  # Would need history
            remaining_value=remaining_value - amount if remaining_value else Decimal("0"),
            is_first_year=is_first,
        )

    def can_expense_immediately(self, value: Decimal) -> bool:
        """
        Check if asset can be expensed immediately (drobný majetek).

        Assets under 80,000 CZK can be written off immediately.
        """
        return value < self.DEPRECIATION_THRESHOLD

    def suggest_method(
        self,
        acquisition_value: Decimal,
        depreciation_group: DepreciationGroup,
        expected_profit_trend: str = "stable",
    ) -> DepreciationMethod:
        """
        Suggest optimal depreciation method.

        Args:
            acquisition_value: Asset value
            depreciation_group: Tax depreciation group
            expected_profit_trend: "increasing", "decreasing", or "stable"

        Returns:
            Recommended depreciation method
        """
        # Accelerated gives higher deductions in early years
        # Better when profits are expected to be higher now
        if expected_profit_trend == "decreasing":
            return DepreciationMethod.ACCELERATED

        # Linear is simpler and better for stable/increasing profits
        if expected_profit_trend == "increasing":
            return DepreciationMethod.LINEAR

        # For stable profits, compare total tax impact
        # Generally accelerated provides slight advantage due to time value
        if depreciation_group in [DepreciationGroup.GROUP_1, DepreciationGroup.GROUP_2]:
            # Shorter depreciation periods - accelerated is often better
            return DepreciationMethod.ACCELERATED

        # Longer periods - linear is simpler
        return DepreciationMethod.LINEAR

    def compare_methods(
        self,
        acquisition_value: Decimal,
        depreciation_group: DepreciationGroup,
        start_year: int,
    ) -> dict:
        """
        Compare linear vs accelerated depreciation.

        Returns schedules and summary for both methods.
        """
        linear = self.calculate_schedule(
            acquisition_value, depreciation_group,
            DepreciationMethod.LINEAR, start_year
        )
        accelerated = self.calculate_schedule(
            acquisition_value, depreciation_group,
            DepreciationMethod.ACCELERATED, start_year
        )

        return {
            "linear": {
                "schedule": linear,
                "first_year_deduction": linear.yearly_depreciation[0].depreciation_amount if linear.yearly_depreciation else Decimal("0"),
                "total_years": linear.total_years,
            },
            "accelerated": {
                "schedule": accelerated,
                "first_year_deduction": accelerated.yearly_depreciation[0].depreciation_amount if accelerated.yearly_depreciation else Decimal("0"),
                "total_years": accelerated.total_years,
            },
            "recommendation": self.suggest_method(acquisition_value, depreciation_group),
            "first_year_difference": (
                accelerated.yearly_depreciation[0].depreciation_amount -
                linear.yearly_depreciation[0].depreciation_amount
            ) if linear.yearly_depreciation and accelerated.yearly_depreciation else Decimal("0"),
        }


# Global calculator instance
depreciation_calculator = DepreciationCalculator()


def get_depreciation_group(asset_type: str) -> Optional[DepreciationGroup]:
    """Get suggested depreciation group for asset type."""
    asset_type_lower = asset_type.lower()
    for key, group in ASSET_TYPE_CATEGORIES.items():
        if key in asset_type_lower:
            return group
    return None


def calculate_depreciation(
    acquisition_value: Decimal,
    group: int,
    method: str,
    start_year: int,
) -> DepreciationSchedule:
    """
    Convenience function for depreciation calculation.

    Args:
        acquisition_value: Asset value in CZK
        group: Depreciation group (1-6)
        method: "linear" or "accelerated"
        start_year: Starting year

    Returns:
        Complete depreciation schedule
    """
    dep_group = DepreciationGroup(group)
    dep_method = DepreciationMethod(method)

    return depreciation_calculator.calculate_schedule(
        acquisition_value, dep_group, dep_method, start_year
    )
