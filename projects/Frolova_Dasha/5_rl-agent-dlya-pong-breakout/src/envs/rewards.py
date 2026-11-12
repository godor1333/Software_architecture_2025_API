"""Паттерн Strategy: сменные стратегии награды."""
from abc import ABC, abstractmethod


class RewardStrategy(ABC):
    @abstractmethod
    def shape(self, env, base_reward: float) -> float:
        raise NotImplementedError


class SparseRewardStrategy(RewardStrategy):
    """Только очки: +1 за забитый гол, -1 за пропущенный."""

    def shape(self, env, base_reward: float) -> float:
        return float(base_reward)


class ShapedRewardStrategy(RewardStrategy):
    """Спарс-награда + бонус за выравнивание платформы с мячом.

    Ускоряет раннее обучение DQN: агент получает плотный сигнал
    до того, как впервые коснётся мяча.
    """

    ALIGNMENT_BONUS = 0.01

    def shape(self, env, base_reward: float) -> float:
        diff = abs(env.ball_y - (env.left_y + env.paddle_h / 2))
        aligned = 1.0 if diff < env.paddle_h / 2 else 0.0
        return float(base_reward) + self.ALIGNMENT_BONUS * aligned


REWARD_STRATEGIES = {
    "sparse": SparseRewardStrategy,
    "shaped": ShapedRewardStrategy,
}
