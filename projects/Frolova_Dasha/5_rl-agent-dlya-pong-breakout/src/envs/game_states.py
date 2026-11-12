"""Паттерн State: жизненный цикл матча как иерархия состояний.

Serving -> Playing -> GameOver. Переходы инкапсулированы в классах,
окружение не знает деталей того, кто и когда двигает мяч.
"""


class GameState:
    def __init__(self, env):
        self.env = env

    def handle(self, cmd) -> "GameState":
        raise NotImplementedError


class ServingState(GameState):
    """Мяч ещё не подан: первый тик подаёт мяч и переводит матч в игру."""

    def handle(self, cmd) -> GameState:
        cmd.execute(self.env)
        self.env._serve_ball()
        return PlayingState(self.env)


class PlayingState(GameState):
    """Активная игра: команды двигают платформы, считается физика и очки."""

    def handle(self, cmd) -> GameState:
        cmd.execute(self.env)
        self.env._move_opponent()
        self.env._physics_step()
        if (
            self.env.left_score >= self.env.max_score
            or self.env.right_score >= self.env.max_score
        ):
            return GameOverState(self.env)
        return self


class GameOverState(GameState):
    """Терминальное состояние: матч завершён."""

    def handle(self, cmd) -> GameState:
        return self
