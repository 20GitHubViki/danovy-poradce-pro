"""
Asset model for company property and depreciation tracking.
"""

import enum
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.company import Company


class AssetCategory(enum.Enum):
    """Asset depreciation category (odpisová skupina)."""

    GROUP_1 = "1"  # 3 roky - počítače, telefony
    GROUP_2 = "2"  # 5 let - auta, nábytek
    GROUP_3 = "3"  # 10 let
    GROUP_4 = "4"  # 20 let
    GROUP_5 = "5"  # 30 let
    GROUP_6 = "6"  # 50 let
    NON_DEPRECIABLE = "non_depreciable"  # Neodpisovaný majetek


class DepreciationMethod(enum.Enum):
    """Depreciation calculation method."""

    LINEAR = "linear"  # Rovnoměrné odpisy
    ACCELERATED = "accelerated"  # Zrychlené odpisy
    IMMEDIATE = "immediate"  # Jednorázový odpis (do 80 000 Kč)


class Asset(Base, TimestampMixin):
    """
    Represents a company asset (long-term property).

    Attributes:
        name: Asset name/description
        category: Depreciation category (1-6)
        acquisition_value: Original purchase price
        acquisition_date: Date of acquisition
        depreciation_method: Method of depreciation
    """

    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)

    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    inventory_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Categorization
    category: Mapped[AssetCategory] = mapped_column(Enum(AssetCategory), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # Values
    acquisition_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    residual_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    accumulated_depreciation: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))

    # Dates
    acquisition_date: Mapped[date] = mapped_column(Date, nullable=False)
    in_use_date: Mapped[date] = mapped_column(Date, nullable=False)
    disposal_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Depreciation settings
    depreciation_method: Mapped[DepreciationMethod] = mapped_column(
        Enum(DepreciationMethod), default=DepreciationMethod.LINEAR
    )
    useful_life_years: Mapped[int] = mapped_column(nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(default=True)

    # Relationships
    company: Mapped["Company"] = relationship(back_populates="assets")
    depreciations: Mapped[list["Depreciation"]] = relationship(
        back_populates="asset",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Asset(id={self.id}, name='{self.name}', value={self.acquisition_value})>"

    @property
    def current_value(self) -> Decimal:
        """Calculate current book value."""
        return self.acquisition_value - self.accumulated_depreciation

    @property
    def is_fully_depreciated(self) -> bool:
        """Check if asset is fully depreciated."""
        return self.accumulated_depreciation >= (self.acquisition_value - self.residual_value)


class Depreciation(Base, TimestampMixin):
    """Yearly depreciation record for an asset."""

    __tablename__ = "depreciations"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False, index=True)

    year: Mapped[int] = mapped_column(nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    accumulated_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    is_tax_depreciation: Mapped[bool] = mapped_column(default=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    asset: Mapped["Asset"] = relationship(back_populates="depreciations")

    def __repr__(self) -> str:
        return f"<Depreciation(asset_id={self.asset_id}, year={self.year}, amount={self.amount})>"
