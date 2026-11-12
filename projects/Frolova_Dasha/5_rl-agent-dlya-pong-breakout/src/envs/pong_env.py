"""Pong на Pygame в Gymnasium-обёртке.

Здесь же применяется паттерн State (game_states.py) и Command (commands.py).
"""
from collections import deque
from typing import Optional

import numpy as np
import pygame
import gymnasium as gym
from gymnasium import spaces

from src.envs.commands import ACTION_COMMANDS
from src.envs.game_states import GameOverState, PlayingState, ServingState
from src.envs.rewards import RewardStrategy, SparseRewardStrategy

SCREEN_SIZE = 84
PADDLE_H = 14
PADDLE_W = 3
BALL_SIZE = 3


class PongEnv(gym.Env):
    metadata = {"render_modes": ["rgb_array", "human"], "render_fps": 30}

    def __init__(
        self,
        render_mode: Optional[str] = None,
        reward_strategy: RewardStrategy = None,
        max_score: int = 11,
        max_steps: int = 2000,
        seed: int = 0,
        opponent_skill: float = 0.9,
    ):
        super().__init__()
        assert render_mode in (None, "rgb_array", "human")
        self.render_mode = render_mode
        self.reward_strategy = reward_strategy or SparseRewardStrategy()
        self.max_score = max_score
        self.max_steps = max_steps
        self.opponent_skill = opponent_skill
        self.rng = np.random.default_rng(seed)

        self.observation_space = spaces.Box(
            0, 255, shape=(4, SCREEN_SIZE, SCREEN_SIZE), dtype=np.uint8
        )
        self.action_space = spaces.Discrete(3)

        self.height = SCREEN_SIZE
        self.paddle_h = PADDLE_H
        self.paddle_speed = 5
        self.left_y = SCREEN_SIZE // 2 - PADDLE_H // 2
        self.right_y = SCREEN_SIZE // 2 - PADDLE_H // 2
        self.ball_x = SCREEN_SIZE / 2
        self.ball_y = SCREEN_SIZE / 2
        self.ball_vx = 0.0
        self.ball_vy = 0.0
        self.left_score = 0
        self.right_score = 0
        self._point_reward = 0.0
        self._t = 0
        self._state: Optional[ServingState] = None
        self._frames = deque(maxlen=4)

        if render_mode == "human":
            pygame.display.set_mode((SCREEN_SIZE * 4, SCREEN_SIZE * 4))
        self.screen = pygame.Surface((SCREEN_SIZE, SCREEN_SIZE))

    # ------------------ gym API ------------------
    def reset(self, *, seed: Optional[int] = None, options=None):
        super().reset(seed=seed)
        self.left_y = self.right_y = SCREEN_SIZE // 2 - PADDLE_H // 2
        self.left_score = self.right_score = 0
        self._t = 0
        self._state = ServingState(self)
        self._point_reward = 0.0
        self._frames.clear()
        frame = self._render_frame()
        for _ in range(4):
            self._frames.append(frame)
        return self._observation(), {"score_agent": 0, "score_opp": 0}

    def step(self, action: int):
        assert self.action_space.contains(int(action))
        self._t += 1
        self._state = self._state.handle(ACTION_COMMANDS[int(action)])
        terminated = isinstance(self._state, GameOverState)
        reward = self.reward_strategy.shape(self, self._point_reward)
        self._point_reward = 0.0
        truncated = (not terminated) and self._t >= self.max_steps
        self._frames.append(self._render_frame())
        info = {"score_agent": self.left_score, "score_opp": self.right_score}
        return self._observation(), float(reward), terminated, truncated, info

    def render(self):
        if self.render_mode == "human":
            surf = pygame.transform.scale(
                self.screen, (SCREEN_SIZE * 4, SCREEN_SIZE * 4)
            )
            pygame.display.get_surface().blit(surf, (0, 0))
            pygame.display.flip()
        return self._render_frame()

    # ------------------ внутренняя физика ------------------
    def _serve_ball(self) -> None:
        self.ball_x = SCREEN_SIZE / 2
        self.ball_y = SCREEN_SIZE / 2
        self.ball_vx = 2.2 * self.rng.choice([-1.0, 1.0])
        self.ball_vy = float(self.rng.uniform(-1.5, 1.5))

    def _move_opponent(self) -> None:
        target = self.ball_y + self.rng.normal(0, 4 * (1 - self.opponent_skill))
        diff = target - (self.right_y + PADDLE_H / 2)
        move = float(np.clip(diff, -5, 5)) * self.opponent_skill
        self.right_y = int(
            np.clip(self.right_y + move, 0, SCREEN_SIZE - PADDLE_H)
        )

    def _physics_step(self) -> None:
        self.ball_x += self.ball_vx
        self.ball_y += self.ball_vy
        # отскоки от верхней и нижней стенок
        if self.ball_y <= 0:
            self.ball_y = -self.ball_y
            self.ball_vy = abs(self.ball_vy)
        elif self.ball_y >= SCREEN_SIZE - BALL_SIZE:
            self.ball_y = 2 * (SCREEN_SIZE - BALL_SIZE) - self.ball_y
            self.ball_vy = -abs(self.ball_vy)
        self.ball_vy = float(np.clip(self.ball_vy, -3, 3))

        # ракетка игрока (левая)
        if self.ball_x <= PADDLE_W and self.ball_vx < 0:
            if self.left_y <= self.ball_y + BALL_SIZE and self.ball_y <= self.left_y + PADDLE_H:
                self.ball_vx = abs(self.ball_vx) * 1.02
                self.ball_vy += (self.ball_y - (self.left_y + PADDLE_H / 2)) * 0.08

        # ракетка противника (правая)
        if self.ball_x >= SCREEN_SIZE - PADDLE_W - BALL_SIZE and self.ball_vx > 0:
            if self.right_y <= self.ball_y + BALL_SIZE and self.ball_y <= self.right_y + PADDLE_H:
                self.ball_vx = -abs(self.ball_vx)

        # голы
        if self.ball_x < -2:
            self.right_score += 1
            self._point_reward = -1.0
            self._serve_ball()
        elif self.ball_x > SCREEN_SIZE + 2:
            self.left_score += 1
            self._point_reward = 1.0
            self._serve_ball()

    # ------------------ рендер и наблюдение ------------------
    def _render_frame(self) -> np.ndarray:
        surf = self.screen
        surf.fill((0, 0, 0))
        pygame.draw.rect(surf, (255, 255, 255), (0, int(self.left_y), PADDLE_W, PADDLE_H))
        pygame.draw.rect(
            surf, (255, 255, 255),
            (SCREEN_SIZE - PADDLE_W, int(self.right_y), PADDLE_W, PADDLE_H),
        )
        pygame.draw.rect(
            surf, (255, 255, 255), (int(self.ball_x), int(self.ball_y), BALL_SIZE, BALL_SIZE)
        )
        arr = pygame.surfarray.array3d(surf)  # (W, H, 3)
        gray = (
            0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
        ).astype(np.uint8)
        return np.ascontiguousarray(np.transpose(gray, (1, 0)))  # (H, W)

    def _observation(self) -> np.ndarray:
        return np.stack(list(self._frames)).astype(np.uint8)
