import pygame
from game.config import *

class Camera:
    """Камера для отслеживания игрока"""
    def __init__(self):
        self.x = 0
        self.y = 0
    
    def update(self, target_x, target_y):
        self.x = target_x - SCREEN_WIDTH // 2
        self.y = target_y - SCREEN_HEIGHT // 2
        
        # Ограничения камеры
        self.x = max(0, min(self.x, WORLD_WIDTH - SCREEN_WIDTH))
        self.y = max(0, min(self.y, WORLD_HEIGHT - SCREEN_HEIGHT))

