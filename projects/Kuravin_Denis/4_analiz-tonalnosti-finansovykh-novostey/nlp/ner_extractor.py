import re
from typing import List, Dict, Tuple
from ..models import NamedEntity

KNOWN_COMPANIES = [
    {
        "canonical_name": "ПАО Сбербанк",
        "ticker": "SBER",
        "exchange": "MOEX",
        "sector": "Banking & FinTech",
        "aliases": [r"\bсбер\b", r"\bсбер\w*\b", r"\bсбербанк\w*\b", r"\bsber\b", r"\bsberbank\b"]
    },
    {
        "canonical_name": "ПАО Газпром",
        "ticker": "GAZP",
        "exchange": "MOEX",
        "sector": "Energy & Utilities",
        "aliases": [r"\bгазпром\w*\b", r"\bgazprom\b", r"\bgazp\b"]
    },
    {
        "canonical_name": "Яндекс",
        "ticker": "YDEX",
        "exchange": "MOEX",
        "sector": "Information Technology",
        "aliases": [r"\bяндекс\w*\b", r"\byandex\b", r"\byndx\b", r"\bydex\b"]
    },
    {
        "canonical_name": "Т-Банк (ТКС Холдинг)",
        "ticker": "T",
        "exchange": "MOEX",
        "sector": "Banking & FinTech",
        "aliases": [r"\bт-банк\w*\b", r"\bтинькофф\w*\b", r"\bткс\s+холдинг\w*\b", r"\btcs\b", r"\btcsg\b"]
    },
    {
        "canonical_name": "ПАО Лукойл",
        "ticker": "LKOH",
        "exchange": "MOEX",
        "sector": "Oil & Gas",
        "aliases": [r"\bлукойл\w*\b", r"\blukoil\b", r"\blkoh\b"]
    },
    {
        "canonical_name": "Nvidia Corporation",
        "ticker": "NVDA",
        "exchange": "NASDAQ",
        "sector": "Semiconductors & AI",
        "aliases": [r"\bnvidia\b", r"\bнвидиа\b", r"\bnvda\b"]
    },
    {
        "canonical_name": "Apple Inc.",
        "ticker": "AAPL",
        "exchange": "NASDAQ",
        "sector": "Consumer Electronics",
        "aliases": [r"\bapple\b", r"\bэппл\b", r"\baapl\b"]
    }
]

class FinancialNERExtractor:
    """Модуль извлечения финансовых сущностей (Named Entity Recognition)."""

    def __init__(self):
        self.companies = KNOWN_COMPANIES

    def extract_entities(self, text: str) -> List[NamedEntity]:
        """Находит в тексте упоминания публичных компаний и тикеров."""
        text_lower = text.lower()
        found_entities: List[NamedEntity] = []

        for comp in self.companies:
            count = 0
            for pattern in comp["aliases"]:
                matches = re.findall(pattern, text_lower)
                count += len(matches)

            if count > 0:
                found_entities.append(NamedEntity(
                    name=comp["canonical_name"],
                    ticker=comp["ticker"],
                    exchange=comp["exchange"],
                    sector=comp["sector"],
                    mentions_count=count
                ))

        return found_entities
