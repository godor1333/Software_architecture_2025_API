from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from ..models import FraudEvaluationResult, FraudStatus
from ..config import settings
from ..ml.scorer import MLFraudScorer

if TYPE_CHECKING:
    from .chain_of_responsibility import EvaluationContext

class IScoringStrategy(ABC):
    """Интерфейс стратегии антифрод-скоринга (Strategy Pattern)."""

    @abstractmethod
    def evaluate(self, context: 'EvaluationContext') -> FraudEvaluationResult:
        pass

class RuleBasedStrategy(IScoringStrategy):
    """Стратегия оценки исключительно на основе набора эвристических правил."""

    def evaluate(self, context: 'EvaluationContext') -> FraudEvaluationResult:
        score = 0.0
        rules = list(context.matched_rules)
        reasons = []

        if context.event.click_interval_ms is not None and context.event.click_interval_ms < 200:
            score += 0.45
            rules.append("RULE_SUB_SECOND_CLICK")
            reasons.append("Слишком быстрый клик (< 200ms)")

        if context.ip_clicks_1min > 10:
            score += 0.35
            rules.append("RULE_BURST_TRAFFIC")
            reasons.append("Всплеск кликов с одного IP")

        if context.event.device_type == "mobile" and "windows" in context.event.os.lower():
            score += 0.30
            rules.append("RULE_DEVICE_OS_MISMATCH")
            reasons.append("Несоответствие устройства и операционной системы")

        score = min(1.0, score)
        is_fraud = score >= settings.fraud_threshold
        status = FraudStatus.BLOCKED if is_fraud else (FraudStatus.SUSPICIOUS if score >= settings.suspicious_threshold else FraudStatus.ALLOWED)
        primary_reason = "; ".join(reasons) if reasons else "Трафик легитимен"

        return FraudEvaluationResult(
            click_id=context.event.click_id,
            is_fraud=is_fraud,
            fraud_score=round(score, 3),
            status=status,
            primary_reason=primary_reason,
            matched_rules=rules
        )

class MLOnlyStrategy(IScoringStrategy):
    """Стратегия оценки только через вероятностную модель XGBoost."""

    def __init__(self):
        self.scorer = MLFraudScorer()

    def evaluate(self, context: 'EvaluationContext') -> FraudEvaluationResult:
        proba, features = self.scorer.score(
            context.event,
            ip_history_1min=context.ip_clicks_1min,
            ip_history_5min=context.ip_clicks_5min
        )
        is_fraud = proba >= settings.fraud_threshold
        status = FraudStatus.BLOCKED if is_fraud else (FraudStatus.SUSPICIOUS if proba >= settings.suspicious_threshold else FraudStatus.ALLOWED)

        reason = f"XGBoost скор фрода: {proba:.2%}"
        if is_fraud:
            reason += " (Превышен порог классификатора)"

        return FraudEvaluationResult(
            click_id=context.event.click_id,
            is_fraud=is_fraud,
            fraud_score=round(proba, 4),
            status=status,
            primary_reason=reason,
            matched_rules=context.matched_rules + ["ML_XGBOOST_EVALUATED"],
            features_used=features
        )

class HybridScoringStrategy(IScoringStrategy):
    """Гибридная стратегия (ML + бизнес-эвристики)."""

    def __init__(self, ml_weight: float = 0.7, rule_weight: float = 0.3):
        self.ml_strategy = MLOnlyStrategy()
        self.rule_strategy = RuleBasedStrategy()
        self.ml_weight = ml_weight
        self.rule_weight = rule_weight

    def evaluate(self, context: 'EvaluationContext') -> FraudEvaluationResult:
        ml_res = self.ml_strategy.evaluate(context)
        rule_res = self.rule_strategy.evaluate(context)

        combined_score = (ml_res.fraud_score * self.ml_weight) + (rule_res.fraud_score * self.rule_weight)
        combined_score = min(1.0, max(0.0, combined_score))

        is_fraud = combined_score >= settings.fraud_threshold
        status = FraudStatus.BLOCKED if is_fraud else (FraudStatus.SUSPICIOUS if combined_score >= settings.suspicious_threshold else FraudStatus.ALLOWED)

        all_rules = list(set(ml_res.matched_rules + rule_res.matched_rules))
        primary_reason = f"Гибридный скоринг (ML={ml_res.fraud_score:.2f}, Rules={rule_res.fraud_score:.2f}) -> Итог {combined_score:.2f}"

        return FraudEvaluationResult(
            click_id=context.event.click_id,
            is_fraud=is_fraud,
            fraud_score=round(combined_score, 4),
            status=status,
            primary_reason=primary_reason,
            matched_rules=all_rules,
            features_used=ml_res.features_used
        )
