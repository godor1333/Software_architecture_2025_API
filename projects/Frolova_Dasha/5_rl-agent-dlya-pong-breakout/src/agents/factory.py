"""Паттерн Factory Method: создание агента по имени алгоритма.

Реализации регистрируются декоратором в src/training/strategies.py,
поэтому новый алгоритм добавляется без правки фабрики (OCP).
"""
from __future__ import annotations

from typing import Dict, Type


class AgentFactory:
    _registry: Dict[str, Type] = {}

    @classmethod
    def register(cls, name: str):
        def deco(c: Type) -> Type:
            cls._registry[name.upper()] = c
            return c

        return deco

    @classmethod
    def create(cls, name: str, env, **overrides):
        cls._ensure_registered()
        if name.upper() not in cls._registry:
            raise ValueError(
                f"Unknown algorithm '{name}'. Доступны: {sorted(cls._registry)}"
            )
        return cls._registry[name.upper()](env=env, **overrides)

    @classmethod
    def load(cls, name: str, path: str):
        cls._ensure_registered()
        return cls._registry[name.upper()].load(path)

    @classmethod
    def _ensure_registered(cls):
        if not cls._registry:
            import src.training.strategies  # noqa: F401 — регистрация стратегий
