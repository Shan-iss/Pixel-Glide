import pygame
from settings import *

class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, level):
        super().__init__()

        self.image = pygame.Surface((40, 40))
        self.image.fill(RED)
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)

        self.speed = 2 + (level * 0.3)
        self.direction = 1

    def update(self):
        self.rect.x += self.speed * self.direction

        if self.rect.left < 0 or self.rect.right > WORLD_WIDTH:
            self.direction *= -1