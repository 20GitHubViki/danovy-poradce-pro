"""
Person model for individual (FO) tax tracking.
"""

import enum
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class IncomeType(enum.Enum):
    """Type of personal income."""

    EMPLOYMENT = "employment"  # §6 - příjmy ze závislé činnosti
    BUSINESS = "business"  # §7 - příjmy ze samostatné činnosti
    CAPITAL = "capital"  # §8 - příjmy z kapitálového majetku
    RENTAL = "rental"  # §9 - příjmy z nájmu
    OTHER = "other"  # §10 - ostatní příjmy


class Person(Base, TimestampMixin):
    """
    Represents an individual person for personal tax tracking.

    Used to track income from employment, benefits, and calculate
    personal tax obligations.
    """

    __tablename__ = "persons"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Personal info (encrypted in production)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Tax settings
    tax_residence: Mapped[str] = mapped_column(String(2), default="CZ")
    has_tax_bonus: Mapped[bool] = mapped_column(default=False)  # Sleva na poplatníka
    has_spouse_deduction: Mapped[bool] = mapped_column(default=False)
    children_count: Mapped[int] = mapped_column(default=0)

    # Relationships
    incomes: Mapped[list["PersonIncome"]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Person(id={self.id}, name='{self.name}')>"


class PersonIncome(Base, TimestampMixin):
    """
    Represents an income entry for a person.

    Tracks employment income, benefits, and other income types
    for personal tax calculations.
    """

    __tablename__ = "person_incomes"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"), nullable=False, index=True)

    # Income details
    type: Mapped[IncomeType] = mapped_column(Enum(IncomeType), nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Amounts
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tax_paid: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    social_insurance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    health_insurance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    net_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Period
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    year: Mapped[int] = mapped_column(nullable=False, index=True)

    # Benefits (for employment income)
    benefits_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    benefits_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Employer info (for employment income)
    employer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    employer_ico: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)

    # Relationships
    person: Mapped["Person"] = relationship(back_populates="incomes")

    def __repr__(self) -> str:
        return f"<PersonIncome(id={self.id}, type={self.type.value}, gross={self.gross_amount})>"
