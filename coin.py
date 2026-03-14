import pygame

class Coin(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()

        self.image = pygame.Surface((20, 20))
        self.image.fill((255, 215, 0))  # gold color

        self.rect = self.image.get_rect()
        self.rect.center = (x, y)