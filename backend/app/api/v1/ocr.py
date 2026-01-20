"""
OCR API endpoints for invoice scanning.

Provides invoice data extraction from images.
"""

from datetime import date
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field

from app.services.ocr import ocr_service, OCRBackend, ExtractedInvoiceData

router = APIRouter()


class InvoiceDataResponse(BaseModel):
    """Extracted invoice data response."""

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
    total_amount: Optional[float] = None
    tax_amount: Optional[float] = None
    tax_base: Optional[float] = None
    currency: str = "CZK"

    # Tax info
    tax_rates: list[int] = Field(default_factory=list)
    items: list[dict] = Field(default_factory=list)

    # Metadata
    confidence: float = Field(..., ge=0, le=1, description="Extraction confidence (0-1)")
    warnings: list[str] = Field(default_factory=list)

    @classmethod
    def from_extracted(cls, data: ExtractedInvoiceData) -> "InvoiceDataResponse":
        """Create response from extracted data."""
        return cls(
            supplier_name=data.supplier_name,
            supplier_ico=data.supplier_ico,
            supplier_dic=data.supplier_dic,
            supplier_address=data.supplier_address,
            invoice_number=data.invoice_number,
            issue_date=data.issue_date,
            due_date=data.due_date,
            variable_symbol=data.variable_symbol,
            total_amount=float(data.total_amount) if data.total_amount else None,
            tax_amount=float(data.tax_amount) if data.tax_amount else None,
            tax_base=float(data.tax_base) if data.tax_base else None,
            currency=data.currency,
            tax_rates=data.tax_rates,
            items=data.items,
            confidence=data.confidence,
            warnings=data.warnings,
        )


class ScanBase64Request(BaseModel):
    """Request with base64-encoded image."""

    image: str = Field(..., description="Base64-encoded image data")
    backend: Optional[str] = Field(
        None,
        description="OCR backend: claude_vision, tesseract, or mock",
    )


@router.post("/scan", response_model=InvoiceDataResponse)
async def scan_invoice(
    file: UploadFile = File(..., description="Invoice image (JPEG, PNG, PDF)"),
):
    """
    Scan an invoice image and extract data.

    Uploads an image file and extracts invoice information using OCR.
    Supports JPEG, PNG, and PDF formats.

    Returns extracted fields including:
    - Supplier information (name, IČO, DIČ, address)
    - Invoice details (number, dates, variable symbol)
    - Financial data (amounts, tax, currency)
    """
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/webp", "application/pdf"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Nepodporovaný typ souboru: {file.content_type}. Povolené: {', '.join(allowed_types)}",
        )

    try:
        # Read file content
        image_bytes = await file.read()

        if len(image_bytes) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(
                status_code=400,
                detail="Soubor je příliš velký. Maximum je 10MB.",
            )

        # Extract invoice data
        extracted = await ocr_service.extract_invoice_data(image_bytes=image_bytes)

        return InvoiceDataResponse.from_extracted(extracted)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Chyba při zpracování faktury: {str(e)}",
        )


@router.post("/scan-base64", response_model=InvoiceDataResponse)
async def scan_invoice_base64(request: ScanBase64Request):
    """
    Scan an invoice from base64-encoded image.

    Alternative endpoint for scanning when image is already base64-encoded.
    Useful for mobile apps or when image is embedded in request.
    """
    try:
        # Parse backend if provided
        backend = None
        if request.backend:
            try:
                backend = OCRBackend(request.backend)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Neplatný backend: {request.backend}. Použijte: claude_vision, tesseract, nebo mock",
                )

        from app.services.ocr import get_ocr_service

        service = get_ocr_service(backend)

        # Extract invoice data
        extracted = await service.extract_invoice_data(image_base64=request.image)

        return InvoiceDataResponse.from_extracted(extracted)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Chyba při zpracování faktury: {str(e)}",
        )


@router.get("/status")
async def get_ocr_status():
    """
    Check OCR service status.

    Returns information about available OCR backends and configuration.
    """
    from app.config import settings

    backends = {
        "claude_vision": {
            "available": bool(settings.anthropic_api_key),
            "description": "Claude Vision API - nejpřesnější, vyžaduje API klíč",
        },
        "tesseract": {
            "available": _check_tesseract(),
            "description": "Lokální Tesseract OCR - vyžaduje instalaci pytesseract",
        },
        "mock": {
            "available": True,
            "description": "Testovací backend - vrací ukázková data",
        },
    }

    recommended = "claude_vision" if backends["claude_vision"]["available"] else (
        "tesseract" if backends["tesseract"]["available"] else "mock"
    )

    return {
        "status": "ready" if any(b["available"] for b in backends.values()) else "not_configured",
        "backends": backends,
        "recommended": recommended,
    }


def _check_tesseract() -> bool:
    """Check if Tesseract is available."""
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


@router.post("/validate-ico/{ico}")
async def validate_ico(ico: str):
    """
    Validate Czech IČO (company ID number).

    Checks if the IČO has valid format and checksum.
    """
    if not ico or len(ico) != 8 or not ico.isdigit():
        return {
            "ico": ico,
            "valid": False,
            "reason": "IČO musí mít přesně 8 číslic",
        }

    # Czech IČO validation algorithm (mod 11 checksum)
    weights = [8, 7, 6, 5, 4, 3, 2]
    checksum = sum(int(ico[i]) * weights[i] for i in range(7))
    remainder = checksum % 11

    if remainder == 0:
        expected_check = 1
    elif remainder == 1:
        expected_check = 0
    else:
        expected_check = 11 - remainder

    is_valid = int(ico[7]) == expected_check

    return {
        "ico": ico,
        "valid": is_valid,
        "reason": None if is_valid else "Neplatný kontrolní součet",
    }


@router.post("/validate-dic/{dic}")
async def validate_dic(dic: str):
    """
    Validate Czech DIČ (VAT ID number).

    Checks if the DIČ has valid format (CZ + IČO or CZ + birth number).
    """
    dic = dic.upper().strip()

    if not dic.startswith("CZ"):
        return {
            "dic": dic,
            "valid": False,
            "reason": "DIČ musí začínat CZ",
        }

    number_part = dic[2:]

    # Can be IČO (8 digits) or birth number (9-10 digits)
    if len(number_part) == 8:
        # Validate as IČO
        ico_result = await validate_ico(number_part)
        return {
            "dic": dic,
            "valid": ico_result["valid"],
            "reason": ico_result.get("reason"),
            "type": "právnická osoba" if ico_result["valid"] else None,
        }
    elif 9 <= len(number_part) <= 10 and number_part.isdigit():
        # Basic birth number format check
        return {
            "dic": dic,
            "valid": True,
            "reason": None,
            "type": "fyzická osoba",
        }
    else:
        return {
            "dic": dic,
            "valid": False,
            "reason": "Neplatný formát DIČ",
        }
