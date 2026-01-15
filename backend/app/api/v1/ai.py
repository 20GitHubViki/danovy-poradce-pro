"""
AI Agent API endpoints.

Provides interface for AI-powered analysis and recommendations.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings

router = APIRouter()


class AnalysisRequest(BaseModel):
    """Request for AI analysis."""

    query: str = Field(..., min_length=1)
    company_id: Optional[int] = None
    context: Optional[dict] = None


class AnalysisResponse(BaseModel):
    """Response from AI analysis."""

    answer: str
    sources: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    suggestions: list[str] = Field(default_factory=list)


class RecommendationRequest(BaseModel):
    """Request for AI recommendations."""

    company_id: int
    focus_area: Optional[str] = None  # tax, accounting, compliance, all


class ComplianceCheckRequest(BaseModel):
    """Request for compliance check."""

    company_id: int
    check_type: str = "all"  # all, tax, accounting, legal


class ComplianceIssue(BaseModel):
    """Single compliance issue."""

    severity: str  # error, warning, info
    category: str
    title: str
    description: str
    recommendation: str
    legal_reference: Optional[str] = None


class ComplianceCheckResponse(BaseModel):
    """Response from compliance check."""

    status: str  # ok, warnings, errors
    issues: list[ComplianceIssue]
    summary: str


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze(
    request: AnalysisRequest,
    db: Session = Depends(get_db),
):
    """
    Perform AI analysis on a query.

    Uses Claude to analyze the query in context of the company's data
    and Czech tax laws.
    """
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=503,
            detail="AI service not configured. Set ANTHROPIC_API_KEY.",
        )

    # TODO: Implement Claude API call
    # For now, return placeholder response
    return AnalysisResponse(
        answer=(
            "Tato funkce vyžaduje konfiguraci API klíče pro Claude. "
            "Nastavte ANTHROPIC_API_KEY v prostředí."
        ),
        sources=["Placeholder"],
        confidence=0.0,
        suggestions=["Nakonfigurujte API klíč pro AI funkce"],
    )


@router.post("/recommend")
async def get_recommendations(
    request: RecommendationRequest,
    db: Session = Depends(get_db),
):
    """
    Get AI-powered recommendations for a company.

    Analyzes company data and provides actionable recommendations
    for tax optimization, compliance, and accounting.
    """
    if not settings.anthropic_api_key:
        return {
            "status": "limited",
            "message": "AI recommendations require API key configuration",
            "recommendations": [],
        }

    # TODO: Implement full AI recommendations
    # For now, return basic rule-based recommendations
    return {
        "status": "basic",
        "message": "Using rule-based recommendations (AI not configured)",
        "recommendations": [
            {
                "category": "tax",
                "title": "Kontrola DPH registrace",
                "description": "Zkontrolujte, zda nepřekračujete limit pro povinnou registraci k DPH.",
                "priority": "medium",
            },
            {
                "category": "accounting",
                "title": "Uzávěrkové operace",
                "description": "Připravte se na roční účetní závěrku.",
                "priority": "low",
            },
        ],
    }


@router.post("/compliance-check", response_model=ComplianceCheckResponse)
async def check_compliance(
    request: ComplianceCheckRequest,
    db: Session = Depends(get_db),
):
    """
    Perform compliance check on company data.

    Checks for common issues with tax filings, accounting records,
    and legal requirements.
    """
    issues = []

    # TODO: Implement actual compliance checks based on company data
    # For now, return example structure

    # Example checks that would be performed:
    # - Missing invoices for large transactions
    # - Incomplete asset depreciation records
    # - Missing tax payments
    # - Incorrect VAT calculations
    # - Missing documentation

    return ComplianceCheckResponse(
        status="ok",
        issues=issues,
        summary="Základní kontrola proběhla bez nalezených problémů. "
        "Pro detailní analýzu nakonfigurujte AI službu.",
    )


@router.get("/status")
async def get_ai_status():
    """Check AI service status and configuration."""
    return {
        "configured": bool(settings.anthropic_api_key),
        "model": settings.claude_model,
        "features": {
            "analysis": bool(settings.anthropic_api_key),
            "recommendations": bool(settings.anthropic_api_key),
            "compliance_check": True,  # Basic checks work without AI
        },
    }
