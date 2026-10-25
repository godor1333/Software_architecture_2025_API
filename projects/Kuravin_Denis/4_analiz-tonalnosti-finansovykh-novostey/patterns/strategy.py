from abc import ABC, abstractmethod
from typing import Tuple, List
from ..models import SentimentLabel
from ..nlp.sentiment_analyzer import FinBERTSentimentAnalyzer

class ISentimentStrategy(ABC):
    """Интерфейс стратегии оценки тональности (Strategy Pattern)."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def evaluate(self, text: str) -> Tuple[SentimentLabel, float, float, List[str]]:
        """Возвращает (SentimentLabel, score [-1.0, 1.0], confidence, key_drivers)."""
        pass

class FinBERTStrategy(ISentimentStrategy):
    """Стратегия глубокого анализа тональности на базе финансовой языковой модели FinBERT."""

    def __init__(self):
        self.analyzer = FinBERTSentimentAnalyzer()

    @property
    def name(self) -> str:
        return "FinBERT-Finance-Sentiment"

    def evaluate(self, text: str) -> Tuple[SentimentLabel, float, float, List[str]]:
        return self.analyzer.analyze(text)

class LexiconStrategy(ISentimentStrategy):
    """Легковесная эвристическая стратегия быстрого анализа тональности."""

    @property
    def name(self) -> str:
        return "Fast-Lexicon-Sentiment"

    def evaluate(self, text: str) -> Tuple[SentimentLabel, float, float, List[str]]:
        txt = text.lower()
        pos_words = ["рост", "прибыль", "выручка", "дивиденды", "рекорд", "успех"]
        neg_words = ["убыток", "падение", "санкции", "кризис", "банкротство", "штраф"]

        pos_count = sum(1 for w in pos_words if w in txt)
        neg_count = sum(1 for w in neg_words if w in txt)

        if pos_count > neg_count:
            return SentimentLabel.POSITIVE, 0.55, 0.75, ["Лексический перевес позитивных терминов"]
        elif neg_count > pos_count:
            return SentimentLabel.NEGATIVE, -0.55, 0.75, ["Лексический перевес негативных терминов"]
        else:
            return SentimentLabel.NEUTRAL, 0.0, 0.65, ["Сбалансированная или нейтральная лексика"]
