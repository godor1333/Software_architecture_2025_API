<<<<<<< HEAD
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
=======
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
>>>>>>> 0037982a52b70d8ed1ac0df57ec0f7ee8fcf872b
        return delta_progress * 80.0