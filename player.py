import pygame
from settings import *

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()

        self.width = 40
        self.height = 50

        self.image = pygame.Surface((self.width, self.height))
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)

        self.vel_x = 0
        self.vel_y = 0

        self.speed = 5
        self.jump_power = JUMP_POWER
        self.gravity = GRAVITY

        self.on_ground = False

        self.hp = 3
        self.invincible = False
        self.invincible_timer = 0

        # Animation State
        self.state = "idle"
        self.animation_timer = 0
        self.animation_frame = 0

    def handle_input(self):
        keys = pygame.key.get_pressed()

        self.vel_x = 0

        if keys[pygame.K_LEFT]:
            self.vel_x = -self.speed

        if keys[pygame.K_RIGHT]:
            self.vel_x = self.speed

    def apply_gravity(self):
        self.vel_y += self.gravity

    def jump(self):
        if self.on_ground:
            self.vel_y = self.jump_power
            self.on_ground = False

    def update(self, platforms):

        self.handle_input()
        self.apply_gravity()

        # Horizontal movement
        self.rect.x += self.vel_x

        # Vertical movement
        self.rect.y += self.vel_y
        self.on_ground = False

        for platform in platforms:
            if self.rect.colliderect(platform.rect):

                if self.vel_y > 0:
                    self.rect.bottom = platform.rect.top
                    self.vel_y = 0
                    self.on_ground = True

                elif self.vel_y < 0:
                    self.rect.top = platform.rect.bottom
                    self.vel_y = 0

        # Update animation state
        self.update_animation()

        # Invincibility timer
        if self.invincible:
            self.invincible_timer -= 1
            if self.invincible_timer <= 0:
                self.invincible = False

    def update_animation(self):

        if not self.on_ground:
            if self.vel_y < 0:
                self.state = "jump"
            else:
                self.state = "fall"

        else:
            if self.vel_x != 0:
                self.state = "run"
            else:
                self.state = "idle"

        # Simple color-based animation
        if self.state == "idle":
            self.image.fill((0, 0, 255))

        elif self.state == "run":
            self.animation_timer += 1
            if self.animation_timer % 10 < 5:
                self.image.fill((0, 100, 255))
            else:
                self.image.fill((0, 150, 255))

        elif self.state == "jump":
            self.image.fill((255, 200, 0))

        elif self.state == "fall":
            self.image.fill((255, 100, 0))

    def take_damage(self):
        if not self.invincible:
            self.hp -= 1
            self.invincible = True
            self.invincible_timer = 60