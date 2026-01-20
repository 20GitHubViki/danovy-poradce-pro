"""
Memory System API endpoints.

Provides REST interface for the AI agent memory system.
"""

from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.config import settings
from app.memory import (
    MemoryManager,
    ProjectContext,
    Decision,
    SearchResult,
)
from app.memory.models import TodoStatus, DecisionCategory

router = APIRouter()

# Initialize memory manager
memory = MemoryManager(settings.memory_dir)


# === Request/Response Models ===


class UpdateContextRequest(BaseModel):
    """Request for updating project context."""

    updates: dict


class RecordActionRequest(BaseModel):
    """Request for recording an action."""

    action_type: str
    content: str
    agent: Optional[str] = None
    action: Optional[str] = None
    result: Optional[str] = None


class RecordDecisionRequest(BaseModel):
    """Request for recording a decision."""

    category: DecisionCategory
    question: str
    decision: str
    reasoning: str
    alternatives: list[str] = Field(default_factory=list)
    code_reference: Optional[str] = None


class UpdateCodeFileRequest(BaseModel):
    """Request for updating code file info."""

    file_path: str
    purpose: str
    exports: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    status: str = "stable"
    todos: list[str] = Field(default_factory=list)


class AddTodoRequest(BaseModel):
    """Request for adding a todo."""

    content: str
    priority: int = 0
    related_files: list[str] = Field(default_factory=list)


class SearchRequest(BaseModel):
    """Request for searching memory."""

    query: str
    search_in: list[str] = Field(default=["history", "decisions", "code"])
    limit: int = 10


# === Context Endpoints ===


@router.get("/context", response_model=ProjectContext)
async def get_context():
    """Get current project context."""
    return await memory.load_context()


@router.put("/context", response_model=ProjectContext)
async def update_context(request: UpdateContextRequest):
    """Update project context with specific fields."""
    return await memory.update_context(request.updates)


@router.get("/summary")
async def get_summary(scope: str = Query("project", pattern="^(project|session)$")):
    """Get summary of project or current session."""
    if scope == "project":
        return {"summary": await memory.generate_project_summary()}
    else:
        return {"summary": await memory.generate_session_summary()}


# === Session Endpoints ===


@router.post("/session/start")
async def start_session():
    """Start a new session."""
    session_id = memory.start_new_session()
    return {"session_id": session_id}


@router.get("/session/current")
async def get_current_session():
    """Get current session ID and history."""
    history = await memory.get_session_history(memory.current_session_id)
    return {
        "session_id": memory.current_session_id,
        "entries_count": len(history),
        "history": history[-10:],  # Last 10 entries
    }


# === History Endpoints ===


@router.post("/history/record")
async def record_action(request: RecordActionRequest):
    """Record an action to session history."""
    await memory.record_action(
        action_type=request.action_type,
        content=request.content,
        agent=request.agent,
        action=request.action,
        result=request.result,
    )
    return {"status": "recorded"}


@router.get("/history")
async def get_history(limit: int = Query(20, ge=1, le=100)):
    """Get recent session history."""
    entries = await memory.get_recent_history(limit=limit)
    return {"entries": entries}


# === Decision Endpoints ===


@router.post("/decisions", response_model=Decision)
async def record_decision(request: RecordDecisionRequest):
    """Record a new decision."""
    return await memory.record_decision(
        category=request.category.value,
        question=request.question,
        decision=request.decision,
        reasoning=request.reasoning,
        alternatives=request.alternatives,
        code_reference=request.code_reference,
    )


@router.get("/decisions")
async def get_decisions(
    category: Optional[DecisionCategory] = None,
    limit: int = Query(20, ge=1, le=100),
):
    """Get decisions, optionally filtered by category."""
    decisions = await memory.get_decisions(
        category=category.value if category else None,
        limit=limit,
    )
    return {"decisions": decisions}


@router.get("/decisions/{decision_id}")
async def get_decision(decision_id: str):
    """Get a specific decision by ID."""
    decision = await memory.get_decision_by_id(decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    return decision


# === Code Registry Endpoints ===


@router.get("/code-registry")
async def get_code_registry():
    """Get the full code registry."""
    return await memory.get_code_registry()


@router.post("/code-registry/file")
async def update_code_file(request: UpdateCodeFileRequest):
    """Update information about a code file."""
    await memory.update_code_file(
        file_path=request.file_path,
        purpose=request.purpose,
        exports=request.exports,
        dependencies=request.dependencies,
        status=request.status,
        todos=request.todos,
    )
    return {"status": "updated"}


@router.get("/code-registry/related/{file_path:path}")
async def get_related_files(file_path: str):
    """Get files related to a specific file."""
    related = await memory.get_related_files(file_path)
    return {"file": file_path, "related": related}


# === Todo Endpoints ===


@router.get("/todos")
async def get_todos(status: Optional[TodoStatus] = None):
    """Get todos, optionally filtered by status."""
    todos = await memory.get_todos(status=status)
    return {"todos": todos}


@router.post("/todos")
async def add_todo(request: AddTodoRequest):
    """Add a new todo item."""
    todo = await memory.add_todo(
        content=request.content,
        priority=request.priority,
        related_files=request.related_files,
    )
    return todo


@router.put("/todos/{todo_id}/status")
async def update_todo_status(todo_id: str, status: TodoStatus):
    """Update the status of a todo item."""
    todo = await memory.update_todo_status(todo_id, status)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo


# === Search Endpoints ===


@router.post("/search")
async def search_memory(request: SearchRequest):
    """Search across memory components."""
    results = await memory.search(
        query=request.query,
        search_in=request.search_in,
        limit=request.limit,
    )
    return {"query": request.query, "results": results}


# === Export/Import Endpoints ===


@router.get("/export")
async def export_memory():
    """Export all memory to JSON."""
    export_path = settings.memory_dir / "export.json"
    await memory.export_memory(export_path)
    return {"status": "exported", "path": str(export_path)}


@router.post("/import")
async def import_memory(path: str):
    """Import memory from JSON file."""
    import_path = Path(path)
    if not import_path.exists():
        raise HTTPException(status_code=404, detail="Import file not found")
    await memory.import_memory(import_path)
    return {"status": "imported"}
