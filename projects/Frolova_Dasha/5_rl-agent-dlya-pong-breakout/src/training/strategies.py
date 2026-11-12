"""Паттерн Strategy: сменные алгоритмы обучения поверх SB3.

Каждая стратегия инкапсулирует гиперпараметры, обучение и сохранение,
поэтому тренер не знает, DQN перед ним или PPO.
"""
import json
import os

from stable_baselines3 import DQN, PPO

from src.agents.factory import AgentFactory


class BaseStrategy:
    NAME: str = "base"
    ALGO = None
    HYPERPARAMS: dict = {}

    def __init__(self, env=None, **overrides):
        params = {**self.HYPERPARAMS, **overrides}
        params.pop("policy", None)
        if env is not None:
            self.model = self.ALGO("CnnPolicy", env=env, device="cpu", **params)

    def learn(self, total_timesteps: int, callback=None):
        return self.model.learn(total_timesteps=total_timesteps, callback=callback)

    def predict(self, observation, deterministic: bool = True):
        return self.model.predict(observation, deterministic=deterministic)

    def save(self, path: str) -> None:
        self.model.save(path)
        with open(path + ".meta.json", "w", encoding="utf-8") as f:
            json.dump({"algorithm": self.NAME}, f)

    @classmethod
    def load(cls, path: str):
        inst = cls.__new__(cls)
        inst.model = cls.ALGO.load(path, device="cpu")
        return inst


@AgentFactory.register("DQN")
class DQNStrategy(BaseStrategy):
    NAME = "DQN"
    ALGO = DQN
    HYPERPARAMS = dict(
        learning_rate=1e-4,
        buffer_size=50_000,
        learning_starts=10_000,
        batch_size=32,
        target_update_interval=1_000,
        train_freq=4,
        gamma=0.99,
        exploration_fraction=0.2,
        exploration_final_eps=0.05,
        verbose=0,
    )


@AgentFactory.register("PPO")
class PPOStrategy(BaseStrategy):
    NAME = "PPO"
    ALGO = PPO
    HYPERPARAMS = dict(
        learning_rate=2.5e-4,
        n_steps=128,
        batch_size=256,
        n_epochs=4,
        gamma=0.99,
        ent_coef=0.01,
        verbose=0,
    )
