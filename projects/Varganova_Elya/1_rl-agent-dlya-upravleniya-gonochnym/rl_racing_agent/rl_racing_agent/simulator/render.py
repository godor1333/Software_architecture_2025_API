import pygame
import numpy as np


class Renderer:
    def __init__(self, track):
        self.track = track
        self.screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("RL Racing Agent")
        self.clock = pygame.time.Clock()

    def render(self, car_x, car_y, car_angle, speed):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

        self.screen.fill((30, 30, 30))

        # Рисуем трассу (упрощённо — овал)
        cx, cy = 400, 300
        rect = pygame.Rect(cx - 200, cy - 120, 400, 240)
        pygame.draw.ellipse(self.screen, (80, 80, 80), rect, 40)

        # Машина
        px = cx + car_x * 3
        py = cy + car_y * 3
        pygame.draw.circle(self.screen, (255, 80, 80), (int(px), int(py)), 8)

        font = pygame.font.SysFont(None, 24)
        text = font.render(f"Speed: {speed:.1f}", True, (255, 255, 255))
        self.screen.blit(text, (10, 10))

        pygame.display.flip()
        self.clock.tick(60)