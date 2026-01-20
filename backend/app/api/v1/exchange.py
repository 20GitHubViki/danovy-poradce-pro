"""
CNB Exchange Rate API endpoints.

Provides access to Czech National Bank exchange rates.
"""

from datetime import date
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.cnb_rates import cnb_service

router = APIRouter()


class ExchangeRateResponse(BaseModel):
    """Single exchange rate response."""

    currency: str
    rate: float = Field(..., description="Exchange rate to CZK")
    date: date
    amount_in_czk: Optional[float] = Field(
        None, description="If amount provided, converted value in CZK"
    )


class AllRatesResponse(BaseModel):
    """All exchange rates response."""

    date: date
    rates: dict[str, float]
    cache_stats: dict


class ConversionResponse(BaseModel):
    """Currency conversion response."""

    from_currency: str
    to_currency: str
    from_amount: float
    to_amount: float
    rate: float
    date: date


class AnnualAverageResponse(BaseModel):
    """Annual average rate response."""

    currency: str
    year: int
    average_rate: float
    months_sampled: int


@router.get("/rate/{currency}", response_model=ExchangeRateResponse)
async def get_exchange_rate(
    currency: str,
    for_date: Optional[date] = Query(None, description="Date for the rate (default: today)"),
    amount: Optional[float] = Query(None, description="Amount to convert to CZK"),
):
    """
    Get exchange rate for a specific currency.

    Returns the CNB exchange rate for the given currency to CZK.
    """
    try:
        rate_date = for_date or date.today()
        rate = await cnb_service.get_rate(currency, rate_date)

        response = ExchangeRateResponse(
            currency=currency.upper(),
            rate=float(rate),
            date=rate_date,
        )

        if amount is not None:
            converted = await cnb_service.convert(
                Decimal(str(amount)), currency, "CZK", rate_date
            )
            response.amount_in_czk = float(converted)

        return response

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při načítání kurzu: {str(e)}")


@router.get("/rates", response_model=AllRatesResponse)
async def get_all_rates(
    for_date: Optional[date] = Query(None, description="Date for rates (default: today)"),
):
    """
    Get all exchange rates for a specific date.

    Returns all CNB exchange rates to CZK for the given date.
    """
    try:
        rate_date = for_date or date.today()
        rates = await cnb_service.get_rates(rate_date)

        return AllRatesResponse(
            date=rate_date,
            rates={k: float(v) for k, v in rates.items()},
            cache_stats=cnb_service.get_cache_stats(),
        )

    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při načítání kurzů: {str(e)}")


@router.get("/convert", response_model=ConversionResponse)
async def convert_currency(
    amount: float = Query(..., description="Amount to convert"),
    from_currency: str = Query(..., description="Source currency code"),
    to_currency: str = Query("CZK", description="Target currency code"),
    for_date: Optional[date] = Query(None, description="Date for the rate"),
):
    """
    Convert amount between currencies.

    Uses CNB exchange rates to convert between currencies.
    """
    try:
        rate_date = for_date or date.today()
        converted = await cnb_service.convert(
            Decimal(str(amount)),
            from_currency,
            to_currency,
            rate_date,
        )

        # Calculate the effective rate
        rates = await cnb_service.get_rates(rate_date)
        from_rate = rates.get(from_currency.upper(), Decimal("1"))
        to_rate = rates.get(to_currency.upper(), Decimal("1"))
        effective_rate = from_rate / to_rate

        return ConversionResponse(
            from_currency=from_currency.upper(),
            to_currency=to_currency.upper(),
            from_amount=amount,
            to_amount=float(converted),
            rate=float(effective_rate),
            date=rate_date,
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při konverzi: {str(e)}")


@router.get("/annual-average/{currency}", response_model=AnnualAverageResponse)
async def get_annual_average(
    currency: str,
    year: int = Query(..., ge=2000, le=2100, description="Year for average"),
):
    """
    Get annual average exchange rate.

    Useful for tax reporting when converting foreign income.
    Calculates average from monthly samples.
    """
    try:
        avg_rate = await cnb_service.get_annual_average(currency, year)

        # Count months sampled
        current_date = date.today()
        if year < current_date.year:
            months = 12
        elif year == current_date.year:
            months = current_date.month
        else:
            months = 0

        return AnnualAverageResponse(
            currency=currency.upper(),
            year=year,
            average_rate=float(avg_rate),
            months_sampled=months,
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při výpočtu průměru: {str(e)}")


@router.get("/currencies")
async def list_currencies():
    """
    List commonly used currencies.

    Returns list of currency codes supported by CNB.
    """
    return {
        "common": cnb_service.CURRENCIES,
        "note": "CNB publikuje kurzy pro cca 30 měn. Použijte /rates pro kompletní seznam.",
    }


@router.post("/cache/clear")
async def clear_cache():
    """
    Clear the exchange rate cache.

    Forces fresh data fetch on next request.
    """
    cnb_service.clear_cache()
    return {"message": "Cache vymazána", "stats": cnb_service.get_cache_stats()}
