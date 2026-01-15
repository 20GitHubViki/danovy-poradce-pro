"""
Memory Manager - Central manager for all memory operations.

This is the core of the memory system, providing:
- Context loading and saving
- Session history tracking
- Decision recording
- Code registry management
- Semantic search across all memory
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

import aiofiles
import aiofiles.os

from app.memory.models import (
    ProjectContext,
    SessionEntry,
    Decision,
    CodeFileInfo,
    CodeRegistry,
    TodoItem,
    TodoStatus,
    ErrorRecord,
    UserPreferences,
    SearchResult,
)


class MemoryManager:
    """
    Central manager for all memory operations.

    Usage:
        memory = MemoryManager()
        context = await memory.load_context()
        await memory.record_action(...)
        await memory.update_context(...)
    """

    def __init__(self, memory_dir: Path | str = ".agent-memory"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self._current_session_id: Optional[str] = None

    @property
    def current_session_id(self) -> str:
        """Get or create current session ID."""
        if self._current_session_id is None:
            self._current_session_id = f"sess_{uuid.uuid4().hex[:8]}"
        return self._current_session_id

    def start_new_session(self) -> str:
        """Start a new session and return the session ID."""
        self._current_session_id = f"sess_{uuid.uuid4().hex[:8]}"
        return self._current_session_id

    # ==================== FILE OPERATIONS ====================

    async def _load_json(self, filename: str) -> Optional[dict]:
        """Load JSON file from memory directory."""
        path = self.memory_dir / filename
        if not path.exists():
            return None
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            content = await f.read()
            return json.loads(content)

    async def _save_json(self, filename: str, data: dict | list) -> None:
        """Save data to JSON file in memory directory."""
        path = self.memory_dir / filename
        async with aiofiles.open(path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(data, indent=2, ensure_ascii=False, default=str))

    async def _append_jsonl(self, filename: str, entry: dict) -> None:
        """Append entry to JSONL file (one JSON object per line)."""
        path = self.memory_dir / filename
        async with aiofiles.open(path, "a", encoding="utf-8") as f:
            await f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")

    async def _read_jsonl(self, filename: str, limit: Optional[int] = None) -> list[dict]:
        """Read JSONL file, optionally limiting to last N entries."""
        path = self.memory_dir / filename
        if not path.exists():
            return []

        entries = []
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            async for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))

        if limit:
            return entries[-limit:]
        return entries

    # ==================== CONTEXT OPERATIONS ====================

    async def load_context(self) -> ProjectContext:
        """
        Load the current project context.

        Returns default context if none exists.
        """
        data = await self._load_json("project_context.json")
        if data:
            return ProjectContext.model_validate(data)
        return ProjectContext()

    async def save_context(self, context: ProjectContext) -> None:
        """Save project context to file."""
        context.update_timestamp()
        await self._save_json("project_context.json", context.model_dump())

    async def update_context(self, updates: dict[str, Any]) -> ProjectContext:
        """
        Update specific fields in project context.

        Args:
            updates: Dictionary of field paths and values to update

        Returns:
            Updated ProjectContext
        """
        context = await self.load_context()

        for key, value in updates.items():
            if "." in key:
                # Handle nested updates like "summary.current_focus"
                parts = key.split(".")
                obj = context
                for part in parts[:-1]:
                    obj = getattr(obj, part)
                setattr(obj, parts[-1], value)
            else:
                setattr(context, key, value)

        await self.save_context(context)
        return context

    async def update_file_structure(self, file_path: str, description: str) -> None:
        """Add or update file in the file structure map."""
        context = await self.load_context()
        context.file_structure[file_path] = description
        await self.save_context(context)

    async def set_current_task(self, task: Optional[str]) -> None:
        """Set the current active task."""
        await self.update_context({"active_context.current_task": task})

    async def add_recent_change(self, change: str) -> None:
        """Add a change to recent changes list (keeps last 10)."""
        context = await self.load_context()
        context.active_context.recent_changes.append(change)
        context.active_context.recent_changes = context.active_context.recent_changes[-10:]
        await self.save_context(context)

    # ==================== SESSION HISTORY ====================

    async def record_action(
        self,
        action_type: str,
        content: str,
        agent: Optional[str] = None,
        action: Optional[str] = None,
        result: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """
        Record an action to session history.

        Args:
            action_type: Type of entry (user_input, agent_action, agent_output, error)
            content: Main content/description
            agent: Agent that performed the action
            action: Specific action taken
            result: Result of the action
            metadata: Additional metadata
        """
        entry = SessionEntry(
            ts=datetime.now(),
            type=action_type,
            agent=agent,
            action=action,
            content=content,
            result=result,
            session_id=self.current_session_id,
            metadata=metadata or {},
        )
        await self._append_jsonl("session_history.jsonl", entry.model_dump())

    async def record_user_input(self, content: str) -> None:
        """Convenience method to record user input."""
        await self.record_action("user_input", content)

    async def record_agent_output(self, content: str, agent: str = "orchestrator") -> None:
        """Convenience method to record agent output."""
        await self.record_action("agent_output", content, agent=agent)

    async def get_recent_history(self, limit: int = 20) -> list[SessionEntry]:
        """Get recent session history entries."""
        entries = await self._read_jsonl("session_history.jsonl", limit=limit)
        return [SessionEntry.model_validate(e) for e in entries]

    async def get_session_history(self, session_id: str) -> list[SessionEntry]:
        """Get all entries for a specific session."""
        all_entries = await self._read_jsonl("session_history.jsonl")
        return [
            SessionEntry.model_validate(e)
            for e in all_entries
            if e.get("session_id") == session_id
        ]

    # ==================== DECISIONS ====================

    async def record_decision(
        self,
        category: str,
        question: str,
        decision: str,
        reasoning: str,
        alternatives: Optional[list[str]] = None,
        code_reference: Optional[str] = None,
        user_approved: bool = False,
    ) -> Decision:
        """
        Record an important decision.

        Returns the created Decision object with assigned ID.
        """
        data = await self._load_json("decisions.json") or {"decisions": []}

        dec = Decision(
            id=f"dec_{len(data['decisions']) + 1:03d}",
            timestamp=datetime.now(),
            category=category,
            question=question,
            decision=decision,
            reasoning=reasoning,
            alternatives_considered=alternatives or [],
            code_reference=code_reference,
            user_approved=user_approved,
        )

        data["decisions"].append(dec.model_dump())
        await self._save_json("decisions.json", data)

        # Also record in session history
        await self.record_action(
            "decision",
            f"Decision {dec.id}: {question} -> {decision}",
            metadata={"decision_id": dec.id},
        )

        return dec

    async def get_decisions(
        self,
        category: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[Decision]:
        """Get decisions, optionally filtered by category."""
        data = await self._load_json("decisions.json") or {"decisions": []}
        decisions = [Decision.model_validate(d) for d in data["decisions"]]

        if category:
            decisions = [d for d in decisions if d.category == category]

        if limit:
            decisions = decisions[-limit:]

        return decisions

    async def get_decision_by_id(self, decision_id: str) -> Optional[Decision]:
        """Get a specific decision by ID."""
        decisions = await self.get_decisions()
        for d in decisions:
            if d.id == decision_id:
                return d
        return None

    # ==================== CODE REGISTRY ====================

    async def get_code_registry(self) -> CodeRegistry:
        """Load the code registry."""
        data = await self._load_json("code_registry.json")
        if data:
            return CodeRegistry.model_validate(data)
        return CodeRegistry()

    async def update_code_file(
        self,
        file_path: str,
        purpose: str,
        exports: Optional[list[str]] = None,
        dependencies: Optional[list[str]] = None,
        status: str = "stable",
        todos: Optional[list[str]] = None,
    ) -> None:
        """Update information about a code file."""
        registry = await self.get_code_registry()

        registry.files[file_path] = CodeFileInfo(
            purpose=purpose,
            exports=exports or [],
            dependencies=dependencies or [],
            last_modified=datetime.now(),
            status=status,
            todos=todos or [],
        )

        await self._save_json("code_registry.json", registry.model_dump())

        # Also update file structure in context
        await self.update_file_structure(file_path, purpose)

    async def get_related_files(self, file_path: str) -> list[str]:
        """Find files related to the given file (by dependencies/imports)."""
        registry = await self.get_code_registry()

        if file_path not in registry.files:
            return []

        file_info = registry.files[file_path]
        related = set()

        # Files this file depends on
        for dep in file_info.dependencies:
            for path in registry.files:
                if dep in path:
                    related.add(path)

        # Files that depend on this file
        for path, info in registry.files.items():
            if file_path in info.dependencies:
                related.add(path)

        return list(related)

    async def update_module_status(
        self,
        module_name: str,
        files: list[str],
        status: str,
        completion: float,
    ) -> None:
        """Update module status in registry."""
        registry = await self.get_code_registry()
        registry.modules[module_name] = {
            "files": files,
            "status": status,
            "completion": completion,
        }
        await self._save_json("code_registry.json", registry.model_dump())

    # ==================== TODOS ====================

    async def get_todos(self, status: Optional[TodoStatus] = None) -> list[TodoItem]:
        """Get todo items, optionally filtered by status."""
        data = await self._load_json("todos.json") or {"todos": []}
        todos = [TodoItem.model_validate(t) for t in data["todos"]]

        if status:
            todos = [t for t in todos if t.status == status]

        return todos

    async def add_todo(
        self,
        content: str,
        priority: int = 0,
        related_files: Optional[list[str]] = None,
    ) -> TodoItem:
        """Add a new todo item."""
        data = await self._load_json("todos.json") or {"todos": []}

        todo = TodoItem(
            id=f"todo_{uuid.uuid4().hex[:8]}",
            content=content,
            priority=priority,
            related_files=related_files or [],
        )

        data["todos"].append(todo.model_dump())
        await self._save_json("todos.json", data)
        return todo

    async def update_todo_status(
        self,
        todo_id: str,
        status: TodoStatus,
    ) -> Optional[TodoItem]:
        """Update the status of a todo item."""
        data = await self._load_json("todos.json") or {"todos": []}

        for i, t in enumerate(data["todos"]):
            if t["id"] == todo_id:
                data["todos"][i]["status"] = status.value
                if status == TodoStatus.COMPLETED:
                    data["todos"][i]["completed_at"] = datetime.now().isoformat()
                await self._save_json("todos.json", data)
                return TodoItem.model_validate(data["todos"][i])

        return None

    # ==================== ERRORS ====================

    async def record_error(
        self,
        error_type: str,
        error_message: str,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
    ) -> ErrorRecord:
        """Record an error for future reference."""
        data = await self._load_json("errors.json") or {"errors": []}

        error = ErrorRecord(
            id=f"err_{uuid.uuid4().hex[:8]}",
            error_type=error_type,
            error_message=error_message,
            file_path=file_path,
            line_number=line_number,
        )

        data["errors"].append(error.model_dump())
        await self._save_json("errors.json", data)

        # Also record in session history
        await self.record_action(
            "error",
            f"{error_type}: {error_message}",
            metadata={"error_id": error.id, "file": file_path},
        )

        return error

    async def resolve_error(
        self,
        error_id: str,
        resolution: str,
        prevention_notes: Optional[str] = None,
    ) -> None:
        """Mark an error as resolved with resolution notes."""
        data = await self._load_json("errors.json") or {"errors": []}

        for i, e in enumerate(data["errors"]):
            if e["id"] == error_id:
                data["errors"][i]["resolution"] = resolution
                data["errors"][i]["resolved_at"] = datetime.now().isoformat()
                data["errors"][i]["prevention_notes"] = prevention_notes
                await self._save_json("errors.json", data)
                return

    # ==================== USER PREFERENCES ====================

    async def get_preferences(self) -> UserPreferences:
        """Get user preferences."""
        data = await self._load_json("user_preferences.json")
        if data:
            return UserPreferences.model_validate(data)
        return UserPreferences()

    async def save_preferences(self, prefs: UserPreferences) -> None:
        """Save user preferences."""
        await self._save_json("user_preferences.json", prefs.model_dump())

    # ==================== SEARCH ====================

    async def search(
        self,
        query: str,
        search_in: Optional[list[str]] = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        """
        Search across memory components.

        This is a simple text-based search. For production,
        implement semantic search with embeddings.

        Args:
            query: Search query
            search_in: List of sources to search (history, decisions, code)
            limit: Maximum results to return
        """
        search_in = search_in or ["history", "decisions", "code"]
        results: list[SearchResult] = []
        query_lower = query.lower()

        if "history" in search_in:
            history = await self.get_recent_history(limit=100)
            for entry in history:
                if query_lower in entry.content.lower():
                    results.append(SearchResult(
                        source="history",
                        content=entry.content,
                        relevance_score=0.8,
                        timestamp=entry.ts,
                        metadata={"session_id": entry.session_id, "type": entry.type},
                    ))

        if "decisions" in search_in:
            decisions = await self.get_decisions()
            for dec in decisions:
                if (
                    query_lower in dec.question.lower()
                    or query_lower in dec.decision.lower()
                    or query_lower in dec.reasoning.lower()
                ):
                    results.append(SearchResult(
                        source="decisions",
                        content=f"{dec.question} -> {dec.decision}",
                        relevance_score=0.9,
                        timestamp=dec.timestamp,
                        metadata={"decision_id": dec.id, "category": dec.category},
                    ))

        if "code" in search_in:
            registry = await self.get_code_registry()
            for path, info in registry.files.items():
                if query_lower in path.lower() or query_lower in info.purpose.lower():
                    results.append(SearchResult(
                        source="code",
                        content=f"{path}: {info.purpose}",
                        relevance_score=0.7,
                        timestamp=info.last_modified,
                        metadata={"file_path": path, "status": info.status},
                    ))

        # Sort by relevance and limit
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:limit]

    # ==================== SUMMARY GENERATION ====================

    async def generate_session_summary(self) -> str:
        """Generate a summary of the current session."""
        history = await self.get_session_history(self.current_session_id)

        if not history:
            return "No actions in current session."

        user_inputs = [e for e in history if e.type == "user_input"]
        actions = [e for e in history if e.type == "agent_action"]
        errors = [e for e in history if e.type == "error"]

        summary_parts = [
            f"Session {self.current_session_id}:",
            f"- {len(user_inputs)} user requests",
            f"- {len(actions)} agent actions",
        ]

        if errors:
            summary_parts.append(f"- {len(errors)} errors encountered")

        if user_inputs:
            summary_parts.append(f"\nLast request: {user_inputs[-1].content[:100]}...")

        return "\n".join(summary_parts)

    async def generate_project_summary(self) -> str:
        """Generate a comprehensive project summary for agent context."""
        context = await self.load_context()
        decisions = await self.get_decisions(limit=5)
        todos = await self.get_todos(status=TodoStatus.IN_PROGRESS)
        registry = await self.get_code_registry()

        summary_parts = [
            f"# {context.meta.project_name} v{context.meta.version}",
            f"Phase: {context.meta.phase}",
            f"\n## Current Focus",
            context.summary.current_focus or "Not set",
        ]

        if context.summary.blockers:
            summary_parts.append(f"\n## Blockers")
            for blocker in context.summary.blockers:
                summary_parts.append(f"- {blocker}")

        if todos:
            summary_parts.append(f"\n## In Progress ({len(todos)} items)")
            for todo in todos[:3]:
                summary_parts.append(f"- {todo.content}")

        if decisions:
            summary_parts.append(f"\n## Recent Decisions")
            for dec in decisions:
                summary_parts.append(f"- {dec.id}: {dec.decision[:50]}...")

        summary_parts.append(f"\n## Codebase ({len(registry.files)} files)")

        return "\n".join(summary_parts)

    # ==================== BACKUP & EXPORT ====================

    async def export_memory(self, output_path: Path) -> None:
        """Export all memory to a single JSON file."""
        export_data = {
            "exported_at": datetime.now().isoformat(),
            "context": (await self.load_context()).model_dump(),
            "decisions": (await self._load_json("decisions.json")) or {"decisions": []},
            "code_registry": (await self.get_code_registry()).model_dump(),
            "todos": (await self._load_json("todos.json")) or {"todos": []},
            "errors": (await self._load_json("errors.json")) or {"errors": []},
            "preferences": (await self.get_preferences()).model_dump(),
        }

        async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(export_data, indent=2, ensure_ascii=False, default=str))

    async def import_memory(self, input_path: Path) -> None:
        """Import memory from exported file."""
        async with aiofiles.open(input_path, "r", encoding="utf-8") as f:
            content = await f.read()
            data = json.loads(content)

        if "context" in data:
            await self._save_json("project_context.json", data["context"])
        if "decisions" in data:
            await self._save_json("decisions.json", data["decisions"])
        if "code_registry" in data:
            await self._save_json("code_registry.json", data["code_registry"])
        if "todos" in data:
            await self._save_json("todos.json", data["todos"])
        if "errors" in data:
            await self._save_json("errors.json", data["errors"])
        if "preferences" in data:
            await self._save_json("user_preferences.json", data["preferences"])
