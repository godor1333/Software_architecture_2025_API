"""Паттерн Factory Method: создание игровых сред по имени."""
from __future__ import annotations

from typing import Callable, Dict, Optional


class EnvFactory:
    _registry: Dict[str, Callable] = {}

    @classmethod
    def register(cls, name: str):
        def deco(fn: Callable) -> Callable:
            cls._registry[name] = fn
            return fn

        return deco

    @classmethod
    def create(cls, name: str, reward_strategy=None, **kwargs):
        if name not in cls._registry:
            raise ValueError(f"Unknown env '{name}'. Доступны: {list(cls._registry)}")
        return cls._registry[name](reward_strategy=reward_strategy, **kwargs)


@EnvFactory.register("PongPygame-v0")
def _pong(reward_strategy=None, **kwargs):
    from src.envs.pong_env import PongEnv  # ленивый импорт: pygame нужен не всем

    return PongEnv(reward_strategy=reward_strategy, **kwargs)


@EnvFactory.register("BreakoutNoFrameskip-v4")
def _breakout(reward_strategy=None, **kwargs):
    import gymnasium as gym
    from gymnasium.wrappers import AtariPreprocessing, FrameStackObservation

    env = gym.make("ALE/Breakout-v5", frameskip=1, **{k: v for k, v in kwargs.items() if k in ("render_mode",)})
    env = AtariPreprocessing(env, noop_max=30, frame_skip=4, screen_size=84, grayscale_obs=True)
    return FrameStackObservation(env, 4)
