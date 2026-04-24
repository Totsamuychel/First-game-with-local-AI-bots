import pygame
import math
from game.config import *

class Enemy:
    """Enemy in the dungeon"""
    def __init__(self, x, y, enemy_type="goblin"):
        self.x = x
        self.y = y
        self.size = 15
        self.enemy_type = enemy_type
        self.max_hp = 50
        self.hp = self.max_hp
        self.damage = 15
        self.speed = 1.5
        self.target = None
        self.attack_cooldown = 0
        self.alive = True

        # Enemy colors
        self.enemy_colors = {
            'goblin': (100, 50, 0),
            'orc': (50, 100, 50),
            'skeleton': (200, 200, 200),
            'demon': (150, 0, 0)
        }
        self.color = self.enemy_colors.get(enemy_type, RED)

    def update(self, players):
        """Update enemy state"""
        if not self.alive:
            return

        # Find nearest player
        closest_player = None
        closest_distance = float('inf')

        for player in players:
            distance = math.sqrt((self.x - player.x)**2 + (self.y - player.y)**2)
            if distance < closest_distance:
                closest_distance = distance
                closest_player = player

        if closest_player and closest_distance < 200:  # Aggro radius
            # Move towards player
            dx = closest_player.x - self.x
            dy = closest_player.y - self.y
            distance = math.sqrt(dx**2 + dy**2)

            if distance > 0:
                self.x += (dx / distance) * self.speed
                self.y += (dy / distance) * self.speed

            # Attack player
            if closest_distance < 30 and self.attack_cooldown == 0:
                closest_player.take_damage(self.damage)
                self.attack_cooldown = 60  # 1 second at 60 FPS

        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

    def take_damage(self, damage):
        """Take damage"""
        self.hp -= damage
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            return True  # Enemy died
        return False

    def draw(self, screen, camera):
        if not self.alive:
            return
        screen_x = self.x - camera.x
        screen_y = self.y - camera.y

        # Enemy circle
        pygame.draw.circle(screen, self.color, (int(screen_x), int(screen_y)), self.size)

        # Health bar
        bar_width = self.size * 2
        bar_height = 4
        bar_x = screen_x - bar_width // 2
        bar_y = screen_y - self.size - 10

        # Health bar background
        pygame.draw.rect(screen, RED, (bar_x, bar_y, bar_width, bar_height))
        # Current health
        hp_width = int((self.hp / self.max_hp) * bar_width)
        pygame.draw.rect(screen, GREEN, (bar_x, bar_y, hp_width, bar_height))
