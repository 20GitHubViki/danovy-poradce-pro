"""
Asset Management API endpoints.

Provides asset CRUD and depreciation calculation.
"""

from datetime import date
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.asset import Asset, Depreciation, AssetCategory, DepreciationMethod as AssetDepreciationMethod
from app.services.depreciation import (
    depreciation_calculator,
    DepreciationGroup,
    DepreciationMethod,
    DepreciationSchedule,
    YearlyDepreciation,
    DEPRECIATION_YEARS,
    get_depreciation_group,
)

router = APIRouter()


# Request/Response Models

class AssetCreate(BaseModel):
    """Request to create a new asset."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    inventory_number: Optional[str] = None
    asset_type: str = Field(..., description="Type of asset (computer, car, etc.)")
    category: str = Field(..., description="Depreciation group (1-6)")
    acquisition_value: float = Field(..., gt=0)
    acquisition_date: date
    in_use_date: date
    depreciation_method: str = Field("linear", description="linear or accelerated")
    residual_value: float = Field(0, ge=0)


class AssetResponse(BaseModel):
    """Asset response model."""

    id: int
    company_id: int
    name: str
    description: Optional[str]
    inventory_number: Optional[str]
    asset_type: str
    category: str
    acquisition_value: float
    residual_value: float
    accumulated_depreciation: float
    current_value: float
    acquisition_date: date
    in_use_date: date
    disposal_date: Optional[date]
    depreciation_method: str
    useful_life_years: int
    is_active: bool
    is_fully_depreciated: bool


class DepreciationYearResponse(BaseModel):
    """Single year depreciation response."""

    year: int
    amount: float
    rate_or_coefficient: float
    accumulated: float
    remaining: float
    is_first_year: bool
    is_final_year: bool


class DepreciationScheduleResponse(BaseModel):
    """Complete depreciation schedule response."""

    acquisition_value: float
    residual_value: float
    depreciation_group: int
    method: str
    start_year: int
    total_depreciation: float
    total_years: int
    yearly_schedule: list[DepreciationYearResponse]
    is_complete: bool


class MethodComparisonResponse(BaseModel):
    """Comparison of depreciation methods."""

    linear_first_year: float
    accelerated_first_year: float
    first_year_difference: float
    recommended_method: str
    linear_schedule: DepreciationScheduleResponse
    accelerated_schedule: DepreciationScheduleResponse


class CategoryInfoResponse(BaseModel):
    """Depreciation category information."""

    group: int
    years: int
    linear_rates: dict
    accelerated_coefficients: dict
    examples: list[str]


# Helper functions

def schedule_to_response(schedule: DepreciationSchedule) -> DepreciationScheduleResponse:
    """Convert schedule to response model."""
    return DepreciationScheduleResponse(
        acquisition_value=float(schedule.acquisition_value),
        residual_value=float(schedule.residual_value),
        depreciation_group=schedule.depreciation_group.value,
        method=schedule.method.value,
        start_year=schedule.start_year,
        total_depreciation=float(schedule.total_depreciation),
        total_years=schedule.total_years,
        yearly_schedule=[
            DepreciationYearResponse(
                year=y.year,
                amount=float(y.depreciation_amount),
                rate_or_coefficient=float(y.rate_or_coefficient),
                accumulated=float(y.accumulated_depreciation),
                remaining=float(y.remaining_value),
                is_first_year=y.is_first_year,
                is_final_year=y.is_final_year,
            )
            for y in schedule.yearly_depreciation
        ],
        is_complete=schedule.is_complete,
    )


# Endpoints

@router.get("/", response_model=list[AssetResponse])
async def list_assets(
    company_id: int = Query(..., description="Company ID"),
    active_only: bool = Query(True, description="Only show active assets"),
    db: Session = Depends(get_db),
):
    """
    List all assets for a company.

    Returns list of assets with current depreciation status.
    """
    query = db.query(Asset).filter(Asset.company_id == company_id)

    if active_only:
        query = query.filter(Asset.is_active == True)

    assets = query.order_by(Asset.acquisition_date.desc()).all()

    return [
        AssetResponse(
            id=a.id,
            company_id=a.company_id,
            name=a.name,
            description=a.description,
            inventory_number=a.inventory_number,
            asset_type=a.asset_type,
            category=a.category.value,
            acquisition_value=float(a.acquisition_value),
            residual_value=float(a.residual_value),
            accumulated_depreciation=float(a.accumulated_depreciation),
            current_value=float(a.current_value),
            acquisition_date=a.acquisition_date,
            in_use_date=a.in_use_date,
            disposal_date=a.disposal_date,
            depreciation_method=a.depreciation_method.value,
            useful_life_years=a.useful_life_years,
            is_active=a.is_active,
            is_fully_depreciated=a.is_fully_depreciated,
        )
        for a in assets
    ]


@router.post("/", response_model=AssetResponse)
async def create_asset(
    company_id: int = Query(..., description="Company ID"),
    asset: AssetCreate = ...,
    db: Session = Depends(get_db),
):
    """
    Create a new asset.

    Validates depreciation category and sets up initial values.
    """
    # Validate category
    try:
        category = AssetCategory(asset.category)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Neplatná odpisová skupina: {asset.category}. Použijte 1-6 nebo 'non_depreciable'.",
        )

    # Validate depreciation method
    try:
        method = AssetDepreciationMethod(asset.depreciation_method)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Neplatná odpisová metoda. Použijte 'linear' nebo 'accelerated'.",
        )

    # Get useful life from category
    if category == AssetCategory.NON_DEPRECIABLE:
        useful_life = 0
    else:
        dep_group = DepreciationGroup(int(category.value))
        useful_life = DEPRECIATION_YEARS[dep_group]

    # Create asset
    db_asset = Asset(
        company_id=company_id,
        name=asset.name,
        description=asset.description,
        inventory_number=asset.inventory_number,
        asset_type=asset.asset_type,
        category=category,
        acquisition_value=Decimal(str(asset.acquisition_value)),
        residual_value=Decimal(str(asset.residual_value)),
        accumulated_depreciation=Decimal("0"),
        acquisition_date=asset.acquisition_date,
        in_use_date=asset.in_use_date,
        depreciation_method=method,
        useful_life_years=useful_life,
        is_active=True,
    )

    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)

    return AssetResponse(
        id=db_asset.id,
        company_id=db_asset.company_id,
        name=db_asset.name,
        description=db_asset.description,
        inventory_number=db_asset.inventory_number,
        asset_type=db_asset.asset_type,
        category=db_asset.category.value,
        acquisition_value=float(db_asset.acquisition_value),
        residual_value=float(db_asset.residual_value),
        accumulated_depreciation=float(db_asset.accumulated_depreciation),
        current_value=float(db_asset.current_value),
        acquisition_date=db_asset.acquisition_date,
        in_use_date=db_asset.in_use_date,
        disposal_date=db_asset.disposal_date,
        depreciation_method=db_asset.depreciation_method.value,
        useful_life_years=db_asset.useful_life_years,
        is_active=db_asset.is_active,
        is_fully_depreciated=db_asset.is_fully_depreciated,
    )


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: int,
    db: Session = Depends(get_db),
):
    """Get a single asset by ID."""
    asset = db.query(Asset).filter(Asset.id == asset_id).first()

    if not asset:
        raise HTTPException(status_code=404, detail="Majetek nenalezen")

    return AssetResponse(
        id=asset.id,
        company_id=asset.company_id,
        name=asset.name,
        description=asset.description,
        inventory_number=asset.inventory_number,
        asset_type=asset.asset_type,
        category=asset.category.value,
        acquisition_value=float(asset.acquisition_value),
        residual_value=float(asset.residual_value),
        accumulated_depreciation=float(asset.accumulated_depreciation),
        current_value=float(asset.current_value),
        acquisition_date=asset.acquisition_date,
        in_use_date=asset.in_use_date,
        disposal_date=asset.disposal_date,
        depreciation_method=asset.depreciation_method.value,
        useful_life_years=asset.useful_life_years,
        is_active=asset.is_active,
        is_fully_depreciated=asset.is_fully_depreciated,
    )


@router.delete("/{asset_id}")
async def dispose_asset(
    asset_id: int,
    disposal_date: date = Query(default_factory=date.today),
    db: Session = Depends(get_db),
):
    """
    Dispose of an asset (mark as inactive).

    Sets disposal date and deactivates the asset.
    """
    asset = db.query(Asset).filter(Asset.id == asset_id).first()

    if not asset:
        raise HTTPException(status_code=404, detail="Majetek nenalezen")

    asset.disposal_date = disposal_date
    asset.is_active = False

    db.commit()

    return {"message": "Majetek vyřazen", "disposal_date": disposal_date}


# Depreciation Calculation Endpoints

@router.get("/calculate/schedule", response_model=DepreciationScheduleResponse)
async def calculate_depreciation_schedule(
    acquisition_value: float = Query(..., gt=0, description="Pořizovací cena"),
    group: int = Query(..., ge=1, le=6, description="Odpisová skupina (1-6)"),
    method: str = Query("linear", description="Metoda: linear nebo accelerated"),
    start_year: int = Query(default_factory=lambda: date.today().year),
    residual_value: float = Query(0, ge=0, description="Zbytková hodnota"),
):
    """
    Calculate depreciation schedule for given parameters.

    Returns complete yearly depreciation schedule.
    """
    try:
        dep_group = DepreciationGroup(group)
        dep_method = DepreciationMethod(method)
    except ValueError:
        raise HTTPException(status_code=400, detail="Neplatné parametry")

    schedule = depreciation_calculator.calculate_schedule(
        Decimal(str(acquisition_value)),
        dep_group,
        dep_method,
        start_year,
        Decimal(str(residual_value)),
    )

    return schedule_to_response(schedule)


@router.get("/calculate/compare", response_model=MethodComparisonResponse)
async def compare_depreciation_methods(
    acquisition_value: float = Query(..., gt=0, description="Pořizovací cena"),
    group: int = Query(..., ge=1, le=6, description="Odpisová skupina (1-6)"),
    start_year: int = Query(default_factory=lambda: date.today().year),
):
    """
    Compare linear vs accelerated depreciation methods.

    Returns schedules for both methods with recommendation.
    """
    try:
        dep_group = DepreciationGroup(group)
    except ValueError:
        raise HTTPException(status_code=400, detail="Neplatná odpisová skupina")

    comparison = depreciation_calculator.compare_methods(
        Decimal(str(acquisition_value)),
        dep_group,
        start_year,
    )

    return MethodComparisonResponse(
        linear_first_year=float(comparison["linear"]["first_year_deduction"]),
        accelerated_first_year=float(comparison["accelerated"]["first_year_deduction"]),
        first_year_difference=float(comparison["first_year_difference"]),
        recommended_method=comparison["recommendation"].value,
        linear_schedule=schedule_to_response(comparison["linear"]["schedule"]),
        accelerated_schedule=schedule_to_response(comparison["accelerated"]["schedule"]),
    )


@router.get("/calculate/can-expense")
async def check_immediate_expense(
    value: float = Query(..., gt=0, description="Hodnota majetku"),
):
    """
    Check if asset can be expensed immediately (drobný majetek).

    Assets under 80,000 CZK can be written off in the year of acquisition.
    """
    can_expense = depreciation_calculator.can_expense_immediately(Decimal(str(value)))
    threshold = float(depreciation_calculator.DEPRECIATION_THRESHOLD)

    return {
        "value": value,
        "threshold": threshold,
        "can_expense_immediately": can_expense,
        "message": (
            f"Majetek lze odepsat jednorázově (hodnota pod {threshold:,.0f} Kč)"
            if can_expense
            else f"Majetek musí být odpisován (hodnota nad {threshold:,.0f} Kč)"
        ),
    }


@router.get("/categories", response_model=list[CategoryInfoResponse])
async def list_depreciation_categories():
    """
    List all depreciation categories with rates and examples.

    Returns information about all 6 depreciation groups.
    """
    from app.services.depreciation import LINEAR_RATES, ACCELERATED_COEFFICIENTS

    examples = {
        1: ["počítače", "telefony", "tiskárny", "software"],
        2: ["automobily", "nábytek", "stroje", "vybavení kanceláře"],
        3: ["klimatizace", "výtahy", "turbíny"],
        4: ["potrubí", "věže", "sloupy"],
        5: ["budovy (kromě výrobních)", "silnice", "mosty"],
        6: ["hotely", "administrativní budovy", "obchodní centra"],
    }

    return [
        CategoryInfoResponse(
            group=i,
            years=DEPRECIATION_YEARS[DepreciationGroup(i)],
            linear_rates={
                "first_year": float(LINEAR_RATES[DepreciationGroup(i)][0]),
                "subsequent_years": float(LINEAR_RATES[DepreciationGroup(i)][1]),
            },
            accelerated_coefficients={
                "first_year": ACCELERATED_COEFFICIENTS[DepreciationGroup(i)][0],
                "subsequent_years": ACCELERATED_COEFFICIENTS[DepreciationGroup(i)][1],
            },
            examples=examples.get(i, []),
        )
        for i in range(1, 7)
    ]


@router.get("/suggest-category")
async def suggest_category(
    asset_type: str = Query(..., description="Typ majetku"),
):
    """
    Suggest depreciation category for an asset type.

    Returns suggested category based on asset type description.
    """
    group = get_depreciation_group(asset_type)

    if group is None:
        return {
            "asset_type": asset_type,
            "suggested_group": None,
            "message": "Nelze automaticky určit odpisovou skupinu. Zkontrolujte přílohu č. 1 zákona o daních z příjmů.",
        }

    return {
        "asset_type": asset_type,
        "suggested_group": group.value,
        "depreciation_years": DEPRECIATION_YEARS[group],
        "message": f"Doporučená odpisová skupina: {group.value} ({DEPRECIATION_YEARS[group]} let)",
    }
