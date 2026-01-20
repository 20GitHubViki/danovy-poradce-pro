"""
App Store Connect API Service.

Fetches sales reports and financial data from Apple App Store Connect.
"""

import jwt
import time
import asyncio
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional
from dataclasses import dataclass
from pathlib import Path
import httpx
import gzip
import io
import csv

from app.config import settings


@dataclass
class SalesReport:
    """A processed sales report entry."""

    date: date
    app_sku: str
    app_name: str
    units: int
    proceeds: Decimal
    currency: str
    country: str
    product_type: str  # App, IAP, Subscription


@dataclass
class FinancialReport:
    """A processed financial report entry."""

    period_start: date
    period_end: date
    currency: str
    total_units: int
    total_proceeds: Decimal
    total_taxes_withheld: Decimal
    exchange_rate: Decimal


class AppStoreConnectService:
    """
    Service for interacting with App Store Connect API.

    Uses JWT authentication with App Store Connect API keys.
    Requires:
    - Key ID (from App Store Connect)
    - Issuer ID (from App Store Connect)
    - Private key (.p8 file)
    """

    BASE_URL = "https://api.appstoreconnect.apple.com"
    SALES_URL = "https://api.appstoreconnect.apple.com/v1/salesReports"
    FINANCE_URL = "https://api.appstoreconnect.apple.com/v1/financeReports"

    def __init__(
        self,
        key_id: Optional[str] = None,
        issuer_id: Optional[str] = None,
        private_key_path: Optional[Path] = None,
    ):
        """
        Initialize the App Store Connect service.

        Args:
            key_id: App Store Connect API Key ID
            issuer_id: App Store Connect Issuer ID
            private_key_path: Path to .p8 private key file
        """
        self.key_id = key_id or settings.appstore_key_id
        self.issuer_id = issuer_id or settings.appstore_issuer_id
        self.private_key_path = private_key_path or settings.appstore_private_key_path
        self._private_key: Optional[str] = None
        self._token_cache: Optional[tuple[str, float]] = None

    def is_configured(self) -> bool:
        """Check if the service is properly configured."""
        return all([
            self.key_id,
            self.issuer_id,
            self.private_key_path and self.private_key_path.exists(),
        ])

    def _load_private_key(self) -> str:
        """Load the private key from file."""
        if self._private_key is None:
            if not self.private_key_path or not self.private_key_path.exists():
                raise ValueError("Private key file not found")
            self._private_key = self.private_key_path.read_text()
        return self._private_key

    def _generate_token(self) -> str:
        """
        Generate a JWT token for App Store Connect API.

        Tokens are valid for 20 minutes max.
        """
        # Check cache (tokens valid for 15 minutes to be safe)
        if self._token_cache:
            token, expiry = self._token_cache
            if time.time() < expiry - 60:  # 1 minute buffer
                return token

        private_key = self._load_private_key()

        now = int(time.time())
        expiry = now + 15 * 60  # 15 minutes

        payload = {
            "iss": self.issuer_id,
            "iat": now,
            "exp": expiry,
            "aud": "appstoreconnect-v1",
        }

        headers = {
            "alg": "ES256",
            "kid": self.key_id,
            "typ": "JWT",
        }

        token = jwt.encode(
            payload,
            private_key,
            algorithm="ES256",
            headers=headers,
        )

        self._token_cache = (token, expiry)
        return token

    def _get_headers(self) -> dict:
        """Get headers with authorization token."""
        token = self._generate_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def get_sales_report(
        self,
        vendor_number: str,
        report_date: date,
        report_type: str = "SALES",
        report_subtype: str = "SUMMARY",
    ) -> list[SalesReport]:
        """
        Fetch sales report from App Store Connect.

        Args:
            vendor_number: Your vendor number (found in App Store Connect)
            report_date: Date for the report
            report_type: SALES, SUBSCRIPTION, etc.
            report_subtype: SUMMARY, DETAILED, etc.

        Returns:
            List of SalesReport entries
        """
        if not self.is_configured():
            raise ValueError("App Store Connect is not configured")

        params = {
            "filter[vendorNumber]": vendor_number,
            "filter[reportType]": report_type,
            "filter[reportSubType]": report_subtype,
            "filter[reportDate]": report_date.strftime("%Y-%m-%d"),
            "filter[frequency]": "DAILY",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.SALES_URL,
                params=params,
                headers=self._get_headers(),
                timeout=30.0,
            )

            if response.status_code == 404:
                # No data for this date
                return []

            response.raise_for_status()

            # Response is gzipped TSV
            return self._parse_sales_report(response.content)

    def _parse_sales_report(self, content: bytes) -> list[SalesReport]:
        """Parse gzipped TSV sales report."""
        reports = []

        try:
            # Decompress gzip
            with gzip.GzipFile(fileobj=io.BytesIO(content)) as f:
                text = f.read().decode("utf-8")
        except (gzip.BadGzipFile, OSError):
            # Not gzipped, try direct
            text = content.decode("utf-8")

        reader = csv.DictReader(io.StringIO(text), delimiter="\t")

        for row in reader:
            try:
                reports.append(
                    SalesReport(
                        date=datetime.strptime(row.get("Begin Date", ""), "%m/%d/%Y").date(),
                        app_sku=row.get("SKU", ""),
                        app_name=row.get("Title", ""),
                        units=int(row.get("Units", 0)),
                        proceeds=Decimal(row.get("Developer Proceeds", "0")),
                        currency=row.get("Currency of Proceeds", "USD"),
                        country=row.get("Country Code", ""),
                        product_type=row.get("Product Type Identifier", ""),
                    )
                )
            except (ValueError, KeyError):
                continue

        return reports

    async def get_financial_report(
        self,
        vendor_number: str,
        region_code: str,
        report_date: date,
    ) -> Optional[FinancialReport]:
        """
        Fetch financial report from App Store Connect.

        Args:
            vendor_number: Your vendor number
            region_code: Region code (e.g., "US", "EU", "WW")
            report_date: Month for the report (day is ignored)

        Returns:
            FinancialReport or None if not available
        """
        if not self.is_configured():
            raise ValueError("App Store Connect is not configured")

        params = {
            "filter[vendorNumber]": vendor_number,
            "filter[regionCode]": region_code,
            "filter[reportType]": "FINANCIAL",
            "filter[reportDate]": report_date.strftime("%Y-%m"),
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.FINANCE_URL,
                params=params,
                headers=self._get_headers(),
                timeout=30.0,
            )

            if response.status_code == 404:
                return None

            response.raise_for_status()

            return self._parse_financial_report(response.content, report_date)

    def _parse_financial_report(
        self, content: bytes, report_date: date
    ) -> Optional[FinancialReport]:
        """Parse financial report."""
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(content)) as f:
                text = f.read().decode("utf-8")
        except (gzip.BadGzipFile, OSError):
            text = content.decode("utf-8")

        reader = csv.DictReader(io.StringIO(text), delimiter="\t")

        total_units = 0
        total_proceeds = Decimal("0")
        total_taxes = Decimal("0")
        currency = "USD"
        exchange_rate = Decimal("1")

        for row in reader:
            try:
                total_units += int(row.get("Total Units", 0))
                total_proceeds += Decimal(row.get("Total Amount", "0"))
                total_taxes += Decimal(row.get("Total Tax Withheld", "0"))
                currency = row.get("Currency", "USD")
                if row.get("Exchange Rate"):
                    exchange_rate = Decimal(row.get("Exchange Rate", "1"))
            except (ValueError, KeyError):
                continue

        if total_units == 0 and total_proceeds == 0:
            return None

        # Calculate period
        period_start = report_date.replace(day=1)
        if report_date.month == 12:
            period_end = report_date.replace(year=report_date.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            period_end = report_date.replace(month=report_date.month + 1, day=1) - timedelta(days=1)

        return FinancialReport(
            period_start=period_start,
            period_end=period_end,
            currency=currency,
            total_units=total_units,
            total_proceeds=total_proceeds,
            total_taxes_withheld=total_taxes,
            exchange_rate=exchange_rate,
        )

    async def get_monthly_summary(
        self,
        vendor_number: str,
        year: int,
        month: int,
    ) -> dict:
        """
        Get a summary of sales for a month.

        Args:
            vendor_number: Your vendor number
            year: Year
            month: Month (1-12)

        Returns:
            Dictionary with summary data
        """
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)

        all_reports = []
        current = start_date

        while current <= end_date:
            try:
                reports = await self.get_sales_report(vendor_number, current)
                all_reports.extend(reports)
            except Exception:
                pass  # Skip days with errors
            current += timedelta(days=1)
            await asyncio.sleep(0.1)  # Rate limiting

        # Aggregate
        total_units = sum(r.units for r in all_reports)
        total_proceeds_by_currency = {}
        by_app = {}
        by_country = {}

        for r in all_reports:
            # By currency
            if r.currency not in total_proceeds_by_currency:
                total_proceeds_by_currency[r.currency] = Decimal("0")
            total_proceeds_by_currency[r.currency] += r.proceeds

            # By app
            if r.app_name not in by_app:
                by_app[r.app_name] = {"units": 0, "proceeds": Decimal("0")}
            by_app[r.app_name]["units"] += r.units
            by_app[r.app_name]["proceeds"] += r.proceeds

            # By country
            if r.country not in by_country:
                by_country[r.country] = {"units": 0, "proceeds": Decimal("0")}
            by_country[r.country]["units"] += r.units
            by_country[r.country]["proceeds"] += r.proceeds

        return {
            "period": f"{year}-{month:02d}",
            "total_units": total_units,
            "proceeds_by_currency": {
                k: float(v) for k, v in total_proceeds_by_currency.items()
            },
            "by_app": {
                k: {"units": v["units"], "proceeds": float(v["proceeds"])}
                for k, v in by_app.items()
            },
            "by_country": {
                k: {"units": v["units"], "proceeds": float(v["proceeds"])}
                for k, v in sorted(by_country.items(), key=lambda x: -x[1]["proceeds"])[:10]
            },
            "report_count": len(all_reports),
        }


# Global instance
appstore_service = AppStoreConnectService()
