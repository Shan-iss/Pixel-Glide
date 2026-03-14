import pygame

class ParallaxBackground:
    def __init__(self, width, height):
        self.width = width
        self.height = height

        # Layer 1 (sky)
        self.sky = pygame.Surface((width, height))
        self.sky.fill((135, 206, 235))

        # Layer 2 (far hills)
        self.hills = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.rect(self.hills, (100, 200, 100), (0, height-200, width, 200))

        # Layer 3 (ground shade)
        self.ground = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.rect(self.ground, (50, 150, 50), (0, height-120, width, 120))

    def draw(self, screen, camera_x):
        screen.blit(self.sky, (0, 0))
        screen.blit(self.hills, (-camera_x * 0.3, 0))
        screen.blit(self.ground, (-camera_x * 0.6, 0))