import pygame
import math
import random
from game.config import *

class Teammate:
    """Тиммейт-помощник"""
    def __init__(self, x, y, owner_id):
        self.x = x
        self.y = y
        self.size = BOT_SIZE
        self.speed = BOT_SPEED
        self.owner_id = owner_id
        self.target_resource = None
        self.hp = 50
        self.max_hp = 50
        self.weapon = None
        self.attack_cooldown = 0
    
    def update(self, resources, resource_piles, enemies=None, current_world=WORLD_RESOURCE):
        # В мире ресурсов - собираем ресурсы
        if current_world == WORLD_RESOURCE:
            self._collect_resources(resources, resource_piles)
        # В мире базы - защищаем или атакуем
        elif current_world == WORLD_BASE and enemies:
            self._combat_behavior(enemies)
        
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
    
    def _collect_resources(self, resources, resource_piles):
        """Поведение сбора ресурсов"""
        # Найти ближайший ресурс или кучу
        targets = resources + resource_piles
        
        if not self.target_resource or self.target_resource not in targets:
            closest_target = None
            closest_distance = float('inf')
            
            for target in targets:
                distance = math.sqrt((self.x - target.x)**2 + (self.y - target.y)**2)
                if distance < closest_distance:
                    closest_distance = distance
                    closest_target = target
            
            self.target_resource = closest_target
        
        # Двигаться к цели
        if self.target_resource:
            dx = self.target_resource.x - self.x
            dy = self.target_resource.y - self.y
            distance = math.sqrt(dx**2 + dy**2)
            
            if distance > 5:  # Не подходить слишком близко
                # Нормализуем направление движения
                move_x = (dx / distance) * self.speed
                move_y = (dy / distance) * self.speed
                
                # Проверяем новую позицию
                new_x = self.x + move_x
                new_y = self.y + move_y
                
                # Проверяем границы мира и препятствия
                new_x = max(self.size, min(new_x, WORLD_WIDTH - self.size))
                new_y = max(self.size, min(new_y, WORLD_HEIGHT - self.size))
                
                # Если застряли (не двигаемся), попробуем обойти препятствие
                if abs(new_x - self.x) < 0.1 and abs(new_y - self.y) < 0.1:
                    # Случайное отклонение для обхода препятствий
                    angle = random.uniform(-math.pi/2, math.pi/2)
                    new_x = self.x + self.speed * math.cos(angle)
                    new_y = self.y + self.speed * math.sin(angle)
                    new_x = max(self.size, min(new_x, WORLD_WIDTH - self.size))
                    new_y = max(self.size, min(new_y, WORLD_HEIGHT - self.size))
                
                self.x = new_x
                self.y = new_y
            else:
                # Если достигли цели, сбрасываем её
                self.target_resource = None
    
    def _combat_behavior(self, enemies):
        """Боевое поведение"""
        if not enemies:
            return
        
        # Найти ближайшего врага
        closest_enemy = min(enemies, key=lambda e: math.sqrt((self.x - e.x)**2 + (self.y - e.y)**2))
        
        # Двигаться к врагу и атаковать
        dx = closest_enemy.x - self.x
        dy = closest_enemy.y - self.y
        distance = math.sqrt(dx**2 + dy**2)
        
        if distance > 30:  # Подойти ближе
            self.x += (dx / distance) * self.speed
            self.y += (dy / distance) * self.speed
        elif self.attack_cooldown == 0:  # Атаковать
            self.attack(closest_enemy)
    
    def collect_resource(self, resource):
        """Собрать ресурс"""
        distance = math.sqrt((self.x - resource.x)**2 + (self.y - resource.y)**2)
        if distance < self.size + resource.size:
            return True
        return False
    
    def attack(self, target):
        """Атаковать цель"""
        if self.attack_cooldown > 0:
            return False
        
        damage = 15 if not self.weapon else WEAPON_STATS.get(self.weapon, {'damage': 15})['damage']
        target.take_damage(damage)
        self.attack_cooldown = 45
        return True
    
    def take_damage(self, damage):
        """Получить урон"""
        self.hp -= damage
        return self.hp <= 0
    
    def draw(self, screen, camera):
        screen_x = self.x - camera.x
        screen_y = self.y - camera.y
        
        # Основной круг
        pygame.draw.circle(screen, GREEN, (int(screen_x), int(screen_y)), self.size)
        
        # Полоска здоровья
        bar_width = self.size * 2
        bar_height = 3
        bar_x = screen_x - bar_width // 2
        bar_y = screen_y - self.size - 8
        
        pygame.draw.rect(screen, RED, (bar_x, bar_y, bar_width, bar_height))
        hp_width = int((self.hp / self.max_hp) * bar_width)
        pygame.draw.rect(screen, GREEN, (bar_x, bar_y, hp_width, bar_height))

