"""
Knowledge Base module for Daňový Poradce Pro.

Provides structured access to Czech tax laws, rules, and templates.
"""

from app.knowledge.loader import KnowledgeBaseLoader
from app.knowledge.search import KnowledgeSearch

__all__ = [
    "KnowledgeBaseLoader",
    "KnowledgeSearch",
]
