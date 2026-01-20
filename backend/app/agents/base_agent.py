"""
Base Agent class for all AI agents.

Provides common functionality for interacting with Claude API.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import anthropic

from app.config import settings


@dataclass
class AgentResponse:
    """Response from an agent query."""

    answer: str
    sources: list[str]
    confidence: float
    reasoning: Optional[str] = None
    suggestions: list[str] = None

    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []


class BaseAgent(ABC):
    """
    Base class for all AI agents.

    Provides common functionality for:
    - Claude API interaction
    - Knowledge base access
    - Response parsing
    """

    def __init__(self):
        """Initialize the agent with Claude client."""
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is not configured")

        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model
        self.max_tokens = settings.claude_max_tokens

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        pass

    @abstractmethod
    def get_agent_name(self) -> str:
        """Return the name of this agent."""
        pass

    async def query(
        self,
        user_input: str,
        context: Optional[dict] = None,
        knowledge: Optional[str] = None,
    ) -> AgentResponse:
        """
        Query the agent with user input.

        Args:
            user_input: The user's question or request
            context: Additional context (company data, etc.)
            knowledge: Relevant knowledge from the knowledge base

        Returns:
            AgentResponse with the agent's answer
        """
        system_prompt = self.get_system_prompt()

        # Build the user message with context
        user_message = self._build_user_message(user_input, context, knowledge)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )

            return self._parse_response(response)

        except anthropic.APIError as e:
            return AgentResponse(
                answer=f"Omlouvám se, nastala chyba při komunikaci s AI: {str(e)}",
                sources=[],
                confidence=0.0,
                suggestions=["Zkuste to prosím znovu později"],
            )

    def _build_user_message(
        self,
        user_input: str,
        context: Optional[dict] = None,
        knowledge: Optional[str] = None,
    ) -> str:
        """Build the complete user message with context."""
        parts = []

        if knowledge:
            parts.append(f"RELEVANTNÍ ZNALOSTI:\n{knowledge}\n")

        if context:
            parts.append(f"KONTEXT:\n{self._format_context(context)}\n")

        parts.append(f"DOTAZ:\n{user_input}")

        return "\n---\n".join(parts)

    def _format_context(self, context: dict) -> str:
        """Format context dictionary for the prompt."""
        lines = []
        for key, value in context.items():
            if isinstance(value, dict):
                lines.append(f"{key}:")
                for k, v in value.items():
                    lines.append(f"  - {k}: {v}")
            elif isinstance(value, list):
                lines.append(f"{key}: {', '.join(str(v) for v in value)}")
            else:
                lines.append(f"{key}: {value}")
        return "\n".join(lines)

    def _parse_response(self, response) -> AgentResponse:
        """Parse Claude's response into AgentResponse."""
        content = response.content[0].text

        # Extract confidence based on response patterns
        confidence = 0.8  # Default confidence

        if any(word in content.lower() for word in ["nejsem si jistý", "pravděpodobně", "možná"]):
            confidence = 0.6
        elif any(word in content.lower() for word in ["určitě", "jednoznačně", "podle zákona"]):
            confidence = 0.9

        # Extract sources if mentioned
        sources = []
        if "§" in content or "zákon" in content.lower():
            # Simple extraction of legal references
            import re

            refs = re.findall(r"§\s*\d+[a-z]?\s*(?:odst\.\s*\d+)?(?:\s*zákona\s*č\.\s*\d+/\d+)?", content)
            sources.extend(refs)

        return AgentResponse(
            answer=content,
            sources=sources,
            confidence=confidence,
        )
