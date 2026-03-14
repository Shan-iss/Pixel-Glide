# level.py
from settings import LEVEL_LENGTH

class LevelManager:
    def __init__(self):
        self.current_level = 1
        self.distance = 0
        self.boss_spawned = False
        self.completed = False

    def update(self, scroll_speed):
        self.distance += scroll_speed

        if self.distance >= LEVEL_LENGTH[self.current_level]:
            self.boss_spawned = True

    def next_level(self):
        self.current_level += 1
        self.distance = 0
        self.boss_spawned = False
        self.completed = False