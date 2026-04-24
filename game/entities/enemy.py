import pygame
import math
from game.config import *

class Enemy:
    """Враг в подземелье"""
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
        
        # Цвета врагов
        self.enemy_colors = {
            'goblin': (100, 50, 0),
            'orc': (50, 100, 50),
            'skeleton': (200, 200, 200),
            'demon': (150, 0, 0)
        }
        self.color = self.enemy_colors.get(enemy_type, RED)
    
    def update(self, players):
        """Обновление врага"""
        if not self.alive:
            return
        
        # Найти ближайшего игрока
        closest_player = None
        closest_distance = float('inf')
        
        for player in players:
            distance = math.sqrt((self.x - player.x)**2 + (self.y - player.y)**2)
            if distance < closest_distance:
                closest_distance = distance
                closest_player = player
        
        if closest_player and closest_distance < 200:  # Радиус агро
            # Двигаться к игроку
            dx = closest_player.x - self.x
            dy = closest_player.y - self.y
            distance = math.sqrt(dx**2 + dy**2)
            
            if distance > 20:  # Подойти ближе
                self.x += (dx / distance) * self.speed
                self.y += (dy / distance) * self.speed
            elif self.attack_cooldown == 0:  # Атаковать
                closest_player.take_damage(self.damage)
                self.attack_cooldown = 60
        
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
    
    def take_damage(self, damage, game=None):
        """Получить урон"""
        self.hp -= damage
        
        # Создаем индикатор урона если передана ссылка на игру
        if game:
            game.add_damage_indicator(self.x, self.y - 20, damage, (255, 100, 100))
        
        if self.hp <= 0:
            self.alive = False
            return True
        return False
    
    def draw(self, screen, camera):
        if not self.alive:
            return
            
        screen_x = self.x - camera.x
        screen_y = self.y - camera.y
        
        # Основной круг врага
        pygame.draw.circle(screen, self.color, (int(screen_x), int(screen_y)), self.size)
        pygame.draw.circle(screen, BLACK, (int(screen_x), int(screen_y)), self.size, 2)
        
        # Полоска здоровья
        if self.hp < self.max_hp:
            bar_width = self.size * 2
            bar_height = 3
            bar_x = screen_x - bar_width // 2
            bar_y = screen_y - self.size - 8
            
            pygame.draw.rect(screen, RED, (bar_x, bar_y, bar_width, bar_height))
            hp_width = int((self.hp / self.max_hp) * bar_width)
            pygame.draw.rect(screen, GREEN, (bar_x, bar_y, hp_width, bar_height))

