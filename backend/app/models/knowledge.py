"""
Knowledge Document model for storing tax law knowledge base.
"""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base


class KnowledgeCategory(enum.Enum):
    """Categories for knowledge documents."""

    INCOME_TAX = "income_tax"  # Daň z příjmu
    VAT = "vat"  # DPH
    SOCIAL_INSURANCE = "social_insurance"  # Sociální pojištění
    HEALTH_INSURANCE = "health_insurance"  # Zdravotní pojištění
    ACCOUNTING = "accounting"  # Účetnictví
    DIVIDENDS = "dividends"  # Dividendy
    DEPRECIATION = "depreciation"  # Odpisy
    APPSTORE = "appstore"  # App Store příjmy
    OSVC = "osvc"  # OSVČ - self-employed rules
    PAUSAL = "pausal"  # Paušální výdaje
    GENERAL = "general"  # Obecné
    OTHER = "other"  # Ostatní


class KnowledgeDocument(Base):
    """
    Knowledge document for AI tax advisor.

    Stores uploaded tax laws, regulations, and other knowledge
    that the AI agent can use for providing recommendations.
    """

    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True, index=True)

    # Document metadata
    title = Column(String(500), nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(Enum(KnowledgeCategory), default=KnowledgeCategory.GENERAL, nullable=False)

    # Content
    content = Column(Text, nullable=False)  # Full text content
    summary = Column(Text, nullable=True)  # AI-generated or manual summary

    # Source information
    source = Column(String(255), nullable=True)  # e.g., "Zákon č. 586/1992 Sb."
    source_url = Column(String(500), nullable=True)
    effective_date = Column(DateTime, nullable=True)  # When the law/rule became effective
    expiry_date = Column(DateTime, nullable=True)  # When it expires (if applicable)

    # Versioning
    version = Column(String(50), nullable=True)  # e.g., "2025", "v1.0"
    year = Column(Integer, nullable=True, index=True)  # Tax year it applies to

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)  # Verified by admin

    # Upload info
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    uploaded_by = relationship("User")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Search optimization
    keywords = Column(Text, nullable=True)  # Comma-separated keywords for search

    def __repr__(self) -> str:
        return f"<KnowledgeDocument(id={self.id}, title='{self.title[:50]}...', category='{self.category.value}')>"

    def to_context_string(self) -> str:
        """Convert document to string format for AI context."""
        parts = [f"# {self.title}"]

        if self.source:
            parts.append(f"Zdroj: {self.source}")

        if self.year:
            parts.append(f"Rok: {self.year}")

        if self.summary:
            parts.append(f"\nSouhrn: {self.summary}")

        parts.append(f"\n{self.content}")

        return "\n".join(parts)
