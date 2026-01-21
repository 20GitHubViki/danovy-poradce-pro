"""
OSVČ (Self-Employed) models for tax year management and income tracking.
"""

import enum
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Enum, ForeignKey, Numeric, Text
from sqlalchemy.orm import relationship

from app.models.base import Base


class ExpenseMode(enum.Enum):
    """Expense calculation modes for OSVČ."""

    PAUSAL_60 = "pausal_60"  # 60% paušál - for sales, App Store
    PAUSAL_40 = "pausal_40"  # 40% paušál - for services
    PAUSAL_30 = "pausal_30"  # 30% paušál - for rentals
    PAUSAL_80 = "pausal_80"  # 80% paušál - for agricultural
    ACTUAL = "actual"  # Skutečné výdaje - actual documented expenses


class IncomeSource(enum.Enum):
    """Sources of income for OSVČ."""

    APPSTORE_PAID = "appstore_paid"  # App Store - paid apps
    APPSTORE_SUB = "appstore_sub"  # App Store - subscriptions
    APPSTORE_IAP = "appstore_iap"  # App Store - in-app purchases
    AFFILIATE = "affiliate"  # Affiliate income
    FREELANCE = "freelance"  # Freelance/consulting
    OTHER = "other"  # Other income


class TaxYear(Base):
    """
    Tax year configuration for OSVČ.

    Stores year-specific settings like employment status,
    expense mode, and start month for partial-year calculations.
    """

    __tablename__ = "tax_years"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Year settings
    year = Column(Integer, nullable=False, index=True)
    is_employed = Column(Boolean, default=True, nullable=False)  # Is user also employed?
    is_osvc_secondary = Column(Boolean, default=True, nullable=False)  # OSVČ vedlejší?
    start_month = Column(Integer, default=1, nullable=False)  # 1-12, for partial year

    # Expense mode
    expenses_mode = Column(Enum(ExpenseMode), default=ExpenseMode.PAUSAL_60, nullable=False)

    # Notes
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User")
    income_entries = relationship("IncomeEntry", back_populates="tax_year", cascade="all, delete-orphan")
    computation_results = relationship("ComputationResult", back_populates="tax_year", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<TaxYear(id={self.id}, year={self.year}, user_id={self.user_id})>"


class IncomeEntry(Base):
    """
    Individual income entry for OSVČ.

    Tracks payouts from various sources (App Store, affiliate, etc.)
    with support for multi-currency and FX conversion.
    """

    __tablename__ = "income_entries"

    id = Column(Integer, primary_key=True, index=True)
    tax_year_id = Column(Integer, ForeignKey("tax_years.id", ondelete="CASCADE"), nullable=False)

    # Source classification
    source = Column(Enum(IncomeSource), default=IncomeSource.APPSTORE_PAID, nullable=False)

    # Dates
    payout_date = Column(Date, nullable=False, index=True)
    period_start = Column(Date, nullable=True)  # Period this payout covers
    period_end = Column(Date, nullable=True)

    # Amounts
    currency = Column(String(3), default="CZK", nullable=False)  # ISO 4217
    amount_gross = Column(Numeric(12, 2), nullable=False)  # Gross amount
    amount_net = Column(Numeric(12, 2), nullable=True)  # Net received (after fees)
    platform_fees = Column(Numeric(12, 2), nullable=True)  # Platform fees (Apple 15-30%)

    # FX conversion
    fx_rate = Column(Numeric(10, 4), nullable=True)  # FX rate to CZK if not CZK
    amount_czk = Column(Numeric(12, 2), nullable=False)  # Final amount in CZK

    # Metadata
    notes = Column(Text, nullable=True)
    reference = Column(String(255), nullable=True)  # External reference (invoice #, etc.)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tax_year = relationship("TaxYear", back_populates="income_entries")

    def __repr__(self) -> str:
        return f"<IncomeEntry(id={self.id}, source={self.source.value}, amount_czk={self.amount_czk})>"


class TaxRuleset(Base):
    """
    Tax ruleset with year-specific parameters.

    Stores tax rates, caps, and thresholds for each tax year.
    Multiple versions can exist for a year (for corrections/updates).
    """

    __tablename__ = "tax_rulesets"

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False, index=True)
    version = Column(String(20), default="1.0", nullable=False)

    # Expense rates and caps
    expense_rate_60 = Column(Numeric(4, 2), default=0.60, nullable=False)
    expense_cap_60 = Column(Numeric(12, 2), default=2000000, nullable=False)
    expense_rate_40 = Column(Numeric(4, 2), default=0.40, nullable=False)
    expense_cap_40 = Column(Numeric(12, 2), default=800000, nullable=False)
    expense_rate_30 = Column(Numeric(4, 2), default=0.30, nullable=False)
    expense_cap_30 = Column(Numeric(12, 2), default=600000, nullable=False)
    expense_rate_80 = Column(Numeric(4, 2), default=0.80, nullable=False)
    expense_cap_80 = Column(Numeric(12, 2), default=1600000, nullable=False)

    # Health insurance (VZP)
    health_base_rate = Column(Numeric(4, 2), default=0.50, nullable=False)
    health_contrib_rate = Column(Numeric(5, 3), default=0.135, nullable=False)
    health_min_base = Column(Numeric(12, 2), nullable=True)  # Minimum assessment base

    # Social insurance (ČSSZ)
    social_base_rate = Column(Numeric(4, 2), default=0.55, nullable=False)
    social_contrib_rate = Column(Numeric(5, 3), default=0.292, nullable=False)
    social_secondary_threshold = Column(Numeric(12, 2), default=105520, nullable=False)  # Rozhodná částka
    social_min_base = Column(Numeric(12, 2), nullable=True)  # Minimum assessment base

    # Income tax (DPFO)
    income_tax_rate = Column(Numeric(4, 2), default=0.15, nullable=False)
    income_tax_rate_high = Column(Numeric(4, 2), default=0.23, nullable=False)
    income_tax_threshold = Column(Numeric(12, 2), default=1582812, nullable=False)  # Solidarity threshold
    tax_credit_basic = Column(Numeric(12, 2), default=30840, nullable=False)  # Sleva na poplatníka

    # Metadata
    effective_from = Column(Date, nullable=False)
    description = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<TaxRuleset(id={self.id}, year={self.year}, version={self.version})>"


class ComputationResult(Base):
    """
    Stored computation result for a tax year.

    Captures all calculated values with reference to the ruleset used,
    enabling audit trail and reproducibility.
    """

    __tablename__ = "computation_results"

    id = Column(Integer, primary_key=True, index=True)
    tax_year_id = Column(Integer, ForeignKey("tax_years.id", ondelete="CASCADE"), nullable=False)
    ruleset_id = Column(Integer, ForeignKey("tax_rulesets.id"), nullable=False)

    # Income totals
    total_income = Column(Numeric(12, 2), nullable=False)
    total_expenses = Column(Numeric(12, 2), nullable=False)
    profit = Column(Numeric(12, 2), nullable=False)  # Základ daně

    # Health insurance (VZP)
    health_base = Column(Numeric(12, 2), nullable=False)  # Vyměřovací základ
    health_due = Column(Numeric(12, 2), nullable=False)  # Pojistné

    # Social insurance (ČSSZ)
    social_threshold_hit = Column(Boolean, default=False, nullable=False)  # Above rozhodná částka?
    social_base = Column(Numeric(12, 2), nullable=False)  # Vyměřovací základ
    social_due = Column(Numeric(12, 2), nullable=False)  # Pojistné

    # Income tax (DPFO)
    income_tax_base = Column(Numeric(12, 2), nullable=False)  # Základ daně
    income_tax_before_credits = Column(Numeric(12, 2), nullable=False)  # Daň před slevami
    income_tax_credits = Column(Numeric(12, 2), nullable=False)  # Slevy na dani
    income_tax_due = Column(Numeric(12, 2), nullable=False)  # Výsledná daň

    # Summary
    total_due = Column(Numeric(12, 2), nullable=False)  # Total to pay (tax + insurance)

    # Audit
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    included_entries = Column(Integer, nullable=False)  # Number of income entries included

    # Relationships
    tax_year = relationship("TaxYear", back_populates="computation_results")
    ruleset = relationship("TaxRuleset")

    def __repr__(self) -> str:
        return f"<ComputationResult(id={self.id}, tax_year_id={self.tax_year_id}, total_due={self.total_due})>"
