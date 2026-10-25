from __future__ import annotations

from typing import Protocol

from app.schemas import OrderEvent, ScoreResponse


class ScoreRepository(Protocol):
    def save(self, score: ScoreResponse) -> ScoreResponse: ...

    def get(self, order_id: str) -> ScoreResponse | None: ...

    def save_order(self, event: OrderEvent) -> None: ...


class InMemoryScoreRepository:
    """Repository pattern. Swappable for PostgreSQL in a production deployment."""

    def __init__(self) -> None:
        self._items: dict[str, ScoreResponse] = {}
        self._orders: dict[str, OrderEvent] = {}

    def save(self, score: ScoreResponse) -> ScoreResponse:
        self._items[score.order_id] = score
        return score

    def get(self, order_id: str) -> ScoreResponse | None:
        return self._items.get(order_id)

    def save_order(self, event: OrderEvent) -> None:
        self._orders[event.order_id] = event
