"""
AI Agent API endpoints.

Provides interface for AI-powered analysis and recommendations.
"""

from decimal import Decimal
from typing import Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import extract

from app.database import get_db
from app.config import settings
from app.models.company import Company
from app.models.transaction import Transaction
from app.models.knowledge import KnowledgeCategory
from app.api.v1.knowledge import get_knowledge_context

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


class DividendVsSalaryRequest(BaseModel):
    """Request for dividend vs salary analysis."""

    available_profit: Decimal = Field(..., gt=0)
    other_income: Decimal = Field(default=Decimal("0"), ge=0)
    year: Optional[int] = None


class DividendVsSalaryResponse(BaseModel):
    """Response from dividend vs salary analysis."""

    recommendation: str
    dividend_net: Decimal
    salary_net: Decimal
    savings: Decimal
    explanation: str
    legal_references: list[str]
    warnings: list[str]


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


class TaxConceptRequest(BaseModel):
    """Request for tax concept explanation."""

    concept: str = Field(..., min_length=1)


class TaxDeadlinesRequest(BaseModel):
    """Request for tax deadlines."""

    year: Optional[int] = None


def _get_tax_advisor():
    """Get TaxAdvisorAgent instance."""
    from app.agents.tax_advisor import TaxAdvisorAgent

    return TaxAdvisorAgent()


def _get_company_context(db: Session, company_id: int) -> dict:
    """Build context from company data."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        return {}

    year = date.today().year
    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.company_id == company_id,
            extract("year", Transaction.date) == year,
        )
        .all()
    )

    income = sum(t.amount_czk for t in transactions if t.is_income)
    expenses = sum(t.amount_czk for t in transactions if t.is_expense)

    return {
        "company_name": company.name,
        "ico": company.ico,
        "year": year,
        "income_ytd": float(income),
        "expenses_ytd": float(expenses),
        "profit_ytd": float(income - expenses),
        "transaction_count": len(transactions),
    }


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze(
    request: AnalysisRequest,
    db: Session = Depends(get_db),
):
    """
    Perform AI analysis on a query.

    Uses Claude to analyze the query in context of the company's data,
    Czech tax laws, and uploaded knowledge documents.
    """
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=503,
            detail="AI služba není nakonfigurována. Nastavte ANTHROPIC_API_KEY.",
        )

    try:
        agent = _get_tax_advisor()

        # Build context
        context = request.context or {}
        if request.company_id:
            company_context = _get_company_context(db, request.company_id)
            context.update(company_context)

        # Add knowledge base context
        knowledge_context = get_knowledge_context(
            db=db,
            query=request.query,
            year=date.today().year,
            limit=5,
        )
        if knowledge_context:
            context["knowledge_base"] = knowledge_context

        response = await agent.analyze_query(request.query, context)

        return AnalysisResponse(
            answer=response.answer,
            sources=response.sources,
            confidence=response.confidence,
            suggestions=response.suggestions or [],
        )

    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Chyba při zpracování dotazu: {str(e)}",
        )


@router.post("/dividend-vs-salary", response_model=DividendVsSalaryResponse)
async def analyze_dividend_vs_salary(
    request: DividendVsSalaryRequest,
    db: Session = Depends(get_db),
):
    """
    Analyze optimal payout strategy: dividend vs salary.

    Compares tax implications of both approaches and provides
    AI-powered recommendation with explanation.
    """
    if not settings.anthropic_api_key:
        # Fall back to calculator-only response without AI explanation
        from app.services.tax_calculator import TaxCalculator

        year = request.year or date.today().year
        calculator = TaxCalculator(year=year)
        comparison = calculator.compare_dividend_vs_salary(
            request.available_profit, request.other_income
        )

        return DividendVsSalaryResponse(
            recommendation=comparison["recommendation"]["better_option"],
            dividend_net=Decimal(str(comparison["dividend"]["net_amount"])),
            salary_net=Decimal(str(comparison["salary"]["net_amount"])),
            savings=comparison["recommendation"]["savings"],
            explanation=comparison["recommendation"]["reasoning"],
            legal_references=["§36 zákona č. 586/1992 Sb. (srážková daň z dividend)"],
            warnings=[
                "Pro detailní AI analýzu nakonfigurujte ANTHROPIC_API_KEY.",
                "Výpočet je orientační.",
            ],
        )

    try:
        agent = _get_tax_advisor()
        analysis = await agent.analyze_dividend_vs_salary(
            request.available_profit,
            request.other_income,
            request.year,
        )

        return DividendVsSalaryResponse(
            recommendation=analysis.recommendation,
            dividend_net=analysis.dividend_net,
            salary_net=analysis.salary_net,
            savings=analysis.savings,
            explanation=analysis.explanation,
            legal_references=analysis.legal_references,
            warnings=analysis.warnings,
        )

    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Chyba při analýze: {str(e)}",
        )


@router.post("/explain-concept", response_model=AnalysisResponse)
async def explain_tax_concept(
    request: TaxConceptRequest,
    db: Session = Depends(get_db),
):
    """
    Explain a tax concept in simple terms.

    Provides clear explanation with examples and legal references.
    """
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=503,
            detail="AI služba není nakonfigurována. Nastavte ANTHROPIC_API_KEY.",
        )

    try:
        agent = _get_tax_advisor()
        response = await agent.explain_tax_concept(request.concept)

        return AnalysisResponse(
            answer=response.answer,
            sources=response.sources,
            confidence=response.confidence,
            suggestions=response.suggestions or [],
        )

    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Chyba při zpracování dotazu: {str(e)}",
        )


@router.post("/tax-deadlines", response_model=AnalysisResponse)
async def get_tax_deadlines(
    request: TaxDeadlinesRequest,
    db: Session = Depends(get_db),
):
    """
    Get important tax deadlines for the year.

    Returns comprehensive list of deadlines for s.r.o.
    """
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=503,
            detail="AI služba není nakonfigurována. Nastavte ANTHROPIC_API_KEY.",
        )

    try:
        agent = _get_tax_advisor()
        response = await agent.get_tax_deadlines(request.year)

        return AnalysisResponse(
            answer=response.answer,
            sources=response.sources,
            confidence=response.confidence,
            suggestions=response.suggestions or [],
        )

    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Chyba při zpracování dotazu: {str(e)}",
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
    # Get company context
    context = _get_company_context(db, request.company_id)

    if not context:
        raise HTTPException(status_code=404, detail="Firma nenalezena")

    if not settings.anthropic_api_key:
        # Return basic rule-based recommendations
        recommendations = []

        # Check profit for tax optimization
        profit = context.get("profit_ytd", 0)
        if profit > 0:
            recommendations.append({
                "category": "tax",
                "title": "Daňová optimalizace",
                "description": f"Při zisku {profit:,.0f} Kč zvažte optimální formu výplaty.",
                "priority": "medium",
            })

        # Check income for VAT threshold
        income = context.get("income_ytd", 0)
        if income > 1_500_000:
            recommendations.append({
                "category": "compliance",
                "title": "Kontrola DPH registrace",
                "description": "Blížíte se k hranici 2M Kč pro povinnou registraci k DPH.",
                "priority": "high" if income > 1_800_000 else "medium",
            })

        return {
            "status": "basic",
            "message": "Základní doporučení (pro AI analýzu nastavte ANTHROPIC_API_KEY)",
            "recommendations": recommendations,
        }

    try:
        agent = _get_tax_advisor()

        focus = request.focus_area or "all"
        query = f"Analyzuj finanční situaci firmy a poskytni doporučení pro oblast: {focus}"

        response = await agent.analyze_query(query, context)

        return {
            "status": "ai",
            "message": "AI analýza dokončena",
            "recommendations": [
                {
                    "category": request.focus_area or "general",
                    "title": "AI Analýza",
                    "description": response.answer,
                    "priority": "medium",
                    "sources": response.sources,
                }
            ],
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Chyba při analýze: {str(e)}",
        )


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
    context = _get_company_context(db, request.company_id)

    if not context:
        raise HTTPException(status_code=404, detail="Firma nenalezena")

    issues = []

    # Basic rule-based compliance checks
    income = context.get("income_ytd", 0)
    if income > 2_000_000:
        issues.append(
            ComplianceIssue(
                severity="warning",
                category="vat",
                title="Překročen limit pro DPH",
                description="Roční obrat překročil 2 000 000 Kč.",
                recommendation="Zkontrolujte, zda jste registrováni jako plátce DPH.",
                legal_reference="§6 zákona č. 235/2004 Sb.",
            )
        )

    if settings.anthropic_api_key:
        try:
            agent = _get_tax_advisor()
            check_areas = [request.check_type] if request.check_type != "all" else None
            response = await agent.check_compliance(context, check_areas)

            # AI might find additional issues
            if "problém" in response.answer.lower() or "chyba" in response.answer.lower():
                issues.append(
                    ComplianceIssue(
                        severity="info",
                        category="ai_analysis",
                        title="AI Analýza",
                        description=response.answer[:500],
                        recommendation="Prostudujte detailní analýzu výše.",
                    )
                )
        except Exception:
            pass  # Fall back to basic checks

    status = "ok"
    if any(i.severity == "error" for i in issues):
        status = "errors"
    elif issues:
        status = "warnings"

    summary = (
        f"Nalezeno {len(issues)} položek k řešení."
        if issues
        else "Základní kontrola proběhla bez nalezených problémů."
    )

    return ComplianceCheckResponse(
        status=status,
        issues=issues,
        summary=summary,
    )


@router.get("/status")
async def get_ai_status():
    """Check AI service status and configuration."""
    return {
        "configured": bool(settings.anthropic_api_key),
        "model": settings.claude_model,
        "features": {
            "analysis": bool(settings.anthropic_api_key),
            "dividend_vs_salary": True,  # Works without AI (basic mode)
            "recommendations": True,  # Works without AI (basic mode)
            "compliance_check": True,  # Works without AI (basic mode)
            "tax_concepts": bool(settings.anthropic_api_key),
            "tax_deadlines": bool(settings.anthropic_api_key),
        },
    }
