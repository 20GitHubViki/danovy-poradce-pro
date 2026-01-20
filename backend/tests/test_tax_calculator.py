"""
Unit tests for TaxCalculator service.

Tests Czech tax calculations for:
- Corporate tax (DPPO)
- Dividend withholding tax
- Personal income tax (DPFO)
- Full profit cycle (corporate + dividend)
- Dividend vs salary comparison
"""

import pytest
from decimal import Decimal
from app.services.tax_calculator import TaxCalculator


class TestTaxCalculator:
    """Test suite for TaxCalculator."""

    @pytest.fixture
    def calculator_2025(self):
        """Get calculator for 2025 tax year."""
        return TaxCalculator(year=2025)

    @pytest.fixture
    def calculator_2026(self):
        """Get calculator for 2026 tax year."""
        return TaxCalculator(year=2026)


class TestCorporateTax(TestTaxCalculator):
    """Tests for corporate tax calculations."""

    def test_corporate_tax_basic(self, calculator_2025):
        """Test basic corporate tax calculation."""
        result = calculator_2025.calculate_corporate_tax(Decimal("1000000"))

        assert result.profit_before_tax == Decimal("1000000")
        assert result.corporate_tax == Decimal("210000")  # 21%
        assert result.profit_after_tax == Decimal("790000")
        assert result.effective_rate == Decimal("0.21")

    def test_corporate_tax_small_amount(self, calculator_2025):
        """Test corporate tax with small amount."""
        result = calculator_2025.calculate_corporate_tax(Decimal("100000"))

        assert result.corporate_tax == Decimal("21000")
        assert result.profit_after_tax == Decimal("79000")

    def test_corporate_tax_zero_profit(self, calculator_2025):
        """Test corporate tax with zero profit."""
        result = calculator_2025.calculate_corporate_tax(Decimal("0"))

        assert result.corporate_tax == Decimal("0")
        assert result.profit_after_tax == Decimal("0")
        assert result.effective_rate == Decimal("0")

    def test_corporate_tax_negative_profit(self, calculator_2025):
        """Test corporate tax with loss (negative profit)."""
        result = calculator_2025.calculate_corporate_tax(Decimal("-100000"))

        assert result.corporate_tax == Decimal("0")
        assert result.profit_after_tax == Decimal("-100000")
        assert result.effective_rate == Decimal("0")

    def test_corporate_tax_rounding(self, calculator_2025):
        """Test that corporate tax is rounded to whole CZK."""
        result = calculator_2025.calculate_corporate_tax(Decimal("123456"))

        # 123456 * 0.21 = 25925.76 -> rounded to 25926
        assert result.corporate_tax == Decimal("25926")


class TestDividendTax(TestTaxCalculator):
    """Tests for dividend withholding tax calculations."""

    def test_dividend_tax_basic(self, calculator_2025):
        """Test basic dividend tax calculation."""
        result = calculator_2025.calculate_dividend_tax(Decimal("790000"))

        assert result.gross_dividend == Decimal("790000")
        assert result.withholding_tax == Decimal("118500")  # 15%
        assert result.net_dividend == Decimal("671500")

    def test_dividend_tax_zero(self, calculator_2025):
        """Test dividend tax with zero amount."""
        result = calculator_2025.calculate_dividend_tax(Decimal("0"))

        assert result.withholding_tax == Decimal("0")
        assert result.net_dividend == Decimal("0")

    def test_dividend_tax_negative(self, calculator_2025):
        """Test dividend tax with negative amount."""
        result = calculator_2025.calculate_dividend_tax(Decimal("-100000"))

        assert result.withholding_tax == Decimal("0")
        assert result.net_dividend == Decimal("-100000")

    def test_dividend_tax_rounding(self, calculator_2025):
        """Test that dividend tax is rounded correctly."""
        result = calculator_2025.calculate_dividend_tax(Decimal("333333"))

        # 333333 * 0.15 = 49999.95 -> rounded to 50000
        assert result.withholding_tax == Decimal("50000")


class TestFullCycle(TestTaxCalculator):
    """Tests for full profit cycle (corporate + dividend)."""

    def test_full_cycle_1m(self, calculator_2025):
        """Test full cycle with 1M profit."""
        result = calculator_2025.calculate_full_cycle(Decimal("1000000"))

        # Corporate tax: 1000000 * 0.21 = 210000
        assert result.corporate_tax == Decimal("210000")
        assert result.profit_after_tax == Decimal("790000")

        # Dividend tax: 790000 * 0.15 = 118500
        assert result.dividend_withholding == Decimal("118500")
        assert result.net_dividend == Decimal("671500")

        # Total tax: 210000 + 118500 = 328500
        assert result.total_tax == Decimal("328500")

        # Effective rate: 328500 / 1000000 = 0.3285
        assert result.effective_rate == Decimal("0.3285")

    def test_full_cycle_effective_rate(self, calculator_2025):
        """Test that effective rate is approximately 32.85%."""
        result = calculator_2025.calculate_full_cycle(Decimal("500000"))

        # The combined rate should be around 32.85% (21% + 15% of remaining 79%)
        # 21% + (79% * 15%) = 21% + 11.85% = 32.85%
        assert float(result.effective_rate) == pytest.approx(0.3285, rel=0.01)

    def test_full_cycle_zero_profit(self, calculator_2025):
        """Test full cycle with zero profit."""
        result = calculator_2025.calculate_full_cycle(Decimal("0"))

        assert result.corporate_tax == Decimal("0")
        assert result.dividend_withholding == Decimal("0")
        assert result.net_dividend == Decimal("0")
        assert result.effective_rate == Decimal("0")


class TestSalaryTax(TestTaxCalculator):
    """Tests for salary/personal income tax calculations."""

    def test_salary_basic(self, calculator_2025):
        """Test basic salary tax calculation."""
        result = calculator_2025.calculate_salary_tax(Decimal("50000"))

        # Social: 50000 * 0.065 = 3250
        assert result.social_insurance == Decimal("3250")

        # Health: 50000 * 0.045 = 2250
        assert result.health_insurance == Decimal("2250")

        # Income tax: 50000 * 0.15 = 7500
        assert result.income_tax == Decimal("7500")

        # No solidarity tax for 50000
        assert result.solidarity_tax == Decimal("0")

        # Net: 50000 - 3250 - 2250 - 7500 = 37000
        assert result.net_salary == Decimal("37000")

    def test_salary_employer_cost(self, calculator_2025):
        """Test employer cost calculation."""
        result = calculator_2025.calculate_salary_tax(Decimal("50000"))

        # Employer social: 50000 * 0.248 = 12400
        # Employer health: 50000 * 0.09 = 4500
        # Total employer cost: 50000 + 12400 + 4500 = 66900
        assert result.employer_cost == Decimal("66900")

    def test_salary_with_solidarity_tax(self, calculator_2025):
        """Test salary above solidarity threshold."""
        # Monthly salary that would exceed annual threshold
        high_salary = Decimal("200000")  # Monthly

        result = calculator_2025.calculate_salary_tax(high_salary, other_income=Decimal("1800000"))

        # With 1.8M other income + 200k this month, we're over threshold
        assert result.solidarity_tax > Decimal("0")

    def test_salary_zero(self, calculator_2025):
        """Test salary tax with zero amount."""
        result = calculator_2025.calculate_salary_tax(Decimal("0"))

        assert result.social_insurance == Decimal("0")
        assert result.health_insurance == Decimal("0")
        assert result.income_tax == Decimal("0")
        assert result.net_salary == Decimal("0")
        assert result.employer_cost == Decimal("0")

    def test_salary_max_social_base(self, calculator_2025):
        """Test that social insurance respects maximum base."""
        # Very high salary that exceeds max base
        high_salary = Decimal("3000000")

        result = calculator_2025.calculate_salary_tax(high_salary)

        # Social insurance should be capped at max base
        max_base = Decimal("2110416")
        expected_social = (max_base * Decimal("0.065")).quantize(Decimal("1"))
        assert result.social_insurance == expected_social


class TestDividendVsSalary(TestTaxCalculator):
    """Tests for dividend vs salary comparison."""

    def test_comparison_basic(self, calculator_2025):
        """Test basic dividend vs salary comparison."""
        result = calculator_2025.compare_dividend_vs_salary(Decimal("500000"))

        assert "dividend" in result
        assert "salary" in result
        assert "recommendation" in result

        # Both should have net amounts
        assert "net_amount" in result["dividend"]
        assert "net_amount" in result["salary"]

    def test_comparison_recommendation(self, calculator_2025):
        """Test that comparison provides a recommendation."""
        result = calculator_2025.compare_dividend_vs_salary(Decimal("500000"))

        assert result["recommendation"]["better_option"] in ["dividend", "salary"]
        assert "savings" in result["recommendation"]
        assert "reasoning" in result["recommendation"]

    def test_comparison_effective_rates(self, calculator_2025):
        """Test that effective rates are calculated."""
        result = calculator_2025.compare_dividend_vs_salary(Decimal("500000"))

        assert "effective_rate" in result["dividend"]
        assert "effective_rate" in result["salary"]

        # Both rates should be positive
        assert result["dividend"]["effective_rate"] > 0
        assert result["salary"]["effective_rate"] > 0

    def test_comparison_with_other_income(self, calculator_2025):
        """Test comparison with other income affecting solidarity tax."""
        result_no_other = calculator_2025.compare_dividend_vs_salary(
            Decimal("500000"), other_income=Decimal("0")
        )
        result_high_other = calculator_2025.compare_dividend_vs_salary(
            Decimal("500000"), other_income=Decimal("2000000")
        )

        # With high other income, salary should be less favorable
        # because of solidarity tax
        salary_rate_no_other = result_no_other["salary"]["effective_rate"]
        salary_rate_high_other = result_high_other["salary"]["effective_rate"]

        assert salary_rate_high_other > salary_rate_no_other


class TestTaxRates(TestTaxCalculator):
    """Tests for tax rates by year."""

    def test_rates_2025(self, calculator_2025):
        """Test 2025 tax rates are correctly loaded."""
        rates = calculator_2025.rates

        assert rates.corporate_tax == Decimal("0.21")
        assert rates.dividend_withholding == Decimal("0.15")
        assert rates.personal_tax_base == Decimal("0.15")
        assert rates.personal_tax_solidarity == Decimal("0.23")

    def test_rates_2026(self, calculator_2026):
        """Test 2026 tax rates are correctly loaded."""
        rates = calculator_2026.rates

        assert rates.corporate_tax == Decimal("0.21")
        assert rates.dividend_withholding == Decimal("0.15")

    def test_fallback_to_2025_for_unknown_year(self):
        """Test that unknown years fall back to 2025 rates."""
        calculator = TaxCalculator(year=2030)

        # Should fall back to 2025 rates
        assert calculator.rates.corporate_tax == Decimal("0.21")


class TestEdgeCases(TestTaxCalculator):
    """Tests for edge cases and boundary conditions."""

    def test_very_small_amounts(self, calculator_2025):
        """Test calculations with very small amounts."""
        result = calculator_2025.calculate_corporate_tax(Decimal("1"))

        # Should still calculate correctly
        assert result.corporate_tax >= Decimal("0")

    def test_very_large_amounts(self, calculator_2025):
        """Test calculations with very large amounts."""
        result = calculator_2025.calculate_full_cycle(Decimal("100000000"))

        # Should handle large numbers
        assert result.net_dividend > Decimal("0")
        assert result.total_tax > Decimal("0")

    def test_decimal_precision(self, calculator_2025):
        """Test that decimal precision is maintained."""
        result = calculator_2025.calculate_corporate_tax(Decimal("123456.789"))

        # Result should be rounded to whole CZK
        assert result.corporate_tax == result.corporate_tax.quantize(Decimal("1"))
