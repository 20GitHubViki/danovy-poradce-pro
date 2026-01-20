"""
CNB Exchange Rate Service.

Fetches exchange rates from Czech National Bank with TTL-based caching.
"""

import asyncio
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Optional
import httpx


class CacheEntry:
    """Cache entry with TTL support."""

    def __init__(self, data: dict[str, Decimal], ttl_seconds: int = 3600):
        self.data = data
        self.expires_at = datetime.now() + timedelta(seconds=ttl_seconds)

    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at


class CNBExchangeRateService:
    """
    Service for fetching exchange rates from Czech National Bank (ČNB).

    Rates are published daily around 14:30 CET.
    Features:
    - TTL-based caching (default 1 hour)
    - Historical rates support
    - All major currencies supported
    """

    BASE_URL = "https://www.cnb.cz/cs/financni-trhy/devizovy-trh/kurzy-devizoveho-trhu/kurzy-devizoveho-trhu"
    DEFAULT_TTL = 3600  # 1 hour cache

    # Common currencies with their Czech names for reference
    CURRENCIES = {
        "EUR": "Euro",
        "USD": "Americký dolar",
        "GBP": "Britská libra",
        "CHF": "Švýcarský frank",
        "PLN": "Polský zlotý",
        "JPY": "Japonský jen",
        "CAD": "Kanadský dolar",
        "AUD": "Australský dolar",
        "SEK": "Švédská koruna",
        "NOK": "Norská koruna",
        "DKK": "Dánská koruna",
        "HUF": "Maďarský forint",
        "RUB": "Ruský rubl",
        "CNY": "Čínský renminbi",
    }

    def __init__(self, ttl_seconds: int = DEFAULT_TTL):
        self._cache: dict[str, CacheEntry] = {}
        self._ttl = ttl_seconds
        self._lock = asyncio.Lock()

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
        currency = currency.upper()
        rates = await self.get_rates(for_date)

        if currency not in rates:
            available = ", ".join(sorted(rates.keys())[:10])
            raise ValueError(
                f"Currency {currency} not found. Available: {available}..."
            )

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
            Dictionary of currency code -> rate to CZK
        """
        for_date = for_date or date.today()
        cache_key = for_date.isoformat()

        async with self._lock:
            # Check cache
            if cache_key in self._cache:
                entry = self._cache[cache_key]
                if not entry.is_expired():
                    return entry.data
                # Remove expired entry
                del self._cache[cache_key]

            # Fetch new rates
            rates = await self._fetch_rates(for_date)

            if rates:
                # Historical rates don't expire (data won't change)
                ttl = self._ttl if for_date >= date.today() else 86400 * 365
                self._cache[cache_key] = CacheEntry(rates, ttl)

            return rates

    async def convert(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str = "CZK",
        for_date: Optional[date] = None,
    ) -> Decimal:
        """
        Convert amount between currencies.

        Args:
            amount: Amount to convert
            from_currency: Source currency code
            to_currency: Target currency code (default: CZK)
            for_date: Date for the rate

        Returns:
            Converted amount
        """
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        if from_currency == to_currency:
            return amount

        rates = await self.get_rates(for_date)

        # Convert to CZK first (if not already)
        if from_currency == "CZK":
            czk_amount = amount
        elif from_currency in rates:
            czk_amount = amount * rates[from_currency]
        else:
            raise ValueError(f"Currency {from_currency} not found")

        # Convert from CZK to target
        if to_currency == "CZK":
            return czk_amount
        elif to_currency in rates:
            return czk_amount / rates[to_currency]
        else:
            raise ValueError(f"Currency {to_currency} not found")

    async def get_annual_average(
        self,
        currency: str,
        year: int,
    ) -> Decimal:
        """
        Get annual average exchange rate (useful for tax reporting).

        Args:
            currency: Currency code
            year: Year for average

        Returns:
            Average exchange rate for the year
        """
        currency = currency.upper()

        # Sample rates from each month
        rates = []
        for month in range(1, 13):
            # Use 15th of each month
            try:
                rate_date = date(year, month, 15)
                if rate_date > date.today():
                    break
                rate = await self.get_rate(currency, rate_date)
                rates.append(rate)
            except (ValueError, Exception):
                continue

        if not rates:
            raise ValueError(f"No rates found for {currency} in {year}")

        return sum(rates) / len(rates)

    async def _fetch_rates(self, for_date: date) -> dict[str, Decimal]:
        """Fetch rates from CNB API."""
        url = f"{self.BASE_URL}/denni_kurz.txt"
        params = {"date": for_date.strftime("%d.%m.%Y")}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params=params, timeout=10.0)
                response.raise_for_status()
            except httpx.TimeoutException:
                raise ConnectionError("CNB API timeout")
            except httpx.HTTPError as e:
                # For weekends/holidays, CNB returns data for last trading day
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
        rates = {"CZK": Decimal("1")}  # Include CZK as 1:1
        lines = text.strip().split("\n")

        # Skip header lines (date and column headers)
        for line in lines[2:]:
            parts = line.split("|")
            if len(parts) >= 5:
                try:
                    amount = int(parts[2])
                    code = parts[3].strip()
                    # Czech uses comma as decimal separator
                    rate = Decimal(parts[4].replace(",", ".").strip())
                    # Normalize to single unit rate
                    rates[code] = rate / amount
                except (ValueError, InvalidOperation):
                    continue

        return rates

    def clear_cache(self) -> None:
        """Clear the rate cache."""
        self._cache.clear()

    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        now = datetime.now()
        valid = sum(1 for e in self._cache.values() if not e.is_expired())
        return {
            "total_entries": len(self._cache),
            "valid_entries": valid,
            "expired_entries": len(self._cache) - valid,
        }


# Global service instance
cnb_service = CNBExchangeRateService()


# Convenience functions
async def get_exchange_rate(currency: str, for_date: Optional[date] = None) -> Decimal:
    """
    Convenience function to get a single exchange rate.

    Args:
        currency: Currency code (e.g., "USD")
        for_date: Date for rate (default: today)

    Returns:
        Exchange rate to CZK
    """
    return await cnb_service.get_rate(currency, for_date)


async def convert_to_czk(
    amount: Decimal,
    currency: str,
    for_date: Optional[date] = None,
) -> Decimal:
    """
    Convert amount to CZK.

    Args:
        amount: Amount to convert
        currency: Source currency code
        for_date: Date for rate

    Returns:
        Amount in CZK
    """
    return await cnb_service.convert(amount, currency, "CZK", for_date)
