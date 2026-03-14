import pygame

def draw_text(screen, text, size, x, y):
    font = pygame.font.SysFont("arial", size)
    render = font.render(text, True, (255, 255, 255))
    screen.blit(render, (x, y))