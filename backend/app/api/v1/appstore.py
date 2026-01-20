"""
App Store Connect API endpoints.

Provides access to App Store sales and financial data.
"""

from datetime import date
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.appstore import appstore_service, SalesReport, FinancialReport

router = APIRouter()


class SalesReportResponse(BaseModel):
    """Sales report entry response."""

    date: date
    app_sku: str
    app_name: str
    units: int
    proceeds: float
    currency: str
    country: str
    product_type: str


class FinancialReportResponse(BaseModel):
    """Financial report response."""

    period_start: date
    period_end: date
    currency: str
    total_units: int
    total_proceeds: float
    total_taxes_withheld: float
    exchange_rate: float


class MonthlySummaryResponse(BaseModel):
    """Monthly summary response."""

    period: str
    total_units: int
    proceeds_by_currency: dict[str, float]
    by_app: dict[str, dict]
    by_country: dict[str, dict]
    report_count: int


@router.get("/status")
async def get_appstore_status():
    """Check App Store Connect integration status."""
    return {
        "configured": appstore_service.is_configured(),
        "message": (
            "App Store Connect je nakonfigurován"
            if appstore_service.is_configured()
            else "App Store Connect není nakonfigurován. Nastavte APPSTORE_KEY_ID, APPSTORE_ISSUER_ID a APPSTORE_PRIVATE_KEY_PATH."
        ),
    }


@router.get("/sales", response_model=list[SalesReportResponse])
async def get_sales_report(
    vendor_number: str = Query(..., description="Your App Store Connect vendor number"),
    report_date: date = Query(..., description="Date for the report"),
    report_type: str = Query("SALES", description="Report type: SALES, SUBSCRIPTION"),
):
    """
    Get daily sales report from App Store Connect.

    Requires App Store Connect API credentials to be configured.
    """
    if not appstore_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="App Store Connect není nakonfigurován",
        )

    try:
        reports = await appstore_service.get_sales_report(
            vendor_number=vendor_number,
            report_date=report_date,
            report_type=report_type,
        )

        return [
            SalesReportResponse(
                date=r.date,
                app_sku=r.app_sku,
                app_name=r.app_name,
                units=r.units,
                proceeds=float(r.proceeds),
                currency=r.currency,
                country=r.country,
                product_type=r.product_type,
            )
            for r in reports
        ]

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při načítání dat: {str(e)}")


@router.get("/financial", response_model=Optional[FinancialReportResponse])
async def get_financial_report(
    vendor_number: str = Query(..., description="Your App Store Connect vendor number"),
    region_code: str = Query("WW", description="Region code: US, EU, WW"),
    year: int = Query(..., description="Year"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
):
    """
    Get monthly financial report from App Store Connect.

    Financial reports are available after Apple processes payments (usually 30-45 days after month end).
    """
    if not appstore_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="App Store Connect není nakonfigurován",
        )

    try:
        report = await appstore_service.get_financial_report(
            vendor_number=vendor_number,
            region_code=region_code,
            report_date=date(year, month, 1),
        )

        if not report:
            return None

        return FinancialReportResponse(
            period_start=report.period_start,
            period_end=report.period_end,
            currency=report.currency,
            total_units=report.total_units,
            total_proceeds=float(report.total_proceeds),
            total_taxes_withheld=float(report.total_taxes_withheld),
            exchange_rate=float(report.exchange_rate),
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při načítání dat: {str(e)}")


@router.get("/monthly-summary", response_model=MonthlySummaryResponse)
async def get_monthly_summary(
    vendor_number: str = Query(..., description="Your App Store Connect vendor number"),
    year: int = Query(..., description="Year"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
):
    """
    Get aggregated monthly summary of App Store sales.

    This fetches daily reports and aggregates them into a monthly summary.
    Note: This may take some time as it fetches data for each day.
    """
    if not appstore_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="App Store Connect není nakonfigurován",
        )

    try:
        summary = await appstore_service.get_monthly_summary(
            vendor_number=vendor_number,
            year=year,
            month=month,
        )

        return MonthlySummaryResponse(**summary)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při načítání dat: {str(e)}")
