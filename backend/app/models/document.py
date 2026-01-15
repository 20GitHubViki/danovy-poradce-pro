"""
Document model for storing uploaded files and OCR data.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.transaction import Transaction
    from app.models.invoice import Invoice


class Document(Base, TimestampMixin):
    """
    Represents an uploaded document (invoice scan, receipt, etc.).

    Attributes:
        filename: Original filename
        file_path: Path to stored file
        mime_type: MIME type of the file
        ocr_text: Extracted text from OCR
        ocr_data: Structured OCR data (JSON)
    """

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)

    # File info
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # OCR data
    ocr_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ocr_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ocr_processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ocr_confidence: Mapped[Optional[float]] = mapped_column(nullable=True)

    # Classification
    document_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    detected_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    detected_amount: Mapped[Optional[float]] = mapped_column(nullable=True)

    # Relationships
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="document")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="document")

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, filename='{self.filename}')>"
