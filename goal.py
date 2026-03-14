import pygame

class Goal(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((30, 60))
        self.image.fill((255, 215, 0))
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)