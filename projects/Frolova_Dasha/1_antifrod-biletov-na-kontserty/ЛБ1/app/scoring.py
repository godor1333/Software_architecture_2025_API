from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import OrderEvent, RuleHit


class ScoringRule(Protocol):
    def evaluate(self, event: OrderEvent) -> RuleHit | None: ...


@dataclass(frozen=True)
class VelocityRule:
    def evaluate(self, event: OrderEvent) -> RuleHit | None:
        if event.purchase_attempts_10m >= 5:
            return RuleHit(
                code="HIGH_VELOCITY",
                description="Пять или более попыток покупки за 10 минут",
                weight=0.45,
            )
        return None


@dataclass(frozen=True)
class BulkPurchaseRule:
    def evaluate(self, event: OrderEvent) -> RuleHit | None:
        if event.ticket_count >= 6:
            return RuleHit(
                code="BULK_PURCHASE",
                description="Крупная покупка: шесть или более билетов",
                weight=0.30,
            )
        return None


@dataclass(frozen=True)
class FreshAccountRule:
    def evaluate(self, event: OrderEvent) -> RuleHit | None:
        if event.account_age_days <= 2:
            return RuleHit(
                code="FRESH_ACCOUNT",
                description="Учётная запись создана не более двух дней назад",
                weight=0.20,
            )
        return None


@dataclass(frozen=True)
class DeviceSharingRule:
    def evaluate(self, event: OrderEvent) -> RuleHit | None:
        if event.device_accounts_24h >= 3:
            return RuleHit(
                code="SHARED_DEVICE",
                description="С устройства использовалось три или более аккаунтов за 24 часа",
                weight=0.25,
            )
        return None


class RuleChain:
    """Chain of Responsibility: rules are evaluated independently in order."""

    def __init__(self, rules: list[ScoringRule]) -> None:
        self._rules = rules

    def score(self, event: OrderEvent) -> tuple[float, list[RuleHit]]:
        hits = [hit for rule in self._rules if (hit := rule.evaluate(event)) is not None]
        return min(1.0, round(sum(hit.weight for hit in hits), 2)), hits


def default_rule_chain() -> RuleChain:
    return RuleChain([
        VelocityRule(),
        BulkPurchaseRule(),
        FreshAccountRule(),
        DeviceSharingRule(),
    ])
