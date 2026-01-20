"""
Knowledge Base Loader.

Loads and manages Czech tax law knowledge from JSON files.
"""

import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

from app.config import settings


@dataclass
class LawSection:
    """A section of a law."""

    section: str
    title: str
    content: str
    application: list[str] = field(default_factory=list)
    rate: Optional[float] = None
    notes: Optional[str] = None


@dataclass
class TaxLaw:
    """Representation of a tax law."""

    law_id: str
    name: str
    valid_from: str
    sections: list[LawSection]
    rates: dict[str, float]
    year: int


@dataclass
class TaxRule:
    """A tax rule or procedure."""

    rule_id: str
    title: str
    description: str
    conditions: list[dict]
    process: list[str]
    taxation: dict
    law_references: list[str] = field(default_factory=list)


class KnowledgeBaseLoader:
    """
    Loads and manages knowledge base files.

    Knowledge is organized by:
    - Laws: Tax legislation by year
    - Rules: Specific tax procedures and rules
    - Templates: Document templates
    """

    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize the knowledge base loader.

        Args:
            base_dir: Base directory for knowledge files
        """
        self.base_dir = base_dir or settings.knowledge_base_dir
        self._laws_cache: dict[tuple[str, int], TaxLaw] = {}
        self._rules_cache: dict[str, TaxRule] = {}

    def _load_json(self, path: Path) -> Optional[dict]:
        """Load a JSON file."""
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def load_law(self, law_type: str, year: int) -> Optional[TaxLaw]:
        """
        Load a specific tax law for a year.

        Args:
            law_type: Type of law (income_tax, corporate_tax, vat, etc.)
            year: Tax year

        Returns:
            TaxLaw object or None if not found
        """
        cache_key = (law_type, year)
        if cache_key in self._laws_cache:
            return self._laws_cache[cache_key]

        path = self.base_dir / "laws" / str(year) / f"{law_type}.json"
        data = self._load_json(path)

        if not data:
            return None

        sections = [
            LawSection(
                section=s.get("section", ""),
                title=s.get("title", ""),
                content=s.get("content", ""),
                application=s.get("application", []),
                rate=s.get("rate"),
                notes=s.get("notes"),
            )
            for s in data.get("sections", [])
        ]

        law = TaxLaw(
            law_id=data.get("law_id", ""),
            name=data.get("name", ""),
            valid_from=data.get("valid_from", ""),
            sections=sections,
            rates=data.get("rates", {}),
            year=year,
        )

        self._laws_cache[cache_key] = law
        return law

    def load_rule(self, rule_id: str) -> Optional[TaxRule]:
        """
        Load a specific tax rule.

        Args:
            rule_id: Rule identifier

        Returns:
            TaxRule object or None if not found
        """
        if rule_id in self._rules_cache:
            return self._rules_cache[rule_id]

        path = self.base_dir / "rules" / f"{rule_id}.json"
        data = self._load_json(path)

        if not data:
            return None

        rule = TaxRule(
            rule_id=data.get("rule_id", rule_id),
            title=data.get("title", ""),
            description=data.get("description", ""),
            conditions=data.get("conditions", []),
            process=data.get("process", []),
            taxation=data.get("taxation", {}),
            law_references=data.get("law_references", []),
        )

        self._rules_cache[rule_id] = rule
        return rule

    def get_all_laws(self, year: int) -> list[TaxLaw]:
        """
        Get all laws for a specific year.

        Args:
            year: Tax year

        Returns:
            List of TaxLaw objects
        """
        laws_dir = self.base_dir / "laws" / str(year)
        if not laws_dir.exists():
            return []

        laws = []
        for path in laws_dir.glob("*.json"):
            law_type = path.stem
            law = self.load_law(law_type, year)
            if law:
                laws.append(law)

        return laws

    def get_all_rules(self) -> list[TaxRule]:
        """
        Get all tax rules.

        Returns:
            List of TaxRule objects
        """
        rules_dir = self.base_dir / "rules"
        if not rules_dir.exists():
            return []

        rules = []
        for path in rules_dir.glob("*.json"):
            rule_id = path.stem
            rule = self.load_rule(rule_id)
            if rule:
                rules.append(rule)

        return rules

    def get_rates(self, year: int) -> dict[str, float]:
        """
        Get all tax rates for a specific year.

        Args:
            year: Tax year

        Returns:
            Dictionary of rate names to values
        """
        rates = {}

        for law in self.get_all_laws(year):
            for rate_name, rate_value in law.rates.items():
                rates[f"{law.law_id}_{rate_name}"] = rate_value

        return rates

    def search_sections(
        self,
        query: str,
        year: int,
        law_type: Optional[str] = None,
    ) -> list[tuple[TaxLaw, LawSection]]:
        """
        Search for sections matching a query.

        Args:
            query: Search query
            year: Tax year
            law_type: Limit to specific law type

        Returns:
            List of (TaxLaw, LawSection) tuples
        """
        query_lower = query.lower()
        results = []

        if law_type:
            laws = [self.load_law(law_type, year)]
            laws = [l for l in laws if l is not None]
        else:
            laws = self.get_all_laws(year)

        for law in laws:
            for section in law.sections:
                # Search in section content, title, and application
                if (
                    query_lower in section.content.lower()
                    or query_lower in section.title.lower()
                    or any(query_lower in app.lower() for app in section.application)
                ):
                    results.append((law, section))

        return results

    def format_for_prompt(
        self,
        laws: list[TaxLaw] = None,
        rules: list[TaxRule] = None,
        sections: list[tuple[TaxLaw, LawSection]] = None,
    ) -> str:
        """
        Format knowledge for inclusion in AI prompts.

        Args:
            laws: Laws to include
            rules: Rules to include
            sections: Specific sections to include

        Returns:
            Formatted string for prompt
        """
        parts = []

        if sections:
            parts.append("RELEVANTNÍ PARAGRAFY:")
            for law, section in sections:
                parts.append(
                    f"\n{section.section} {law.name}:\n"
                    f"  {section.title}\n"
                    f"  {section.content}\n"
                    f"  Aplikace: {', '.join(section.application)}"
                )

        if rules:
            parts.append("\nPRAVIDLA A POSTUPY:")
            for rule in rules:
                parts.append(
                    f"\n{rule.title}:\n"
                    f"  {rule.description}\n"
                    f"  Proces: {' -> '.join(rule.process)}"
                )

        if laws:
            parts.append("\nSAZBY:")
            for law in laws:
                for rate_name, rate_value in law.rates.items():
                    parts.append(f"  {rate_name}: {rate_value * 100:.1f}%")

        return "\n".join(parts) if parts else ""

    def clear_cache(self) -> None:
        """Clear all cached knowledge."""
        self._laws_cache.clear()
        self._rules_cache.clear()
