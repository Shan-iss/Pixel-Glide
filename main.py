import pygame
import sys
import csv
import os
import random

from settings import *
from player import Player
from goal import Goal
from boss import Boss
from pcg import generate_platforms, generate_enemies
from background import ParallaxBackground

pygame.init()
pygame.mixer.init()

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pixel Glide")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 26)

# ================= BACKGROUND =================
background = ParallaxBackground(WORLD_WIDTH, HEIGHT)

# ================= SAVE DATA =================
def save_game_data(level, score, total_time,
                   enemy_kills, boss_kills,
                   difficulty):

    file_exists = os.path.isfile("game_data.csv")

    with open("game_data.csv", mode="a", newline="") as file:
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow([
                "Level Reached",
                "Score",
                "Total Time (s)",
                "Enemy Kills",
                "Boss Kills",
                "Difficulty"
            ])

        writer.writerow([
            level,
            score,
            total_time,
            enemy_kills,
            boss_kills,
            round(difficulty, 2)
        ])

# ================= ADAPTIVE =================
difficulty_multiplier = 1.0

def update_difficulty(level_time, enemy_kills, damage_taken):
    global difficulty_multiplier

    performance_score = (
        (enemy_kills * 0.4) +
        ((60 - min(level_time, 60)) * 0.3) -
        (damage_taken * 0.3)
    )

    difficulty_multiplier += performance_score * 0.01
    difficulty_multiplier = max(0.7, min(2.5, difficulty_multiplier))

# ================= SCREEN SHAKE =================
shake_intensity = 0

def apply_screen_shake():
    if shake_intensity > 0:
        return pygame.math.Vector2(
            random.randint(-shake_intensity, shake_intensity),
            random.randint(-shake_intensity, shake_intensity)
        )
    return pygame.math.Vector2(0, 0)

# ================= INITIAL =================
level = 1
score = 0
enemy_kill_count = 0
boss_kill_count = 0
coin_count = 0
damage_taken_this_level = 0

spawn_x = 100
spawn_y = 300

platforms, coins = generate_platforms(level)
enemies = generate_enemies(level, difficulty_multiplier)

player = Player(spawn_x, spawn_y)
goal = Goal(WORLD_WIDTH - 100, 390)

boss = None
camera_x = 0.0
game_over = False
running = True

level_start_time = pygame.time.get_ticks()
total_start_time = pygame.time.get_ticks()

# ================= GAME LOOP =================
while running:
    clock.tick(FPS)

    background.draw(screen, camera_x)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE and not game_over:
                player.jump()
                jump_sound.play()

            if event.key == pygame.K_r and game_over:
                level = 1
                score = 0
                enemy_kill_count = 0
                boss_kill_count = 0
                coin_count = 0
                damage_taken_this_level = 0
                difficulty_multiplier = 1.0
                shake_intensity = 0

                platforms, coins = generate_platforms(level)
                enemies = generate_enemies(level, difficulty_multiplier)

                player = Player(spawn_x, spawn_y)
                goal.rect.topleft = (WORLD_WIDTH - 100, 390)

                boss = None
                camera_x = 0.0
                game_over = False

                level_start_time = pygame.time.get_ticks()
                total_start_time = pygame.time.get_ticks()

    if not game_over:

        player.update(platforms)

        for enemy in enemies:
            enemy.update()

        if boss:
            boss.update()

        # FALL
        if player.rect.top > HEIGHT:
            player.take_damage()
            damage_sound.play()
            damage_taken_this_level += 1
            shake_intensity = 6

            if player.hp > 0:
                player.rect.topleft = (spawn_x, spawn_y)
                player.vel_x = 0
                player.vel_y = 0
                camera_x = 0.0

        # SMOOTH CAMERA
        target_x = player.rect.centerx - WIDTH // 2
        camera_x += (target_x - camera_x) * 0.08
        camera_x = max(0, min(WORLD_WIDTH - WIDTH, camera_x))

        # ENEMY COLLISION
        for enemy in enemies[:]:
            if player.rect.colliderect(enemy.rect):
                if player.vel_y > 0:
                    enemies.remove(enemy)
                    player.vel_y = JUMP_POWER
                    score += 100
                    enemy_kill_count += 1
                else:
                    player.take_damage()
                    damage_sound.play()
                    damage_taken_this_level += 1
                    shake_intensity = 6

        # BOSS COLLISION
        if boss and player.rect.colliderect(boss.rect):
            if player.vel_y > 0:
                boss.take_damage()
                boss_sound.play()
                shake_intensity = 8
                player.vel_y = JUMP_POWER

                if boss.hp <= 0:
                    score += 1000
                    boss_kill_count += 1
                    boss = None
            else:
                player.take_damage()
                damage_sound.play()
                damage_taken_this_level += 1
                shake_intensity = 6

        # COIN
        for coin in coins[:]:
            if player.rect.colliderect(coin.rect):
                coins.remove(coin)
                score += 50
                coin_count += 1
                coin_sound.play()

        if player.hp <= 0:
            game_over = True

        # GOAL
        if player.rect.colliderect(goal.rect):

            current_time = pygame.time.get_ticks()
            level_time = (current_time - level_start_time) // 1000

            update_difficulty(level_time,
                              enemy_kill_count,
                              damage_taken_this_level)

            damage_taken_this_level = 0

            score += 500
            level += 1

            platforms, coins = generate_platforms(level)
            enemies = generate_enemies(level, difficulty_multiplier)

            if level % 3 == 0:
                boss = Boss(WORLD_WIDTH - 400, 370, level)
            else:
                boss = None

            player.rect.topleft = (spawn_x, spawn_y)
            player.vel_x = 0
            player.vel_y = 0
            goal.rect.topleft = (WORLD_WIDTH - 100, 390)
            camera_x = 0.0
            level_start_time = pygame.time.get_ticks()

        current_time = pygame.time.get_ticks()
        total_time = (current_time - total_start_time) // 1000

    else:
        current_time = pygame.time.get_ticks()
        total_time = (current_time - total_start_time) // 1000

    # APPLY SHAKE
    shake_offset = apply_screen_shake()
    if shake_intensity > 0:
        shake_intensity -= 1

    # DRAW WORLD
    for platform in platforms:
        screen.blit(platform.image,
                    (int(platform.rect.x - camera_x + shake_offset.x),
                     platform.rect.y + shake_offset.y))

    for coin in coins:
        screen.blit(coin.image,
                    (int(coin.rect.x - camera_x + shake_offset.x),
                     coin.rect.y + shake_offset.y))

    for enemy in enemies:
        screen.blit(enemy.image,
                    (int(enemy.rect.x - camera_x + shake_offset.x),
                     enemy.rect.y + shake_offset.y))

    if boss:
        screen.blit(boss.image,
                    (int(boss.rect.x - camera_x + shake_offset.x),
                     boss.rect.y + shake_offset.y))

    screen.blit(goal.image,
                (int(goal.rect.x - camera_x + shake_offset.x),
                 goal.rect.y + shake_offset.y))

    if not player.invincible or player.invincible_timer % 10 < 5:
        screen.blit(player.image,
                    (int(player.rect.x - camera_x + shake_offset.x),
                     player.rect.y + shake_offset.y))

    # HUD
    screen.blit(font.render(f"HP: {player.hp}", True, BLACK), (20, 20))
    screen.blit(font.render(f"Level: {level}", True, BLACK), (20, 40))
    screen.blit(font.render(f"Score: {score}", True, BLACK), (20, 60))
    screen.blit(font.render(f"Coins: {coin_count}", True, BLACK), (20, 80))
    screen.blit(font.render(f"Difficulty: {round(difficulty_multiplier,2)}", True, BLACK), (20, 100))
    screen.blit(font.render(f"Time: {total_time}s", True, BLACK), (20, 120))

    if game_over:
        screen.blit(font.render("GAME OVER - Press R to Restart", True, RED),
                    (WIDTH // 2 - 200, HEIGHT // 2))

        save_game_data(level, score, total_time,
                       enemy_kill_count, boss_kill_count,
                       difficulty_multiplier)

    pygame.display.update()

pygame.quit()
sys.exit()