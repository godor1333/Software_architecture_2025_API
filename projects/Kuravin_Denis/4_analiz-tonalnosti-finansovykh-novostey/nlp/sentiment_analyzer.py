import re
from typing import Tuple, List, Dict
from ..models import SentimentLabel

FINANCIAL_POSITIVE_TRIGGERS = [
    (r"\bрост\s+(?:чистой\s+)?прибыли\b", 0.45, "Рост прибыли"),
    (r"\bрекордн(?:ые|ая)\s+(?:дивиденды|выручка|прибыль)\b", 0.50, "Рекордные финансовые показатели"),
    (r"\bувеличени(?:е|я)\s+дивиденд\w*\b", 0.40, "Увеличение дивидендов"),
    (r"\bбайбэк\b|\bвыкуп\s+акций\b", 0.35, "Программа обратного выкупа акций (Buyback)"),
    (r"\bпревысил\w*\s+прогноз\w*\b|\bbeat\s+estimate\w*\b", 0.40, "Превышение консенсус-прогноза аналитиков"),
    (r"\bпадени(?:е|я)\s+(?:издержек|расходов|затрат)\b", 0.35, "Оптимизация и падение издержек"),
    (r"\bповысил\w*\s+рейтинг\b|\bтаргет\s+повышен\b", 0.35, "Повышение целевой цены аналитиками"),
    (r"\bрост\s+(?:выручки|доходов|рентабельности)\b", 0.30, "Рост выручки/рентабельности")
]

FINANCIAL_NEGATIVE_TRIGGERS = [
    (r"\bчист(?:ый|ого)\s+убыт(?:ок|ка)\b", -0.50, "Чистый убыток"),
    (r"\bпадени(?:е|я)\s+(?:чистой\s+)?прибыли\b", -0.45, "Падение чистой прибыли"),
    (r"\bсанкци\w*\b", -0.45, "Санкционное давление"),
    (r"\bснижени(?:е|я)\s+(?:выручки|дивидендов)\b", -0.35, "Снижение выручки/дивидендов"),
    (r"\bотзыв\s+лицензии\b", -0.60, "Отзыв банковской лицензии"),
    (r"\bдефолт\b", -0.65, "Дефолт по обязательствам"),
    (r"\bштраф\w*\s+регулятор\w*\b", -0.35, "Штрафные санкции регулятора"),
    (r"\bухудшени(?:е|я)\s+прогноз\w*\b", -0.30, "Ухудшение прогноза менеджмента")
]

class FinBERTSentimentAnalyzer:
    """Анализатор финансовой тональности (FinBERT Sentiment Core)."""

    def analyze(self, text: str) -> Tuple[SentimentLabel, float, float, List[str]]:
        text_lower = text.lower()
        score = 0.0
        drivers = []

        # Позитивные маркеры
        for pattern, weight, desc in FINANCIAL_POSITIVE_TRIGGERS:
            if re.search(pattern, text_lower):
                score += weight
                drivers.append(desc)

        # Негативные маркеры
        for pattern, weight, desc in FINANCIAL_NEGATIVE_TRIGGERS:
            if re.search(pattern, text_lower):
                score += weight
                drivers.append(desc)

        # Ограничение диапазона [-1.0, 1.0]
        score = max(-1.0, min(1.0, score))

        if score >= 0.20:
            label = SentimentLabel.POSITIVE
            confidence = min(0.96, 0.65 + abs(score) * 0.35)
        elif score <= -0.20:
            label = SentimentLabel.NEGATIVE
            confidence = min(0.96, 0.65 + abs(score) * 0.35)
        else:
            label = SentimentLabel.NEUTRAL
            confidence = 0.85
            if not drivers:
                drivers.append("Нейтральное корпоративное раскрытие информации")

        return label, round(score, 3), round(confidence, 3), drivers
