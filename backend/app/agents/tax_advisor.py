"""
Tax Advisor Agent.

Specialized agent for Czech tax law advice and optimization recommendations.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from datetime import datetime

from app.agents.base_agent import BaseAgent, AgentResponse
from app.services.tax_calculator import TaxCalculator


@dataclass
class DividendAnalysis:
    """Result of dividend vs salary analysis."""

    recommendation: str
    dividend_net: Decimal
    salary_net: Decimal
    savings: Decimal
    explanation: str
    legal_references: list[str]
    warnings: list[str]


class TaxAdvisorAgent(BaseAgent):
    """
    Expert agent for Czech tax law.

    Specializes in:
    - Corporate tax (DPPO)
    - Personal income tax (DPFO)
    - Dividend taxation
    - Tax optimization strategies
    - App Store income taxation
    """

    def get_agent_name(self) -> str:
        return "Tax Advisor"

    def get_system_prompt(self) -> str:
        current_year = datetime.now().year
        return f"""Jsi expert na české daňové právo. Jmenuješ se "Daňový Poradce Pro".

TVOJE SPECIALIZACE:
- Daň z příjmu právnických osob (DPPO) - zákon č. 586/1992 Sb.
- Daň z příjmu fyzických osob (DPFO)
- Zdanění dividend a podílů na zisku
- Optimalizace daňové zátěže pro malé s.r.o.
- Zdanění příjmů ze zahraničí (např. App Store)
- Sociální a zdravotní pojištění

AKTUÁLNÍ SAZBY ({current_year}):
- Daň z příjmu PO: 21%
- Srážková daň z dividend: 15%
- Daň z příjmu FO (základní): 15%
- Daň z příjmu FO (solidární): 23% (nad ~2M Kč ročně)
- Sociální pojištění zaměstnanec: 6,5%
- Sociální pojištění zaměstnavatel: 24,8%
- Zdravotní pojištění zaměstnanec: 4,5%
- Zdravotní pojištění zaměstnavatel: 9%

PRAVIDLA ODPOVÍDÁNÍ:
1. VŽDY cituj konkrétní paragraf a zákon, když dáváš daňovou radu
2. Rozlišuj mezi legální optimalizací a nelegálním vyhýbáním se dani
3. Upozorni na rizika a nejistoty interpretace
4. U složitějších případů doporuč konzultaci s daňovým poradcem
5. Odpovídej v češtině, jasně a srozumitelně
6. Pokud si nejsi jistý, řekni to otevřeně

FORMÁT ODPOVĚDI:
- Začni přímou odpovědí na otázku
- Uveď relevantní právní reference
- Pokud je to vhodné, uveď číselný příklad
- Zakončit případnými doporučeními nebo varováními

OMEZENÍ:
- Neposkytuj rady k daňovým únikům
- Nenavrhuj agresivní daňové struktury
- Připomínej, že situace každého je individuální
"""

    async def analyze_query(
        self,
        query: str,
        company_data: Optional[dict] = None,
    ) -> AgentResponse:
        """
        Analyze a general tax-related query.

        Args:
            query: User's tax question
            company_data: Optional company financial data for context

        Returns:
            AgentResponse with tax advice
        """
        context = {}
        if company_data:
            context["company_data"] = company_data

        return await self.query(query, context)

    async def analyze_dividend_vs_salary(
        self,
        profit: Decimal,
        other_income: Decimal = Decimal("0"),
        year: int = None,
    ) -> DividendAnalysis:
        """
        Analyze optimal payout strategy: dividend vs salary.

        Args:
            profit: Available profit before corporate tax
            other_income: Other personal income (for solidarity tax)
            year: Tax year for calculations

        Returns:
            DividendAnalysis with recommendation
        """
        year = year or datetime.now().year
        calculator = TaxCalculator(year=year)

        # Calculate both scenarios
        comparison = calculator.compare_dividend_vs_salary(profit, other_income)

        # Get AI explanation
        context = {
            "profit_before_tax": str(profit),
            "other_income": str(other_income),
            "year": year,
            "dividend_result": comparison["dividend"],
            "salary_result": comparison["salary"],
        }

        query = f"""Analyzuj optimální způsob výplaty zisku {profit:,.0f} Kč z s.r.o. jednočlennému majiteli.

Výsledky výpočtu:
- Dividenda: čistá částka {comparison['dividend']['net_amount']:,.0f} Kč, efektivní sazba {comparison['dividend']['effective_rate']*100:.1f}%
- Mzda: čistá částka {comparison['salary']['net_amount']:,.0f} Kč, efektivní sazba {comparison['salary']['effective_rate']*100:.1f}%

Ostatní příjmy osoby: {other_income:,.0f} Kč

Vysvětli rozdíly a doporuč optimální strategii. Zohledni i nefinanční aspekty (důchodové pojištění, nemocenská, atd.)."""

        response = await self.query(query, context)

        # Determine better option
        better = comparison["recommendation"]["better_option"]
        savings = comparison["recommendation"]["savings"]

        return DividendAnalysis(
            recommendation=better,
            dividend_net=Decimal(str(comparison["dividend"]["net_amount"])),
            salary_net=Decimal(str(comparison["salary"]["net_amount"])),
            savings=savings,
            explanation=response.answer,
            legal_references=response.sources,
            warnings=[
                "Výpočet je orientační a nezahrnuje všechny individuální okolnosti.",
                "Doporučujeme konzultaci s daňovým poradcem pro závazné rozhodnutí.",
            ],
        )

    async def check_compliance(
        self,
        company_data: dict,
        check_areas: list[str] = None,
    ) -> AgentResponse:
        """
        Check tax compliance for a company.

        Args:
            company_data: Company financial and accounting data
            check_areas: Specific areas to check (tax, vat, accounting)

        Returns:
            AgentResponse with compliance findings
        """
        areas = check_areas or ["tax", "vat", "accounting"]

        query = f"""Proveď kontrolu daňové compliance pro následující firmu.

Oblasti kontroly: {', '.join(areas)}

Zkontroluj:
1. Správnost výpočtu daní
2. Dodržení termínů
3. Kompletnost dokumentace
4. Potenciální rizika

Pokud najdeš problémy, uveď:
- Závažnost (vysoká/střední/nízká)
- Konkrétní problém
- Doporučení k nápravě
- Relevantní právní předpis"""

        return await self.query(query, {"company_data": company_data})

    async def explain_tax_concept(self, concept: str) -> AgentResponse:
        """
        Explain a tax concept in simple terms.

        Args:
            concept: Tax concept to explain (e.g., "srážková daň", "odpisy")

        Returns:
            AgentResponse with explanation
        """
        query = f"""Vysvětli koncept "{concept}" jednoduchým způsobem.

Zahrň:
1. Co to je a jak to funguje
2. Kdy se to používá
3. Praktický příklad s čísly
4. Relevantní právní předpis
5. Časté chyby, kterým se vyhnout"""

        return await self.query(query)

    async def get_tax_deadlines(self, year: int = None) -> AgentResponse:
        """
        Get important tax deadlines for the year.

        Args:
            year: Tax year

        Returns:
            AgentResponse with deadline calendar
        """
        year = year or datetime.now().year

        query = f"""Uveď přehled důležitých daňových termínů pro rok {year} pro s.r.o.

Zahrň:
1. Daň z příjmu právnických osob
2. DPH (měsíční/čtvrtletní)
3. Zálohy na daň
4. Účetní závěrka
5. Mzdová agenda

Pro každý termín uveď:
- Datum
- Co se podává/platí
- Sankce za nedodržení"""

        return await self.query(query, {"year": year})
