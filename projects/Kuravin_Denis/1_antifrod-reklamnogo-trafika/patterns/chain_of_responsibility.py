from abc import ABC, abstractmethod
from typing import Optional, List
from ..models import ClickEvent, FraudEvaluationResult, FraudStatus
from ..config import settings
from .strategy import IScoringStrategy

class EvaluationContext:
    """Контекст, передаваемый по цепочке обязанностей."""
    def __init__(self, event: ClickEvent, ip_clicks_1min: int = 1, ip_clicks_5min: int = 1):
        self.event = event
        self.ip_clicks_1min = ip_clicks_1min
        self.ip_clicks_5min = ip_clicks_5min
        self.matched_rules: List[str] = []
        self.is_terminal: bool = False
        self.result: Optional[FraudEvaluationResult] = None

class AbstractAntifraudHandler(ABC):
    """Базовый класс обработчика в цепочке обязанностей (Chain of Responsibility)."""
    def __init__(self):
        self._next_handler: Optional[AbstractAntifraudHandler] = None

    def set_next(self, handler: 'AbstractAntifraudHandler') -> 'AbstractAntifraudHandler':
        self._next_handler = handler
        return handler

    def handle(self, context: EvaluationContext) -> Optional[FraudEvaluationResult]:
        self.process(context)
        if context.is_terminal and context.result is not None:
            return context.result
        if self._next_handler:
            return self._next_handler.handle(context)
        return context.result

    @abstractmethod
    def process(self, context: EvaluationContext) -> None:
        pass

class BlacklistIpHandler(AbstractAntifraudHandler):
    """1. Проверка IP по базе известных ботнетов/черных списков."""
    KNOWN_BAD_IPS = {"198.51.100.24", "203.0.113.88", "192.0.2.144"}

    def process(self, context: EvaluationContext) -> None:
        if context.event.ip_address in self.KNOWN_BAD_IPS:
            context.matched_rules.append("RULE_IP_BLACKLIST")
            context.is_terminal = True
            context.result = FraudEvaluationResult(
                click_id=context.event.click_id,
                is_fraud=True,
                fraud_score=1.0,
                status=FraudStatus.BLOCKED,
                primary_reason="IP находится в черном списке спам-сетей",
                matched_rules=context.matched_rules
            )

class UserAgentBotHandler(AbstractAntifraudHandler):
    """2. Проверка сигнатур ботов и краулеров в User-Agent."""
    BOT_SIGNATURES = ["curl", "python-requests", "wget", "headlesschrome", "phantomjs", "selenium"]

    def process(self, context: EvaluationContext) -> None:
        ua = context.event.user_agent.lower()
        for sig in self.BOT_SIGNATURES:
            if sig in ua:
                context.matched_rules.append(f"RULE_UA_BOT_{sig.upper()}")
                context.is_terminal = True
                context.result = FraudEvaluationResult(
                    click_id=context.event.click_id,
                    is_fraud=True,
                    fraud_score=0.98,
                    status=FraudStatus.BLOCKED,
                    primary_reason=f"Обнаружена сигнатура автоматизированного скрипта ({sig}) в User-Agent",
                    matched_rules=context.matched_rules
                )
                return

class FastClickRateLimitHandler(AbstractAntifraudHandler):
    """3. Проверка частоты кликов (Rate Limiting)."""
    def process(self, context: EvaluationContext) -> None:
        if context.ip_clicks_1min > settings.rate_limit_clicks_per_minute:
            context.matched_rules.append("RULE_RATE_LIMIT_EXCEEDED")
            context.is_terminal = True
            context.result = FraudEvaluationResult(
                click_id=context.event.click_id,
                is_fraud=True,
                fraud_score=0.95,
                status=FraudStatus.BLOCKED,
                primary_reason=f"Превышен лимит частоты кликов: {context.ip_clicks_1min} кликов в минуту",
                matched_rules=context.matched_rules
            )

class ScoringStrategyHandler(AbstractAntifraudHandler):
    """4. Завершающий обработчик: скоринг через выбранную стратегию (ML / Hybrid)."""
    def __init__(self, scoring_strategy: IScoringStrategy):
        super().__init__()
        self.strategy = scoring_strategy

    def process(self, context: EvaluationContext) -> None:
        res = self.strategy.evaluate(context)
        context.result = res
        context.is_terminal = True
