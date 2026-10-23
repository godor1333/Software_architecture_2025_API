import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pygame
from .track import Track
from .commands import CommandInvoker, ThrottleCommand, BrakeCommand, SteerCommand
from .render import Renderer


class RacingEnv(gym.Env):
    """Гоночная среда: цель — пройти трассу, не врезавшись, максимизируя награду за время."""

    metadata = {"render_modes": ["human", "rgb_array"]}

    def __init__(self, render_mode=None):
        super().__init__()
        self.render_mode = render_mode

        # Action: [gas, brake, steer] ∈ [-1, 1]
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(3,), dtype=np.float32)

        # Observation: [x, y, angle, speed, dist_left, dist_right, dist_ahead]
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(7,), dtype=np.float32
        )

        self.track = Track()
        self.invoker = CommandInvoker()
        self.renderer = None
        if render_mode == "human":
            pygame.init()
            self.renderer = Renderer(self.track)

        self.reset()

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.car_x = 0.0
        self.car_y = 0.0
        self.car_angle = 0.0
        self.speed = 0.0
        self.steps = 0
        self.max_steps = 2000
        self.crashed = False
        self.progress = 0.0
        self._last_progress = 0.0
        return self._get_obs(), {}

    def _get_obs(self):
        left, right, ahead = self.track.raycast(self.car_x, self.car_y, self.car_angle)
        return np.array(
            [self.car_x, self.car_y, self.car_angle, self.speed, left, right, ahead],
            dtype=np.float32,
        )

    def step(self, action):
        gas, brake, steer = action

        # Command pattern: инкапсулируем управляющие воздействия
        if gas > 0.1:
            self.invoker.execute(ThrottleCommand(self, float(gas)))
        if brake > 0.1:
            self.invoker.execute(BrakeCommand(self, float(brake)))
        if abs(steer) > 0.05:
            self.invoker.execute(SteerCommand(self, float(steer)))

        self._physics_update()
        self.steps += 1

        # Проверка столкновения
        self.crashed = self.track.is_collision(self.car_x, self.car_y)

        # Награда: прогресс вдоль трассы + штраф за аварию
        if self.crashed:
            reward = -10.0
            terminated = True
        else:
            delta_progress = self.progress - self._last_progress
            reward = delta_progress * 100.0
            self._last_progress = self.progress
            terminated = self.progress >= 1.0

        truncated = self.steps >= self.max_steps
        obs = self._get_obs()
        info = {"crashed": self.crashed, "progress": self.progress}

        if self.renderer:
            self.renderer.render(self.car_x, self.car_y, self.car_angle, self.speed)

        return obs, float(reward), terminated, truncated, info

    def _physics_update(self):
        # Упрощённая модель: газ ускоряет, тормоз замедляет, руль меняет угол
        dt = 0.1
        self.speed += self._accel * dt
        self.speed *= 0.98  # сопротивление
        if self.speed > 50:
            self.speed = 50

        self.car_angle += self._steer * dt * (0.5 + abs(self.speed) * 0.02)
        self.car_x += np.cos(self.car_angle) * self.speed * dt
        self.car_y += np.sin(self.car_angle) * self.speed * dt

        self.progress = self.track.get_progress(self.car_x, self.car_y)

        # Сброс временных команд
        self._accel = 0.0
        self._steer = 0.0

    def close(self):
        if self.renderer:
            pygame.quit()