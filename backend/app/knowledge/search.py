"""
Knowledge Search functionality.

Provides semantic and keyword-based search over the knowledge base.
"""

from typing import Optional
from dataclasses import dataclass

from app.knowledge.loader import KnowledgeBaseLoader, TaxLaw, LawSection, TaxRule


@dataclass
class SearchResult:
    """A search result item."""

    source_type: str  # "law", "section", "rule"
    source_id: str
    title: str
    content: str
    relevance_score: float
    metadata: dict


class KnowledgeSearch:
    """
    Search functionality for the knowledge base.

    Supports:
    - Keyword search
    - Topic-based search
    - Rate lookup
    """

    # Keywords mapped to relevant topics
    TOPIC_KEYWORDS = {
        "dividenda": ["dividend", "podíl na zisku", "srážková daň", "§36"],
        "mzda": ["mzda", "plat", "zaměstnanec", "sociální pojištění", "zdravotní pojištění"],
        "dppo": ["daň z příjmu", "právnická osoba", "korporátní", "21%", "§21"],
        "dpfo": ["daň z příjmu", "fyzická osoba", "15%", "23%", "solidární"],
        "dph": ["daň z přidané hodnoty", "vat", "21%", "15%", "10%", "registrace"],
        "odpisy": ["odpis", "majetek", "amortizace", "odpisová skupina"],
        "appstore": ["app store", "apple", "zahraniční příjem", "w-8ben"],
        "faktura": ["faktura", "doklad", "isdoc", "náležitosti"],
    }

    def __init__(self, loader: Optional[KnowledgeBaseLoader] = None):
        """
        Initialize search.

        Args:
            loader: Knowledge base loader instance
        """
        self.loader = loader or KnowledgeBaseLoader()

    def search(
        self,
        query: str,
        year: int = 2025,
        limit: int = 10,
    ) -> list[SearchResult]:
        """
        Search the knowledge base.

        Args:
            query: Search query
            year: Tax year for law lookup
            limit: Maximum results to return

        Returns:
            List of SearchResult objects
        """
        results = []
        query_lower = query.lower()

        # Identify relevant topics from query
        relevant_topics = self._identify_topics(query_lower)

        # Search in law sections
        section_results = self.loader.search_sections(query, year)
        for law, section in section_results[:limit // 2]:
            score = self._calculate_relevance(query_lower, section.content, section.title)
            results.append(
                SearchResult(
                    source_type="section",
                    source_id=f"{law.law_id}_{section.section}",
                    title=f"{section.section} - {section.title}",
                    content=section.content[:500],
                    relevance_score=score,
                    metadata={
                        "law_id": law.law_id,
                        "law_name": law.name,
                        "year": year,
                        "application": section.application,
                    },
                )
            )

        # Search in rules
        for rule in self.loader.get_all_rules():
            if self._matches_query(query_lower, rule):
                score = self._calculate_relevance(
                    query_lower, rule.description, rule.title
                )
                results.append(
                    SearchResult(
                        source_type="rule",
                        source_id=rule.rule_id,
                        title=rule.title,
                        content=rule.description[:500],
                        relevance_score=score,
                        metadata={
                            "process_steps": len(rule.process),
                            "conditions": len(rule.conditions),
                        },
                    )
                )

        # Sort by relevance and limit
        results.sort(key=lambda r: r.relevance_score, reverse=True)
        return results[:limit]

    def get_relevant_for_topic(
        self,
        topic: str,
        year: int = 2025,
    ) -> str:
        """
        Get knowledge relevant to a specific topic.

        Args:
            topic: Topic identifier (dividenda, dppo, etc.)
            year: Tax year

        Returns:
            Formatted knowledge string for prompts
        """
        topic_lower = topic.lower()

        # Get keywords for topic
        keywords = self.TOPIC_KEYWORDS.get(topic_lower, [topic_lower])

        # Collect relevant sections
        all_sections = []
        for keyword in keywords:
            sections = self.loader.search_sections(keyword, year)
            all_sections.extend(sections)

        # Remove duplicates
        seen = set()
        unique_sections = []
        for law, section in all_sections:
            key = (law.law_id, section.section)
            if key not in seen:
                seen.add(key)
                unique_sections.append((law, section))

        # Get relevant rules
        rules = []
        for rule in self.loader.get_all_rules():
            if any(kw.lower() in rule.title.lower() or kw.lower() in rule.description.lower()
                   for kw in keywords):
                rules.append(rule)

        return self.loader.format_for_prompt(
            sections=unique_sections[:5],
            rules=rules[:3],
        )

    def get_rates_context(self, year: int = 2025) -> str:
        """
        Get tax rates as context string.

        Args:
            year: Tax year

        Returns:
            Formatted rates string
        """
        rates = self.loader.get_rates(year)

        if not rates:
            # Return hardcoded defaults if no files found
            return """DAŇOVÉ SAZBY 2025:
- Daň z příjmu právnických osob: 21%
- Srážková daň z dividend: 15%
- Daň z příjmu fyzických osob (základní): 15%
- Daň z příjmu fyzických osob (solidární): 23% (nad ~2M Kč)
- Sociální pojištění zaměstnanec: 6,5%
- Sociální pojištění zaměstnavatel: 24,8%
- Zdravotní pojištění zaměstnanec: 4,5%
- Zdravotní pojištění zaměstnavatel: 9%
- DPH základní sazba: 21%
- DPH snížená sazba: 12%
"""

        lines = [f"DAŇOVÉ SAZBY {year}:"]
        for name, value in sorted(rates.items()):
            lines.append(f"- {name}: {value * 100:.1f}%")

        return "\n".join(lines)

    def _identify_topics(self, query: str) -> list[str]:
        """Identify relevant topics from query."""
        topics = []
        for topic, keywords in self.TOPIC_KEYWORDS.items():
            if any(kw in query for kw in keywords) or topic in query:
                topics.append(topic)
        return topics

    def _matches_query(self, query: str, rule: TaxRule) -> bool:
        """Check if a rule matches the query."""
        return (
            query in rule.title.lower()
            or query in rule.description.lower()
            or any(query in str(c).lower() for c in rule.conditions)
        )

    def _calculate_relevance(self, query: str, *texts: str) -> float:
        """
        Calculate relevance score for texts.

        Simple keyword matching - can be enhanced with embeddings later.
        """
        query_words = set(query.split())
        total_matches = 0
        total_words = len(query_words)

        for text in texts:
            text_lower = text.lower()
            for word in query_words:
                if word in text_lower:
                    total_matches += 1

        if total_words == 0:
            return 0.0

        return min(1.0, total_matches / (total_words * len(texts)))
