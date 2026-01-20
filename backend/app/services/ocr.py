"""
OCR Service for Invoice Scanning.

Extracts invoice data from images using OCR.
Supports multiple backends: Tesseract (local), Claude Vision, or external APIs.
"""

import base64
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Optional
import httpx

from app.config import settings


class OCRBackend(Enum):
    """Available OCR backends."""

    CLAUDE_VISION = "claude_vision"
    TESSERACT = "tesseract"
    MOCK = "mock"  # For testing


@dataclass
class ExtractedInvoiceData:
    """Extracted invoice data from OCR."""

    # Supplier info
    supplier_name: Optional[str] = None
    supplier_ico: Optional[str] = None
    supplier_dic: Optional[str] = None
    supplier_address: Optional[str] = None

    # Invoice details
    invoice_number: Optional[str] = None
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    variable_symbol: Optional[str] = None

    # Amounts
    total_amount: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    tax_base: Optional[Decimal] = None
    currency: str = "CZK"

    # Tax rates found
    tax_rates: list[int] = field(default_factory=list)

    # Items (if itemized)
    items: list[dict] = field(default_factory=list)

    # Raw text for reference
    raw_text: Optional[str] = None

    # Confidence score (0-1)
    confidence: float = 0.0

    # Warnings/issues found
    warnings: list[str] = field(default_factory=list)


class OCRService:
    """
    OCR Service for extracting invoice data from images.

    Supports:
    - Claude Vision API (recommended for accuracy)
    - Tesseract (local, requires pytesseract)
    - Mock backend (for testing)
    """

    def __init__(self, backend: OCRBackend = OCRBackend.CLAUDE_VISION):
        self.backend = backend

    async def extract_invoice_data(
        self,
        image_path: Optional[Path] = None,
        image_bytes: Optional[bytes] = None,
        image_base64: Optional[str] = None,
    ) -> ExtractedInvoiceData:
        """
        Extract invoice data from an image.

        Provide exactly one of: image_path, image_bytes, or image_base64.

        Args:
            image_path: Path to the image file
            image_bytes: Raw image bytes
            image_base64: Base64-encoded image

        Returns:
            ExtractedInvoiceData with parsed invoice information
        """
        # Get image as base64
        if image_path:
            with open(image_path, "rb") as f:
                image_bytes = f.read()

        if image_bytes:
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        if not image_base64:
            raise ValueError("No image provided")

        # Detect media type
        media_type = self._detect_media_type(image_base64)

        # Route to appropriate backend
        if self.backend == OCRBackend.CLAUDE_VISION:
            return await self._extract_with_claude(image_base64, media_type)
        elif self.backend == OCRBackend.TESSERACT:
            return await self._extract_with_tesseract(image_bytes or base64.b64decode(image_base64))
        elif self.backend == OCRBackend.MOCK:
            return self._extract_mock()
        else:
            raise ValueError(f"Unsupported backend: {self.backend}")

    async def _extract_with_claude(
        self,
        image_base64: str,
        media_type: str,
    ) -> ExtractedInvoiceData:
        """Extract invoice data using Claude Vision API."""
        if not settings.anthropic_api_key:
            raise ValueError("Claude API key not configured. Set ANTHROPIC_API_KEY.")

        # Build the prompt for invoice extraction
        extraction_prompt = """Analyzuj tuto fakturu a extrahuj následující údaje ve formátu JSON:

{
    "supplier_name": "název dodavatele",
    "supplier_ico": "IČO (8 číslic)",
    "supplier_dic": "DIČ (CZ + čísla)",
    "supplier_address": "adresa dodavatele",
    "invoice_number": "číslo faktury",
    "issue_date": "datum vystavení (YYYY-MM-DD)",
    "due_date": "datum splatnosti (YYYY-MM-DD)",
    "variable_symbol": "variabilní symbol",
    "total_amount": číslo (celková částka),
    "tax_amount": číslo (DPH),
    "tax_base": číslo (základ daně),
    "currency": "měna (CZK/EUR/USD)",
    "tax_rates": [sazby DPH v %],
    "items": [{"description": "popis", "quantity": číslo, "unit_price": číslo, "total": číslo}],
    "confidence": číslo 0-1 (jak jsi si jistý výsledky),
    "warnings": ["případné problémy nebo nejasnosti"]
}

Pokud nějaký údaj nenajdeš, použij null. Vrať POUZE JSON bez dalšího textu."""

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": settings.claude_model,
                    "max_tokens": 2048,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": media_type,
                                        "data": image_base64,
                                    },
                                },
                                {
                                    "type": "text",
                                    "text": extraction_prompt,
                                },
                            ],
                        }
                    ],
                },
                timeout=60.0,
            )

            response.raise_for_status()
            result = response.json()

        # Parse Claude's response
        content = result["content"][0]["text"]
        return self._parse_json_response(content)

    async def _extract_with_tesseract(self, image_bytes: bytes) -> ExtractedInvoiceData:
        """Extract invoice data using Tesseract OCR."""
        try:
            import pytesseract
            from PIL import Image
            import io
        except ImportError:
            raise ImportError(
                "Tesseract backend requires pytesseract and Pillow. "
                "Install with: pip install pytesseract Pillow"
            )

        # Convert bytes to image
        image = Image.open(io.BytesIO(image_bytes))

        # Run OCR with Czech language
        raw_text = pytesseract.image_to_string(image, lang="ces+eng")

        # Parse the raw text
        return self._parse_raw_text(raw_text)

    def _extract_mock(self) -> ExtractedInvoiceData:
        """Return mock data for testing."""
        return ExtractedInvoiceData(
            supplier_name="Test Dodavatel s.r.o.",
            supplier_ico="12345678",
            supplier_dic="CZ12345678",
            supplier_address="Testovací 123, Praha",
            invoice_number="FV2026001",
            issue_date=date.today(),
            due_date=date.today(),
            variable_symbol="2026001",
            total_amount=Decimal("12100"),
            tax_amount=Decimal("2100"),
            tax_base=Decimal("10000"),
            currency="CZK",
            tax_rates=[21],
            items=[
                {
                    "description": "Testovací služba",
                    "quantity": 1,
                    "unit_price": 10000,
                    "total": 10000,
                }
            ],
            raw_text="Mock invoice text",
            confidence=1.0,
            warnings=[],
        )

    def _parse_json_response(self, json_text: str) -> ExtractedInvoiceData:
        """Parse JSON response from Claude."""
        import json

        # Clean up potential markdown code blocks
        json_text = json_text.strip()
        if json_text.startswith("```"):
            json_text = re.sub(r"^```json?\n?", "", json_text)
            json_text = re.sub(r"\n?```$", "", json_text)

        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as e:
            return ExtractedInvoiceData(
                raw_text=json_text,
                warnings=[f"Failed to parse JSON: {e}"],
                confidence=0.0,
            )

        # Convert to ExtractedInvoiceData
        return ExtractedInvoiceData(
            supplier_name=data.get("supplier_name"),
            supplier_ico=data.get("supplier_ico"),
            supplier_dic=data.get("supplier_dic"),
            supplier_address=data.get("supplier_address"),
            invoice_number=data.get("invoice_number"),
            issue_date=self._parse_date(data.get("issue_date")),
            due_date=self._parse_date(data.get("due_date")),
            variable_symbol=data.get("variable_symbol"),
            total_amount=self._parse_decimal(data.get("total_amount")),
            tax_amount=self._parse_decimal(data.get("tax_amount")),
            tax_base=self._parse_decimal(data.get("tax_base")),
            currency=data.get("currency", "CZK"),
            tax_rates=data.get("tax_rates", []),
            items=data.get("items", []),
            raw_text=json_text,
            confidence=data.get("confidence", 0.8),
            warnings=data.get("warnings", []),
        )

    def _parse_raw_text(self, text: str) -> ExtractedInvoiceData:
        """Parse raw OCR text using regex patterns."""
        data = ExtractedInvoiceData(raw_text=text)
        warnings = []

        # IČO pattern (8 digits)
        ico_match = re.search(r"IČO?:?\s*(\d{8})", text, re.IGNORECASE)
        if ico_match:
            data.supplier_ico = ico_match.group(1)

        # DIČ pattern (CZ + digits)
        dic_match = re.search(r"DIČ:?\s*(CZ\d+)", text, re.IGNORECASE)
        if dic_match:
            data.supplier_dic = dic_match.group(1)

        # Invoice number patterns
        inv_patterns = [
            r"(?:Faktura|Číslo faktury|Č\.\s*fa\.?):?\s*([A-Z0-9/-]+)",
            r"(?:Invoice|Inv\.?):?\s*([A-Z0-9/-]+)",
        ]
        for pattern in inv_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data.invoice_number = match.group(1).strip()
                break

        # Date patterns (Czech: DD.MM.YYYY)
        date_pattern = r"(\d{1,2})\s*[./]\s*(\d{1,2})\s*[./]\s*(\d{4})"
        dates = re.findall(date_pattern, text)
        if dates:
            try:
                day, month, year = dates[0]
                data.issue_date = date(int(year), int(month), int(day))
                if len(dates) > 1:
                    day, month, year = dates[1]
                    data.due_date = date(int(year), int(month), int(day))
            except (ValueError, IndexError):
                warnings.append("Could not parse dates")

        # Amount patterns (Czech uses comma for decimals, space for thousands)
        amount_patterns = [
            r"Celkem:?\s*([\d\s]+[,.]?\d*)\s*(?:Kč|CZK)?",
            r"(?:K úhradě|Částka):?\s*([\d\s]+[,.]?\d*)",
            r"Total:?\s*([\d\s]+[,.]?\d*)",
        ]
        for pattern in amount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(" ", "").replace(",", ".")
                data.total_amount = self._parse_decimal(amount_str)
                break

        # DPH (VAT) amount
        vat_match = re.search(r"DPH:?\s*([\d\s]+[,.]?\d*)", text, re.IGNORECASE)
        if vat_match:
            amount_str = vat_match.group(1).replace(" ", "").replace(",", ".")
            data.tax_amount = self._parse_decimal(amount_str)

        # Variable symbol
        vs_match = re.search(r"(?:VS|Var\.?\s*symbol):?\s*(\d+)", text, re.IGNORECASE)
        if vs_match:
            data.variable_symbol = vs_match.group(1)

        # Tax rates mentioned
        tax_rate_matches = re.findall(r"(\d+)\s*%\s*(?:DPH|sazba)", text, re.IGNORECASE)
        data.tax_rates = [int(r) for r in tax_rate_matches if int(r) in [0, 10, 15, 21]]

        # Set confidence based on how much we extracted
        fields_found = sum([
            bool(data.supplier_ico),
            bool(data.invoice_number),
            bool(data.issue_date),
            bool(data.total_amount),
        ])
        data.confidence = fields_found / 4

        data.warnings = warnings
        return data

    def _parse_date(self, value: Optional[str]) -> Optional[date]:
        """Parse date from string."""
        if not value:
            return None
        try:
            # Try ISO format first
            return date.fromisoformat(value)
        except (ValueError, TypeError):
            # Try Czech format
            try:
                parts = re.split(r"[./]", value)
                if len(parts) == 3:
                    return date(int(parts[2]), int(parts[1]), int(parts[0]))
            except (ValueError, IndexError):
                pass
        return None

    def _parse_decimal(self, value) -> Optional[Decimal]:
        """Parse decimal from various formats."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        if isinstance(value, str):
            try:
                # Remove spaces, convert Czech comma to dot
                clean = value.replace(" ", "").replace(",", ".")
                return Decimal(clean)
            except (ValueError, Exception):
                pass
        return None

    def _detect_media_type(self, base64_data: str) -> str:
        """Detect media type from base64 header or content."""
        # Check for data URL prefix
        if base64_data.startswith("data:"):
            media_type = base64_data.split(";")[0].split(":")[1]
            return media_type

        # Detect from magic bytes
        try:
            header = base64.b64decode(base64_data[:20])
            if header.startswith(b"\xff\xd8\xff"):
                return "image/jpeg"
            elif header.startswith(b"\x89PNG"):
                return "image/png"
            elif header.startswith(b"GIF"):
                return "image/gif"
            elif header.startswith(b"RIFF") and b"WEBP" in header:
                return "image/webp"
        except Exception:
            pass

        # Default to JPEG
        return "image/jpeg"


# Global service instance
ocr_service = OCRService()


def get_ocr_service(backend: Optional[OCRBackend] = None) -> OCRService:
    """Get OCR service with optional backend override."""
    if backend:
        return OCRService(backend)
    return ocr_service
