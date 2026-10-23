import numpy as np


class Track:
    def __init__(self):
        # Простая овальная трасса: центр (0,0), радиусы 80 и 50
        self.outer_rx, self.outer_ry = 80.0, 50.0
        self.inner_rx, self.inner_ry = 60.0, 30.0

    def is_collision(self, x, y):
        outer = (x / self.outer_rx) ** 2 + (y / self.outer_ry) ** 2 > 1.0
        inner = (x / self.inner_rx) ** 2 + (y / self.inner_ry) ** 2 < 1.0
        return outer or inner

    def get_progress(self, x, y):
        # Угол вдоль овала как приближение прогресса
        angle = np.arctan2(y / self.outer_ry, x / self.outer_rx)
        return (angle + np.pi) / (2 * np.pi)

    def raycast(self, x, y, angle, max_dist=30.0):
        # Упрощённо: расстояния до границ на основе текущего положения
        # В реальном проекте — трассировка лучей
        left = max(0.0, 20.0 - abs(x) * 0.1)
        right = max(0.0, 20.0 - abs(y) * 0.1)
        ahead = max(0.0, 30.0 - self.get_progress(x, y) * 10)
        return left, right, ahead