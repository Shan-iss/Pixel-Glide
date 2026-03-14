from platforms import Platform
from enemy import Enemy
from coin import Coin
from settings import WORLD_WIDTH

def generate_platforms(level):

    platforms = []
    coins = []

    segment_length = 400
    x = 0

    while x < WORLD_WIDTH:

        segment_type = (x // segment_length) % 4

        if segment_type == 0:
            platforms.append(Platform(x, 450, segment_length, 50))
            coins.append(Coin(x + 200, 400))

        elif segment_type == 1:
            platforms.append(Platform(x, 450, segment_length - 120, 50))

        elif segment_type == 2:
            platforms.append(Platform(x, 450, segment_length, 50))
            platforms.append(Platform(x + 150, 360, 120, 20))
            coins.append(Coin(x + 200, 320))

        elif segment_type == 3:
            platforms.append(Platform(x, 450, segment_length, 50))
            platforms.append(Platform(x + 100, 400, 100, 20))
            platforms.append(Platform(x + 220, 350, 100, 20))
            coins.append(Coin(x + 240, 300))

        x += segment_length

    return platforms, coins


def generate_enemies(level, difficulty):

    enemies = []
    x = 600
    segment_length = 400

    while x < WORLD_WIDTH - 300:

        if (x // segment_length) % 4 in [0, 2]:
            enemy = Enemy(x, 410, level)
            enemy.speed *= difficulty
            enemies.append(enemy)

        x += 600

    return enemies