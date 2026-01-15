"""
Pydantic models for Memory System.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


class TodoStatus(str, Enum):
    """Status of a todo item."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class DecisionCategory(str, Enum):
    """Category of architectural/implementation decision."""

    ARCHITECTURE = "architecture"
    IMPLEMENTATION = "implementation"
    TECHNOLOGY = "technology"
    BUSINESS = "business"
    SECURITY = "security"


class ProjectMeta(BaseModel):
    """Project metadata."""

    project_name: str = "Daňový Poradce Pro"
    created_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    version: str = "0.1.0"
    phase: str = "MVP Development"


class ProjectSummary(BaseModel):
    """Current project summary for quick context."""

    one_liner: str = "AI-powered daňová a účetní platforma pro s.r.o. a FO"
    current_focus: Optional[str] = None
    blockers: list[str] = Field(default_factory=list)
    next_milestone: Optional[str] = None


class ArchitectureInfo(BaseModel):
    """Architecture configuration info."""

    backend: dict[str, Any] = Field(default_factory=lambda: {
        "framework": "FastAPI",
        "language": "Python 3.11",
        "database": "SQLite + SQLCipher",
        "key_patterns": ["Repository pattern", "Service layer", "Dependency injection"]
    })
    frontend: dict[str, Any] = Field(default_factory=lambda: {
        "framework": "React 18",
        "language": "TypeScript",
        "styling": "Tailwind CSS",
        "state": "Zustand"
    })
    ai: dict[str, Any] = Field(default_factory=lambda: {
        "provider": "Anthropic Claude",
        "model": "claude-sonnet-4-20250514",
        "patterns": ["Multi-agent", "RAG", "Tool use"]
    })


class Conventions(BaseModel):
    """Project coding conventions."""

    naming: dict[str, str] = Field(default_factory=lambda: {
        "files": "snake_case for Python, PascalCase for React components",
        "variables": "snake_case in Python, camelCase in TypeScript",
        "api_routes": "kebab-case URLs"
    })
    code_style: dict[str, str] = Field(default_factory=lambda: {
        "python": "Black formatter, Ruff linter",
        "typescript": "Prettier, ESLint"
    })
    git: dict[str, str] = Field(default_factory=lambda: {
        "branch_pattern": "feature/, bugfix/, hotfix/",
        "commit_style": "Conventional commits"
    })


class DomainKnowledge(BaseModel):
    """Domain-specific knowledge for tax advisor."""

    tax_rules: dict[str, Any] = Field(default_factory=lambda: {
        "corporate_tax_2025": 0.21,
        "dividend_withholding": 0.15,
        "depreciation_limit": 80000,
        "personal_tax_base": 0.15,
        "personal_tax_solidarity": 0.23
    })
    business_context: dict[str, Any] = Field(default_factory=lambda: {
        "company_type": "s.r.o. - jednatel bez zaměstnanců",
        "income_sources": ["App Store", "Zaměstnání"],
        "accounting_type": "Podvojné účetnictví"
    })


class ActiveContext(BaseModel):
    """Current active working context."""

    current_task: Optional[str] = None
    open_files: list[str] = Field(default_factory=list)
    recent_changes: list[str] = Field(default_factory=list)
    pending_questions: list[str] = Field(default_factory=list)


class ProjectContext(BaseModel):
    """
    Main project context - the primary memory structure.

    This is loaded at the start of each agent session and updated
    after significant actions.
    """

    meta: ProjectMeta = Field(default_factory=ProjectMeta)
    summary: ProjectSummary = Field(default_factory=ProjectSummary)
    architecture: ArchitectureInfo = Field(default_factory=ArchitectureInfo)
    file_structure: dict[str, str] = Field(default_factory=dict)
    conventions: Conventions = Field(default_factory=Conventions)
    domain_knowledge: DomainKnowledge = Field(default_factory=DomainKnowledge)
    active_context: ActiveContext = Field(default_factory=ActiveContext)

    def update_timestamp(self) -> None:
        """Update the last_updated timestamp."""
        self.meta.last_updated = datetime.now()


class SessionEntry(BaseModel):
    """Single entry in session history."""

    ts: datetime = Field(default_factory=datetime.now)
    type: str  # user_input, agent_action, agent_output, error
    agent: Optional[str] = None
    action: Optional[str] = None
    content: str
    result: Optional[str] = None
    session_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class Decision(BaseModel):
    """
    Architectural or implementation decision.

    Decisions are important choices that should be remembered
    and referenced in future sessions.
    """

    id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    category: DecisionCategory
    question: str
    decision: str
    reasoning: str
    alternatives_considered: list[str] = Field(default_factory=list)
    code_reference: Optional[str] = None
    user_approved: bool = False


class CodeFileInfo(BaseModel):
    """Information about a code file in the registry."""

    purpose: str
    exports: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    last_modified: datetime = Field(default_factory=datetime.now)
    status: str = "stable"  # stable, in_progress, needs_review, deprecated
    todos: list[str] = Field(default_factory=list)


class CodeRegistry(BaseModel):
    """Registry of all code files and modules."""

    files: dict[str, CodeFileInfo] = Field(default_factory=dict)
    modules: dict[str, dict[str, Any]] = Field(default_factory=dict)


class TodoItem(BaseModel):
    """A single todo item."""

    id: str
    content: str
    status: TodoStatus = TodoStatus.PENDING
    priority: int = 0  # Higher = more important
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    assigned_agent: Optional[str] = None
    related_files: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)


class ErrorRecord(BaseModel):
    """Record of an error and its resolution."""

    id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    error_type: str
    error_message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    resolution: Optional[str] = None
    resolved_at: Optional[datetime] = None
    prevention_notes: Optional[str] = None


class UserPreferences(BaseModel):
    """User preferences for agent behavior."""

    language: str = "cs"  # Czech
    auto_confirm: bool = False
    verbose_output: bool = True
    preferred_model: str = "claude-sonnet-4-20250514"
    notification_level: str = "all"  # all, important, errors


class SearchResult(BaseModel):
    """Result from semantic search."""

    source: str  # history, decisions, code
    content: str
    relevance_score: float
    timestamp: Optional[datetime] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
