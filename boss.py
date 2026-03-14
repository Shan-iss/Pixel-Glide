import pygame
import random
from settings import *

class Boss(pygame.sprite.Sprite):
    def __init__(self, x, y, level):
        super().__init__()

        self.image = pygame.Surface((80, 80))
        self.image.fill((128, 0, 128))

        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)

        self.hp = 3 + level // 3
        self.speed = 2 + (level * 0.3)
        self.direction = 1

        self.jump_cooldown = 0

    def update(self):

        # patrol movement
        self.rect.x += self.speed * self.direction

        if self.rect.left < 0 or self.rect.right > WORLD_WIDTH:
            self.direction *= -1

        # random jump behavior
        if self.jump_cooldown <= 0:
            if random.randint(0, 100) < 2:
                self.rect.y -= 60
                self.jump_cooldown = 60
        else:
            self.jump_cooldown -= 1
            self.rect.y += 2  # gravity effect

        # ground clamp
        if self.rect.y > 370:
            self.rect.y = 370

    def take_damage(self):
        self.hp -= 1