"""
OSVČ (Self-Employed) API endpoints.

Provides endpoints for tax year management, income entry,
and tax calculations for OSVČ individuals.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.osvc import (
    TaxYear,
    IncomeEntry,
    TaxRuleset,
    ComputationResult,
    ExpenseMode,
    IncomeSource,
)
from app.api.v1.auth import get_current_user
from app.services.osvc_calculator import (
    OSVCCalculator,
    get_default_ruleset,
    create_computation_result,
    FullCalculationResult,
)

router = APIRouter()


# --- Pydantic Schemas ---


class TaxYearCreate(BaseModel):
    """Request to create a tax year."""

    year: int = Field(..., ge=2020, le=2030)
    is_employed: bool = True
    is_osvc_secondary: bool = True
    start_month: int = Field(1, ge=1, le=12)
    expenses_mode: ExpenseMode = ExpenseMode.PAUSAL_60
    notes: Optional[str] = None


class TaxYearUpdate(BaseModel):
    """Request to update a tax year."""

    is_employed: Optional[bool] = None
    is_osvc_secondary: Optional[bool] = None
    start_month: Optional[int] = Field(None, ge=1, le=12)
    expenses_mode: Optional[ExpenseMode] = None
    notes: Optional[str] = None


class TaxYearResponse(BaseModel):
    """Tax year response."""

    id: int
    year: int
    is_employed: bool
    is_osvc_secondary: bool
    start_month: int
    expenses_mode: str
    notes: Optional[str]
    created_at: datetime
    income_count: int = 0
    total_income: Decimal = Decimal("0")

    class Config:
        from_attributes = True


class IncomeEntryCreate(BaseModel):
    """Request to create an income entry."""

    source: IncomeSource = IncomeSource.APPSTORE_PAID
    payout_date: date
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    currency: str = "CZK"
    amount_gross: Decimal
    amount_net: Optional[Decimal] = None
    platform_fees: Optional[Decimal] = None
    fx_rate: Optional[Decimal] = None
    amount_czk: Optional[Decimal] = None
    notes: Optional[str] = None
    reference: Optional[str] = None


class IncomeEntryUpdate(BaseModel):
    """Request to update an income entry."""

    source: Optional[IncomeSource] = None
    payout_date: Optional[date] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    currency: Optional[str] = None
    amount_gross: Optional[Decimal] = None
    amount_net: Optional[Decimal] = None
    platform_fees: Optional[Decimal] = None
    fx_rate: Optional[Decimal] = None
    amount_czk: Optional[Decimal] = None
    notes: Optional[str] = None
    reference: Optional[str] = None


class IncomeEntryResponse(BaseModel):
    """Income entry response."""

    id: int
    tax_year_id: int
    source: str
    payout_date: date
    period_start: Optional[date]
    period_end: Optional[date]
    currency: str
    amount_gross: Decimal
    amount_net: Optional[Decimal]
    platform_fees: Optional[Decimal]
    fx_rate: Optional[Decimal]
    amount_czk: Decimal
    notes: Optional[str]
    reference: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class CalculationResponse(BaseModel):
    """Tax calculation response."""

    # Income summary
    total_income: Decimal
    total_expenses: Decimal
    profit: Decimal

    # DPFO
    dpfo_tax_base: Decimal
    dpfo_tax_before_credits: Decimal
    dpfo_tax_credits: Decimal
    dpfo_tax_due: Decimal
    dpfo_effective_rate: Decimal

    # VZP
    vzp_assessment_base: Decimal
    vzp_contribution: Decimal
    vzp_monthly_advance: Decimal

    # CSSZ
    cssz_above_threshold: bool
    cssz_threshold: Decimal
    cssz_assessment_base: Decimal
    cssz_contribution: Decimal
    cssz_monthly_advance: Decimal

    # Totals
    total_tax_due: Decimal
    total_insurance_due: Decimal
    total_due: Decimal

    # Metadata
    ruleset_version: str
    included_entries: int


class CSVImportResult(BaseModel):
    """Result of CSV import."""

    imported: int
    skipped: int
    errors: List[str]


# --- Tax Year Endpoints ---


@router.post("/tax-years", response_model=TaxYearResponse, status_code=status.HTTP_201_CREATED)
async def create_tax_year(
    data: TaxYearCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new tax year for the user."""
    # Check if year already exists for user
    existing = db.query(TaxYear).filter(
        TaxYear.user_id == user.id,
        TaxYear.year == data.year,
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rok {data.year} již existuje",
        )

    tax_year = TaxYear(
        user_id=user.id,
        year=data.year,
        is_employed=data.is_employed,
        is_osvc_secondary=data.is_osvc_secondary,
        start_month=data.start_month,
        expenses_mode=data.expenses_mode,
        notes=data.notes,
    )

    db.add(tax_year)
    db.commit()
    db.refresh(tax_year)

    return TaxYearResponse(
        id=tax_year.id,
        year=tax_year.year,
        is_employed=tax_year.is_employed,
        is_osvc_secondary=tax_year.is_osvc_secondary,
        start_month=tax_year.start_month,
        expenses_mode=tax_year.expenses_mode.value,
        notes=tax_year.notes,
        created_at=tax_year.created_at,
        income_count=0,
        total_income=Decimal("0"),
    )


@router.get("/tax-years", response_model=List[TaxYearResponse])
async def list_tax_years(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all tax years for the user."""
    tax_years = db.query(TaxYear).filter(
        TaxYear.user_id == user.id
    ).order_by(TaxYear.year.desc()).all()

    results = []
    for ty in tax_years:
        income_entries = db.query(IncomeEntry).filter(
            IncomeEntry.tax_year_id == ty.id
        ).all()

        total = sum(e.amount_czk for e in income_entries) if income_entries else Decimal("0")

        results.append(TaxYearResponse(
            id=ty.id,
            year=ty.year,
            is_employed=ty.is_employed,
            is_osvc_secondary=ty.is_osvc_secondary,
            start_month=ty.start_month,
            expenses_mode=ty.expenses_mode.value,
            notes=ty.notes,
            created_at=ty.created_at,
            income_count=len(income_entries),
            total_income=Decimal(str(total)),
        ))

    return results


@router.get("/tax-years/{year_id}", response_model=TaxYearResponse)
async def get_tax_year(
    year_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a specific tax year."""
    tax_year = db.query(TaxYear).filter(
        TaxYear.id == year_id,
        TaxYear.user_id == user.id,
    ).first()

    if not tax_year:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rok nenalezen",
        )

    income_entries = db.query(IncomeEntry).filter(
        IncomeEntry.tax_year_id == tax_year.id
    ).all()

    total = sum(e.amount_czk for e in income_entries) if income_entries else Decimal("0")

    return TaxYearResponse(
        id=tax_year.id,
        year=tax_year.year,
        is_employed=tax_year.is_employed,
        is_osvc_secondary=tax_year.is_osvc_secondary,
        start_month=tax_year.start_month,
        expenses_mode=tax_year.expenses_mode.value,
        notes=tax_year.notes,
        created_at=tax_year.created_at,
        income_count=len(income_entries),
        total_income=Decimal(str(total)),
    )


@router.put("/tax-years/{year_id}", response_model=TaxYearResponse)
async def update_tax_year(
    year_id: int,
    data: TaxYearUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update a tax year."""
    tax_year = db.query(TaxYear).filter(
        TaxYear.id == year_id,
        TaxYear.user_id == user.id,
    ).first()

    if not tax_year:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rok nenalezen",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tax_year, field, value)

    db.commit()
    db.refresh(tax_year)

    income_entries = db.query(IncomeEntry).filter(
        IncomeEntry.tax_year_id == tax_year.id
    ).all()

    total = sum(e.amount_czk for e in income_entries) if income_entries else Decimal("0")

    return TaxYearResponse(
        id=tax_year.id,
        year=tax_year.year,
        is_employed=tax_year.is_employed,
        is_osvc_secondary=tax_year.is_osvc_secondary,
        start_month=tax_year.start_month,
        expenses_mode=tax_year.expenses_mode.value,
        notes=tax_year.notes,
        created_at=tax_year.created_at,
        income_count=len(income_entries),
        total_income=Decimal(str(total)),
    )


@router.delete("/tax-years/{year_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tax_year(
    year_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a tax year and all its income entries."""
    tax_year = db.query(TaxYear).filter(
        TaxYear.id == year_id,
        TaxYear.user_id == user.id,
    ).first()

    if not tax_year:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rok nenalezen",
        )

    db.delete(tax_year)
    db.commit()

    return None


# --- Income Entry Endpoints ---


@router.post("/tax-years/{year_id}/income", response_model=IncomeEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_income_entry(
    year_id: int,
    data: IncomeEntryCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new income entry."""
    tax_year = db.query(TaxYear).filter(
        TaxYear.id == year_id,
        TaxYear.user_id == user.id,
    ).first()

    if not tax_year:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rok nenalezen",
        )

    # Calculate amount_czk if not provided
    amount_czk = data.amount_czk
    if amount_czk is None:
        if data.currency == "CZK":
            amount_czk = data.amount_gross
        elif data.fx_rate:
            amount_czk = data.amount_gross * data.fx_rate
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pro cizí měnu je nutné zadat kurz nebo částku v CZK",
            )

    entry = IncomeEntry(
        tax_year_id=year_id,
        source=data.source,
        payout_date=data.payout_date,
        period_start=data.period_start,
        period_end=data.period_end,
        currency=data.currency,
        amount_gross=data.amount_gross,
        amount_net=data.amount_net,
        platform_fees=data.platform_fees,
        fx_rate=data.fx_rate,
        amount_czk=amount_czk,
        notes=data.notes,
        reference=data.reference,
    )

    db.add(entry)
    db.commit()
    db.refresh(entry)

    return IncomeEntryResponse(
        id=entry.id,
        tax_year_id=entry.tax_year_id,
        source=entry.source.value,
        payout_date=entry.payout_date,
        period_start=entry.period_start,
        period_end=entry.period_end,
        currency=entry.currency,
        amount_gross=entry.amount_gross,
        amount_net=entry.amount_net,
        platform_fees=entry.platform_fees,
        fx_rate=entry.fx_rate,
        amount_czk=entry.amount_czk,
        notes=entry.notes,
        reference=entry.reference,
        created_at=entry.created_at,
    )


@router.get("/tax-years/{year_id}/income", response_model=List[IncomeEntryResponse])
async def list_income_entries(
    year_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all income entries for a tax year."""
    tax_year = db.query(TaxYear).filter(
        TaxYear.id == year_id,
        TaxYear.user_id == user.id,
    ).first()

    if not tax_year:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rok nenalezen",
        )

    entries = db.query(IncomeEntry).filter(
        IncomeEntry.tax_year_id == year_id
    ).order_by(IncomeEntry.payout_date.desc()).all()

    return [
        IncomeEntryResponse(
            id=e.id,
            tax_year_id=e.tax_year_id,
            source=e.source.value,
            payout_date=e.payout_date,
            period_start=e.period_start,
            period_end=e.period_end,
            currency=e.currency,
            amount_gross=e.amount_gross,
            amount_net=e.amount_net,
            platform_fees=e.platform_fees,
            fx_rate=e.fx_rate,
            amount_czk=e.amount_czk,
            notes=e.notes,
            reference=e.reference,
            created_at=e.created_at,
        )
        for e in entries
    ]


@router.delete("/income/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_income_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete an income entry."""
    entry = db.query(IncomeEntry).join(TaxYear).filter(
        IncomeEntry.id == entry_id,
        TaxYear.user_id == user.id,
    ).first()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Záznam nenalezen",
        )

    db.delete(entry)
    db.commit()

    return None


# --- CSV Import ---


@router.post("/tax-years/{year_id}/income/import-csv", response_model=CSVImportResult)
async def import_income_csv(
    year_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Import income entries from CSV file.

    Expected CSV columns:
    - payout_date (YYYY-MM-DD)
    - period_start (optional)
    - period_end (optional)
    - currency
    - amount_gross
    - amount_net (optional)
    - platform_fees (optional)
    - fx_rate (optional)
    - notes (optional)
    """
    tax_year = db.query(TaxYear).filter(
        TaxYear.id == year_id,
        TaxYear.user_id == user.id,
    ).first()

    if not tax_year:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rok nenalezen",
        )

    # Read CSV content
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))

    imported = 0
    skipped = 0
    errors = []

    for i, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
        try:
            # Parse payout date
            payout_date_str = row.get("payout_date") or row.get("Payout Date")
            if not payout_date_str:
                errors.append(f"Řádek {i}: Chybí datum výplaty")
                skipped += 1
                continue

            payout_date = date.fromisoformat(payout_date_str.strip())

            # Parse amounts
            amount_gross_str = row.get("amount_gross") or row.get("Gross") or row.get("gross")
            if not amount_gross_str:
                errors.append(f"Řádek {i}: Chybí hrubá částka")
                skipped += 1
                continue

            amount_gross = Decimal(amount_gross_str.strip().replace(",", "."))

            # Currency
            currency = (row.get("currency") or row.get("Currency") or "CZK").strip().upper()

            # Optional fields
            amount_net = None
            if row.get("amount_net") or row.get("Net"):
                amount_net = Decimal((row.get("amount_net") or row.get("Net")).strip().replace(",", "."))

            platform_fees = None
            if row.get("platform_fees") or row.get("Fees"):
                platform_fees = Decimal((row.get("platform_fees") or row.get("Fees")).strip().replace(",", "."))

            fx_rate = None
            if row.get("fx_rate") or row.get("FX Rate"):
                fx_rate = Decimal((row.get("fx_rate") or row.get("FX Rate")).strip().replace(",", "."))

            # Calculate CZK amount
            if currency == "CZK":
                amount_czk = amount_gross
            elif fx_rate:
                amount_czk = amount_gross * fx_rate
            else:
                errors.append(f"Řádek {i}: Cizí měna bez kurzu")
                skipped += 1
                continue

            # Period dates
            period_start = None
            period_end = None
            if row.get("period_start") or row.get("Period Start"):
                period_start = date.fromisoformat((row.get("period_start") or row.get("Period Start")).strip())
            if row.get("period_end") or row.get("Period End"):
                period_end = date.fromisoformat((row.get("period_end") or row.get("Period End")).strip())

            notes = row.get("notes") or row.get("Notes") or None

            # Check for duplicate (same date and amount)
            existing = db.query(IncomeEntry).filter(
                IncomeEntry.tax_year_id == year_id,
                IncomeEntry.payout_date == payout_date,
                IncomeEntry.amount_gross == amount_gross,
                IncomeEntry.currency == currency,
            ).first()

            if existing:
                skipped += 1
                continue

            # Create entry
            entry = IncomeEntry(
                tax_year_id=year_id,
                source=IncomeSource.APPSTORE_PAID,  # Default for CSV import
                payout_date=payout_date,
                period_start=period_start,
                period_end=period_end,
                currency=currency,
                amount_gross=amount_gross,
                amount_net=amount_net,
                platform_fees=platform_fees,
                fx_rate=fx_rate,
                amount_czk=amount_czk,
                notes=notes,
            )

            db.add(entry)
            imported += 1

        except Exception as e:
            errors.append(f"Řádek {i}: {str(e)}")
            skipped += 1

    db.commit()

    return CSVImportResult(
        imported=imported,
        skipped=skipped,
        errors=errors[:10],  # Limit errors to first 10
    )


# --- Tax Calculations ---


@router.post("/tax-years/{year_id}/calculate", response_model=CalculationResponse)
async def calculate_taxes(
    year_id: int,
    save_result: bool = Query(False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Calculate taxes for a tax year."""
    tax_year = db.query(TaxYear).filter(
        TaxYear.id == year_id,
        TaxYear.user_id == user.id,
    ).first()

    if not tax_year:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rok nenalezen",
        )

    # Get income entries
    income_entries = db.query(IncomeEntry).filter(
        IncomeEntry.tax_year_id == year_id
    ).all()

    # Get or create ruleset
    ruleset = db.query(TaxRuleset).filter(
        TaxRuleset.year == tax_year.year
    ).order_by(TaxRuleset.version.desc()).first()

    if not ruleset:
        ruleset = get_default_ruleset(tax_year.year)
        db.add(ruleset)
        db.commit()
        db.refresh(ruleset)

    # Calculate
    calculator = OSVCCalculator(ruleset)
    result = calculator.calculate_full(tax_year, income_entries)

    # Save result if requested
    if save_result:
        comp_result = create_computation_result(tax_year, ruleset, result)
        db.add(comp_result)
        db.commit()

    return CalculationResponse(
        total_income=result.total_income,
        total_expenses=result.total_expenses,
        profit=result.profit,
        dpfo_tax_base=result.dpfo.tax_base,
        dpfo_tax_before_credits=result.dpfo.tax_before_credits,
        dpfo_tax_credits=result.dpfo.tax_credits,
        dpfo_tax_due=result.dpfo.tax_due,
        dpfo_effective_rate=result.dpfo.effective_rate,
        vzp_assessment_base=result.vzp.assessment_base,
        vzp_contribution=result.vzp.contribution,
        vzp_monthly_advance=result.vzp.monthly_advance,
        cssz_above_threshold=result.cssz.above_threshold,
        cssz_threshold=result.cssz.threshold,
        cssz_assessment_base=result.cssz.assessment_base,
        cssz_contribution=result.cssz.contribution,
        cssz_monthly_advance=result.cssz.monthly_advance,
        total_tax_due=result.total_tax_due,
        total_insurance_due=result.total_insurance_due,
        total_due=result.total_due,
        ruleset_version=result.ruleset_version,
        included_entries=result.included_entries,
    )


# --- Exports ---


@router.get("/tax-years/{year_id}/export/csv")
async def export_income_csv(
    year_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Export income entries as CSV."""
    tax_year = db.query(TaxYear).filter(
        TaxYear.id == year_id,
        TaxYear.user_id == user.id,
    ).first()

    if not tax_year:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rok nenalezen",
        )

    entries = db.query(IncomeEntry).filter(
        IncomeEntry.tax_year_id == year_id
    ).order_by(IncomeEntry.payout_date).all()

    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "Datum výplaty",
        "Zdroj",
        "Měna",
        "Hrubá částka",
        "Čistá částka",
        "Poplatky",
        "Kurz",
        "Částka CZK",
        "Poznámky",
    ])

    # Data
    for e in entries:
        writer.writerow([
            e.payout_date.isoformat(),
            e.source.value,
            e.currency,
            str(e.amount_gross),
            str(e.amount_net) if e.amount_net else "",
            str(e.platform_fees) if e.platform_fees else "",
            str(e.fx_rate) if e.fx_rate else "",
            str(e.amount_czk),
            e.notes or "",
        ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=prijmy_{tax_year.year}.csv"
        },
    )


@router.get("/tax-years/{year_id}/export/summary")
async def export_tax_summary(
    year_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Export tax calculation summary as JSON."""
    tax_year = db.query(TaxYear).filter(
        TaxYear.id == year_id,
        TaxYear.user_id == user.id,
    ).first()

    if not tax_year:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rok nenalezen",
        )

    # Get income entries
    income_entries = db.query(IncomeEntry).filter(
        IncomeEntry.tax_year_id == year_id
    ).all()

    # Get ruleset
    ruleset = db.query(TaxRuleset).filter(
        TaxRuleset.year == tax_year.year
    ).order_by(TaxRuleset.version.desc()).first()

    if not ruleset:
        ruleset = get_default_ruleset(tax_year.year)

    # Calculate
    calculator = OSVCCalculator(ruleset)
    result = calculator.calculate_full(tax_year, income_entries)

    return {
        "rok": tax_year.year,
        "typ": "OSVČ vedlejší" if tax_year.is_osvc_secondary else "OSVČ hlavní",
        "rezim_vydaju": tax_year.expenses_mode.value,
        "generovano": datetime.utcnow().isoformat(),
        "ruleset_verze": ruleset.version,
        "prijem": {
            "celkem_czk": str(result.total_income),
            "pocet_polozek": result.included_entries,
        },
        "vydaje": {
            "celkem_czk": str(result.total_expenses),
            "sazba": str(ruleset.expense_rate_60) if tax_year.expenses_mode == ExpenseMode.PAUSAL_60 else None,
        },
        "zaklad_dane": str(result.profit),
        "dpfo": {
            "zaklad_dane": str(result.dpfo.tax_base),
            "dan_pred_slevami": str(result.dpfo.tax_before_credits),
            "slevy": str(result.dpfo.tax_credits),
            "dan_k_uhrade": str(result.dpfo.tax_due),
            "efektivni_sazba": str(result.dpfo.effective_rate),
        },
        "vzp": {
            "vymerovaci_zaklad": str(result.vzp.assessment_base),
            "pojistne": str(result.vzp.contribution),
            "mesicni_zaloha": str(result.vzp.monthly_advance),
        },
        "cssz": {
            "rozhodna_castka": str(result.cssz.threshold),
            "nad_rozhodnou_castkou": result.cssz.above_threshold,
            "vymerovaci_zaklad": str(result.cssz.assessment_base),
            "pojistne": str(result.cssz.contribution),
            "mesicni_zaloha": str(result.cssz.monthly_advance),
        },
        "celkem_k_uhrade": {
            "dan": str(result.total_tax_due),
            "pojistne": str(result.total_insurance_due),
            "celkem": str(result.total_due),
        },
    }
