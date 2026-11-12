"""Паттерн Command: каждое действие агента — объект-команда.

Команды инкапсулируют эффект действия, поэтому их можно переиспользовать
в окружении, в оффлайн-реплеях и в daemon-режиме тренера.
"""
from abc import ABC, abstractmethod


class Command(ABC):
    @abstractmethod
    def execute(self, env) -> None:
        raise NotImplementedError


class PaddleUp(Command):
    def execute(self, env) -> None:
        env.left_y = max(0, env.left_y - env.paddle_speed)


class PaddleDown(Command):
    def execute(self, env) -> None:
        env.left_y = min(env.height - env.paddle_h, env.left_y + env.paddle_speed)


class PaddleStay(Command):
    def execute(self, env) -> None:
        pass


ACTION_COMMANDS = {0: PaddleStay(), 1: PaddleUp(), 2: PaddleDown()}
