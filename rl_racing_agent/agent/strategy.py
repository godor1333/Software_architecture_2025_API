from abc import ABC, abstractmethod


class RewardStrategy(ABC):
    @abstractmethod
    def compute(self, delta_progress: float, crashed: bool) -> float:
        pass


class TimeRewardStrategy(RewardStrategy):
    def compute(self, delta_progress, crashed):
        if crashed:
            return -10.0
        return delta_progress * 100.0


class SafeRewardStrategy(RewardStrategy):
    def compute(self, delta_progress, crashed):
        if crashed:
            return -50.0
        return delta_progress * 80.0