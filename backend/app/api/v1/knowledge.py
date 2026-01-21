"""
Knowledge Base API endpoints.

Provides CRUD operations for tax law knowledge documents
that the AI agent uses for recommendations.
"""

from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models.knowledge import KnowledgeDocument, KnowledgeCategory
from app.models.user import User
from app.api.v1.auth import get_current_user, get_admin_user

router = APIRouter()


# --- Pydantic Schemas ---


class KnowledgeCreate(BaseModel):
    """Request to create a new knowledge document."""

    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    category: KnowledgeCategory = KnowledgeCategory.GENERAL
    content: str = Field(..., min_length=1)
    summary: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    version: Optional[str] = None
    year: Optional[int] = None
    keywords: Optional[str] = None


class KnowledgeUpdate(BaseModel):
    """Request to update a knowledge document."""

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    category: Optional[KnowledgeCategory] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    version: Optional[str] = None
    year: Optional[int] = None
    keywords: Optional[str] = None
    is_active: Optional[bool] = None


class KnowledgeResponse(BaseModel):
    """Knowledge document response."""

    id: int
    title: str
    description: Optional[str]
    category: str
    content: str
    summary: Optional[str]
    source: Optional[str]
    source_url: Optional[str]
    effective_date: Optional[datetime]
    expiry_date: Optional[datetime]
    version: Optional[str]
    year: Optional[int]
    keywords: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class KnowledgeListResponse(BaseModel):
    """Paginated list of knowledge documents."""

    items: List[KnowledgeResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class KnowledgeSearchResponse(BaseModel):
    """Search result with relevance."""

    id: int
    title: str
    category: str
    summary: Optional[str]
    source: Optional[str]
    year: Optional[int]
    relevance_snippet: str


# --- API Endpoints ---


@router.post("/", response_model=KnowledgeResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge(
    data: KnowledgeCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Create a new knowledge document.

    Upload tax law, regulation, or other knowledge for the AI advisor.
    """
    document = KnowledgeDocument(
        title=data.title,
        description=data.description,
        category=data.category,
        content=data.content,
        summary=data.summary,
        source=data.source,
        source_url=data.source_url,
        effective_date=data.effective_date,
        expiry_date=data.expiry_date,
        version=data.version,
        year=data.year,
        keywords=data.keywords,
        uploaded_by_id=user.id,
        is_active=True,
        is_verified=False,
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    return KnowledgeResponse(
        id=document.id,
        title=document.title,
        description=document.description,
        category=document.category.value,
        content=document.content,
        summary=document.summary,
        source=document.source,
        source_url=document.source_url,
        effective_date=document.effective_date,
        expiry_date=document.expiry_date,
        version=document.version,
        year=document.year,
        keywords=document.keywords,
        is_active=document.is_active,
        is_verified=document.is_verified,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


@router.get("/", response_model=KnowledgeListResponse)
async def list_knowledge(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[KnowledgeCategory] = None,
    year: Optional[int] = None,
    is_active: Optional[bool] = True,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    List knowledge documents with filtering and pagination.
    """
    query = db.query(KnowledgeDocument)

    if category:
        query = query.filter(KnowledgeDocument.category == category)
    if year:
        query = query.filter(KnowledgeDocument.year == year)
    if is_active is not None:
        query = query.filter(KnowledgeDocument.is_active == is_active)

    total = query.count()
    total_pages = (total + page_size - 1) // page_size

    documents = (
        query.order_by(KnowledgeDocument.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [
        KnowledgeResponse(
            id=doc.id,
            title=doc.title,
            description=doc.description,
            category=doc.category.value,
            content=doc.content,
            summary=doc.summary,
            source=doc.source,
            source_url=doc.source_url,
            effective_date=doc.effective_date,
            expiry_date=doc.expiry_date,
            version=doc.version,
            year=doc.year,
            keywords=doc.keywords,
            is_active=doc.is_active,
            is_verified=doc.is_verified,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )
        for doc in documents
    ]

    return KnowledgeListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/search", response_model=List[KnowledgeSearchResponse])
async def search_knowledge(
    q: str = Query(..., min_length=2),
    category: Optional[KnowledgeCategory] = None,
    year: Optional[int] = None,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Search knowledge documents by text query.

    Searches in title, content, summary, and keywords.
    """
    query = db.query(KnowledgeDocument).filter(KnowledgeDocument.is_active == True)

    # Text search (basic LIKE search - for production use full-text search)
    search_term = f"%{q}%"
    query = query.filter(
        or_(
            KnowledgeDocument.title.ilike(search_term),
            KnowledgeDocument.content.ilike(search_term),
            KnowledgeDocument.summary.ilike(search_term),
            KnowledgeDocument.keywords.ilike(search_term),
        )
    )

    if category:
        query = query.filter(KnowledgeDocument.category == category)
    if year:
        query = query.filter(KnowledgeDocument.year == year)

    documents = query.limit(limit).all()

    results = []
    for doc in documents:
        # Create relevance snippet
        content_lower = doc.content.lower()
        q_lower = q.lower()
        pos = content_lower.find(q_lower)

        if pos != -1:
            start = max(0, pos - 50)
            end = min(len(doc.content), pos + len(q) + 100)
            snippet = doc.content[start:end]
            if start > 0:
                snippet = "..." + snippet
            if end < len(doc.content):
                snippet = snippet + "..."
        else:
            snippet = doc.content[:150] + "..." if len(doc.content) > 150 else doc.content

        results.append(
            KnowledgeSearchResponse(
                id=doc.id,
                title=doc.title,
                category=doc.category.value,
                summary=doc.summary,
                source=doc.source,
                year=doc.year,
                relevance_snippet=snippet,
            )
        )

    return results


@router.get("/categories")
async def list_categories():
    """
    List all available knowledge categories.
    """
    return {
        "categories": [
            {"value": cat.value, "label": _get_category_label(cat)}
            for cat in KnowledgeCategory
        ]
    }


def _get_category_label(cat: KnowledgeCategory) -> str:
    """Get Czech label for category."""
    labels = {
        KnowledgeCategory.INCOME_TAX: "Daň z příjmu",
        KnowledgeCategory.VAT: "DPH",
        KnowledgeCategory.SOCIAL_INSURANCE: "Sociální pojištění",
        KnowledgeCategory.HEALTH_INSURANCE: "Zdravotní pojištění",
        KnowledgeCategory.ACCOUNTING: "Účetnictví",
        KnowledgeCategory.DIVIDENDS: "Dividendy",
        KnowledgeCategory.DEPRECIATION: "Odpisy",
        KnowledgeCategory.APPSTORE: "App Store příjmy",
        KnowledgeCategory.OSVC: "OSVČ",
        KnowledgeCategory.PAUSAL: "Paušální výdaje",
        KnowledgeCategory.GENERAL: "Obecné",
        KnowledgeCategory.OTHER: "Ostatní",
    }
    return labels.get(cat, cat.value)


@router.get("/{document_id}", response_model=KnowledgeResponse)
async def get_knowledge(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Get a specific knowledge document by ID.
    """
    document = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == document_id).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dokument nenalezen",
        )

    return KnowledgeResponse(
        id=document.id,
        title=document.title,
        description=document.description,
        category=document.category.value,
        content=document.content,
        summary=document.summary,
        source=document.source,
        source_url=document.source_url,
        effective_date=document.effective_date,
        expiry_date=document.expiry_date,
        version=document.version,
        year=document.year,
        keywords=document.keywords,
        is_active=document.is_active,
        is_verified=document.is_verified,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


@router.put("/{document_id}", response_model=KnowledgeResponse)
async def update_knowledge(
    document_id: int,
    data: KnowledgeUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Update a knowledge document.
    """
    document = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == document_id).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dokument nenalezen",
        )

    # Update fields if provided
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(document, field, value)

    db.commit()
    db.refresh(document)

    return KnowledgeResponse(
        id=document.id,
        title=document.title,
        description=document.description,
        category=document.category.value,
        content=document.content,
        summary=document.summary,
        source=document.source,
        source_url=document.source_url,
        effective_date=document.effective_date,
        expiry_date=document.expiry_date,
        version=document.version,
        year=document.year,
        keywords=document.keywords,
        is_active=document.is_active,
        is_verified=document.is_verified,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Delete a knowledge document.
    """
    document = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == document_id).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dokument nenalezen",
        )

    db.delete(document)
    db.commit()

    return None


@router.post("/{document_id}/verify", response_model=KnowledgeResponse)
async def verify_knowledge(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_admin_user),
):
    """
    Verify a knowledge document (admin only).

    Verified documents are prioritized in AI recommendations.
    """
    document = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == document_id).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dokument nenalezen",
        )

    document.is_verified = True
    db.commit()
    db.refresh(document)

    return KnowledgeResponse(
        id=document.id,
        title=document.title,
        description=document.description,
        category=document.category.value,
        content=document.content,
        summary=document.summary,
        source=document.source,
        source_url=document.source_url,
        effective_date=document.effective_date,
        expiry_date=document.expiry_date,
        version=document.version,
        year=document.year,
        keywords=document.keywords,
        is_active=document.is_active,
        is_verified=document.is_verified,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


# --- Context Building for AI ---


def get_knowledge_context(
    db: Session,
    category: Optional[KnowledgeCategory] = None,
    year: Optional[int] = None,
    query: Optional[str] = None,
    limit: int = 5,
) -> str:
    """
    Build knowledge context string for AI agent.

    This function is used internally by the AI endpoint to fetch
    relevant knowledge for the agent's context.
    """
    q = db.query(KnowledgeDocument).filter(
        KnowledgeDocument.is_active == True
    )

    # Prioritize verified documents
    q = q.order_by(KnowledgeDocument.is_verified.desc())

    if category:
        q = q.filter(KnowledgeDocument.category == category)
    if year:
        q = q.filter(KnowledgeDocument.year == year)

    if query:
        search_term = f"%{query}%"
        q = q.filter(
            or_(
                KnowledgeDocument.title.ilike(search_term),
                KnowledgeDocument.content.ilike(search_term),
                KnowledgeDocument.keywords.ilike(search_term),
            )
        )

    documents = q.limit(limit).all()

    if not documents:
        return ""

    context_parts = ["RELEVANTNÍ ZNALOSTNÍ BÁZE:"]
    for doc in documents:
        context_parts.append(doc.to_context_string())
        context_parts.append("---")

    return "\n\n".join(context_parts)
