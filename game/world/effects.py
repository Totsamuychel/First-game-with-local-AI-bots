import pygame
import math
import random
from game.config import *

class DamageIndicator:
    """Индикатор урона"""
    def __init__(self, x, y, damage, color=(255, 0, 0)):
        self.x = x
        self.y = y
        self.damage = damage
        self.color = color
        self.timer = 60  # 1 секунда при 60 FPS
        self.start_y = y
    
    def update(self):
        """Обновление индикатора"""
        self.timer -= 1
        self.y = self.start_y - (60 - self.timer) * 0.5  # Движение вверх
        return self.timer > 0
    
    def draw(self, screen, camera):
        """Отрисовка индикатора"""
        if self.timer <= 0:
            return
        
        screen_x = self.x - camera.x
        screen_y = self.y - camera.y
        
        # Прозрачность уменьшается со временем
        alpha = int(255 * (self.timer / 60))
        
        font = pygame.font.Font(None, 20)
        text = font.render(f"-{self.damage}", True, self.color)
        
        # Создаем поверхность с альфа-каналом
        text_surface = pygame.Surface(text.get_size(), pygame.SRCALPHA)
        text_surface.set_alpha(alpha)
        text_surface.blit(text, (0, 0))
        
        screen.blit(text_surface, (screen_x, screen_y))

class LevelUpEffect:
    """Эффект повышения уровня"""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.timer = 120  # 2 секунды
        self.particles = []
        
        # Создаем частицы
        for _ in range(20):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(1, 3)
            self.particles.append({
                'x': x,
                'y': y,
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed,
                'life': random.randint(60, 120)
            })
    
    def update(self):
        """Обновление эффекта"""
        self.timer -= 1
        
        # Обновляем частицы
        for particle in self.particles[:]:
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']
            particle['life'] -= 1
            
            if particle['life'] <= 0:
                self.particles.remove(particle)
        
        return self.timer > 0 and len(self.particles) > 0
    
    def draw(self, screen, camera):
        """Отрисовка эффекта"""
        if self.timer <= 0:
            return
        
        # Отрисовываем частицы
        for particle in self.particles:
            screen_x = particle['x'] - camera.x
            screen_y = particle['y'] - camera.y
            
            alpha = int(255 * (particle['life'] / 120))
            color = (255, 255, 0, alpha)  # Золотой цвет
            
            pygame.draw.circle(screen, color[:3], (int(screen_x), int(screen_y)), 3)
        
        # Текст "LEVEL UP!"
        if self.timer > 60:
            font = pygame.font.Font(None, 36)
            text = font.render("LEVEL UP!", True, (255, 255, 0))
            screen_x = self.x - camera.x - text.get_width() // 2
            screen_y = self.y - camera.y - 50
            
            # Эффект мерцания
            alpha = int(255 * (0.5 + 0.5 * math.sin(self.timer * 0.3)))
            text_surface = pygame.Surface(text.get_size(), pygame.SRCALPHA)
            text_surface.set_alpha(alpha)
            text_surface.blit(text, (0, 0))
            
            screen.blit(text_surface, (screen_x, screen_y))

