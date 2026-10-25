from __future__ import annotations

from datetime import datetime, timezone

from app.config import Settings
from app.schemas import Decision, OrderEvent, ScoreResponse
from app.scoring import RuleChain
from app.storage import AnalyticsStore, CounterStore, ScoreStore


class ScoringService:
    """Application service: combines rules, ML and durable result stores."""

    def __init__(
        self,
        settings: Settings,
        rule_chain: RuleChain,
        model,
        counters: CounterStore,
        scores: ScoreStore,
        analytics: AnalyticsStore,
    ) -> None:
        self.settings = settings
        self.rule_chain = rule_chain
        self.model = model
        self.counters = counters
        self.scores = scores
        self.analytics = analytics

    async def enrich(self, event: OrderEvent) -> OrderEvent:
        return await self.counters.enrich(event)

    async def score(self, event: OrderEvent) -> ScoreResponse:
        rule_score, reasons = self.rule_chain.score(event)
        risk_score = self.model.predict_risk(event) if self.model else rule_score
        result = ScoreResponse(
            order_id=event.order_id,
            risk_score=risk_score,
            decision=Decision.REVIEW if risk_score >= self.settings.decision_threshold else Decision.ALLOW,
            reasons=reasons,
            model_version=self.settings.model_version,
            scored_at=datetime.now(timezone.utc),
        )
        await self.scores.save_order(event)
        await self.scores.save_score(result)
        await self.analytics.write(event, result)
        return result
