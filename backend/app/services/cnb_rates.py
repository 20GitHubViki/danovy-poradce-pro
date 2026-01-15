"""
CNB Exchange Rate Service.

Fetches exchange rates from Czech National Bank.
"""

import asyncio
from datetime import date
from decimal import Decimal
from typing import Optional
import httpx


class CNBExchangeRateService:
    """
    Service for fetching exchange rates from Czech National Bank (ČNB).

    Rates are published daily around 14:30 CET.
    """

    BASE_URL = "https://www.cnb.cz/cs/financni-trhy/devizovy-trh/kurzy-devizoveho-trhu/kurzy-devizoveho-trhu"

    def __init__(self):
        self._cache: dict[str, dict[str, Decimal]] = {}

    async def get_rate(
        self,
        currency: str,
        for_date: Optional[date] = None,
    ) -> Decimal:
        """
        Get exchange rate for a currency.

        Args:
            currency: Currency code (e.g., "USD", "EUR")
            for_date: Date for the rate (default: today)

        Returns:
            Exchange rate to CZK

        Raises:
            ValueError: If currency not found
        """
        for_date = for_date or date.today()
        cache_key = for_date.isoformat()

        # Check cache
        if cache_key in self._cache and currency in self._cache[cache_key]:
            return self._cache[cache_key][currency]

        # Fetch rates
        rates = await self._fetch_rates(for_date)
        self._cache[cache_key] = rates

        if currency not in rates:
            raise ValueError(f"Currency {currency} not found for {for_date}")

        return rates[currency]

    async def get_rates(
        self,
        for_date: Optional[date] = None,
    ) -> dict[str, Decimal]:
        """
        Get all exchange rates for a date.

        Args:
            for_date: Date for rates (default: today)

        Returns:
            Dictionary of currency code -> rate
        """
        for_date = for_date or date.today()
        cache_key = for_date.isoformat()

        if cache_key in self._cache:
            return self._cache[cache_key]

        rates = await self._fetch_rates(for_date)
        self._cache[cache_key] = rates
        return rates

    async def _fetch_rates(self, for_date: date) -> dict[str, Decimal]:
        """Fetch rates from CNB API."""
        url = f"{self.BASE_URL}/denni_kurz.txt"
        params = {"date": for_date.strftime("%d.%m.%Y")}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params=params, timeout=10.0)
                response.raise_for_status()
            except httpx.HTTPError as e:
                # Return empty dict on error (caller should handle)
                return {}

        return self._parse_rates(response.text)

    def _parse_rates(self, text: str) -> dict[str, Decimal]:
        """
        Parse CNB rate text format.

        Format:
        ```
        15.01.2026 #10
        země|měna|množství|kód|kurz
        Austrálie|dolar|1|AUD|15,432
        ...
        ```
        """
        rates = {}
        lines = text.strip().split("\n")

        # Skip header lines (date and column headers)
        for line in lines[2:]:
            parts = line.split("|")
            if len(parts) >= 5:
                try:
                    amount = int(parts[2])
                    code = parts[3]
                    # Czech uses comma as decimal separator
                    rate = Decimal(parts[4].replace(",", "."))
                    # Normalize to single unit rate
                    rates[code] = rate / amount
                except (ValueError, InvalidOperation):
                    continue

        return rates

    def clear_cache(self) -> None:
        """Clear the rate cache."""
        self._cache.clear()


# Convenience function for one-off rate fetching
async def get_exchange_rate(currency: str, for_date: Optional[date] = None) -> Decimal:
    """
    Convenience function to get a single exchange rate.

    Args:
        currency: Currency code (e.g., "USD")
        for_date: Date for rate (default: today)

    Returns:
        Exchange rate to CZK
    """
    service = CNBExchangeRateService()
    return await service.get_rate(currency, for_date)


# InvalidOperation import for error handling
from decimal import InvalidOperation
