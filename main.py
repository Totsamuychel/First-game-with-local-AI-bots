"""
МНОГОМИРОВАЯ 2D-ИГРА: СБОР РЕСУРСОВ, СТРОИТЕЛЬСТВО И PVP
========================================================

УПРАВЛЕНИЕ:
- WASD или стрелки: движение игрока
- ЛКМ: размещение построек/атака/сбор ресурсов
- ПКМ: использование оружия/способностей
- E: взаимодействие с порталами
- Пробел: переключение между режимами (исследование/строительство/бой)
- 1-5: выбор типа постройки/оружия
- TAB: инвентарь
- ESC: выход

МЕХАНИКА:
МИР РЕСУРСОВ (PvP отключен):
- Собирайте 5 типов ресурсов: дерево, камень, железо, золото, кристаллы
- Находите тиммейтов и оружие в кучах ресурсов
- Используйте портал для возврата на базу

МИР БАЗЫ (PvP включен):
- Стройте и расширяйте базу различными постройками
- Создавайте оружие и броню из собранных ресурсов
- Атакуйте базы других игроков
- Защищайте свою базу башнями и стенами

Требования: pip install pygame
"""

import pygame
import random
import math
import sys
import json
import os
import ollama
import threading
import time
from enum import Enum
from database import GameDatabase
from dialogs import Dialog, SaveDialog, LoadDialog, show_exit_confirmation, show_overwrite_confirmation
from building_interfaces import WorkshopInterface, ShopInterface
# -*- coding: utf-8 -*-
# ===============================================
# НАСТРОЙКИ ИГРЫ (БАЛАНСИРОВКА)
# ===============================================

# Размеры экрана
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800

# Размеры игрового мира
WORLD_WIDTH = 2000
WORLD_HEIGHT = 1500

# Настройки игрока
PLAYER_SPEED = 3
PLAYER_SIZE = 15
PLAYER_MAX_HP = 100
PLAYER_ATTACK_RANGE = 50

# Настройки ботов/тиммейтов
BOT_SPEED = 2
BOT_SIZE = 12
TEAMMATE_SPAWN_CHANCE = 0.0005  # Вероятность появления тиммейта в куче ресурсов

# Настройки ресурсов
RESOURCE_SIZE = 8
INITIAL_RESOURCES = 150
RESOURCE_SPAWN_RATE = 0.03
RESOURCE_SPAWN_CENTER_X = WORLD_WIDTH // 2
RESOURCE_SPAWN_CENTER_Y = WORLD_HEIGHT // 2
RESOURCE_SPAWN_RADIUS = 300

# Типы ресурсов
RESOURCE_TYPES = {
    'wood': {'color': (139, 69, 19), 'name': 'Дерево'},
    'stone': {'color': (128, 128, 128), 'name': 'Камень'},
    'iron': {'color': (169, 169, 169), 'name': 'Железо'},
    'gold': {'color': (255, 215, 0), 'name': 'Золото'},
    'crystal': {'color': (147, 0, 211), 'name': 'Кристалл'},
    # Уникальные ресурсы подземелья
    'shadow_essence': {'color': (50, 0, 50), 'name': 'Теневая эссенция'},
    'demon_blood': {'color': (150, 0, 0), 'name': 'Кровь демона'},
    'soul_gem': {'color': (0, 255, 255), 'name': 'Камень души'},
    'void_crystal': {'color': (100, 0, 100), 'name': 'Кристалл пустоты'}
}

# Настройки построек
BUILDING_COSTS = {
    'wall': {'wood': 3, 'stone': 2},
    'tower': {'stone': 5, 'iron': 3},
    'barracks': {'wood': 8, 'iron': 5},
    'workshop': {'wood': 10, 'iron': 8, 'gold': 3},
    'portal': {'crystal': 5, 'gold': 10},
    'dungeon_portal': {'crystal': 50, 'gold': 30, 'iron': 20},  # Портал в подземелье
    'shop': {'wood': 15, 'gold': 10, 'iron': 5},
    'storage': {'wood': 20, 'stone': 15, 'iron': 10},
    'base_expansion': {'crystal': 20, 'gold': 15}
}

# Размеры построек (в клетках сетки)
BUILDING_SIZES = {
    'wall': {'width': 1, 'height': 1},
    'tower': {'width': 2, 'height': 2},
    'barracks': {'width': 3, 'height': 2},
    'workshop': {'width': 3, 'height': 3},
    'portal': {'width': 2, 'height': 2},
    'dungeon_portal': {'width': 3, 'height': 3},
    'shop': {'width': 4, 'height': 3},
    'storage': {'width': 3, 'height': 2}
}

# Настройки сетки строительства
GRID_SIZE = 20  # Размер одной клетки сетки
GRID_COLOR = (100, 100, 100, 50)  # Полупрозрачный серый

TOWER_RANGE = 100
TOWER_DAMAGE = 20
TOWER_ATTACK_SPEED = 90  # кадров между атаками

# Настройки оружия
WEAPON_STATS = {
    'sword': {'damage': 25, 'range': 30, 'cost': {'iron': 3, 'wood': 1}},
    'bow': {'damage': 15, 'range': 80, 'cost': {'wood': 3, 'iron': 1}},
    'axe': {'damage': 35, 'range': 25, 'cost': {'iron': 4, 'wood': 2}},
    'staff': {'damage': 40, 'range': 60, 'cost': {'crystal': 2, 'gold': 1}},
    # Оружие из ресурсов подземелья
    'shadow_blade': {'damage': 50, 'range': 35, 'cost': {'shadow_essence': 5, 'iron': 3}},
    'demon_axe': {'damage': 60, 'range': 30, 'cost': {'demon_blood': 4, 'iron': 5}},
    'soul_staff': {'damage': 70, 'range': 70, 'cost': {'soul_gem': 3, 'crystal': 2}},
    'void_sword': {'damage': 80, 'range': 40, 'cost': {'void_crystal': 4, 'shadow_essence': 3}}
}

# Настройки брони
ARMOR_STATS = {
    'leather': {'defense': 5, 'cost': {'wood': 5}},
    'iron': {'defense': 15, 'cost': {'iron': 8}},
    'gold': {'defense': 25, 'cost': {'gold': 5, 'iron': 3}},
    'crystal': {'defense': 40, 'cost': {'crystal': 3, 'gold': 2}},
    'legendary': {'defense': 60, 'cost': {}},  # Только из подземелий
    # Броня из ресурсов подземелья
    'shadow_armor': {'defense': 45, 'cost': {'shadow_essence': 8, 'iron': 5}},
    'demon_armor': {'defense': 55, 'cost': {'demon_blood': 6, 'iron': 8}},
    'soul_armor': {'defense': 65, 'cost': {'soul_gem': 4, 'crystal': 3}},
    'void_armor': {'defense': 75, 'cost': {'void_crystal': 5, 'shadow_essence': 4}}
}

# Аксессуары
ACCESSORY_STATS = {
    'ring_strength': {'damage_bonus': 10, 'cost': {'gold': 3}},
    'ring_defense': {'defense_bonus': 8, 'cost': {'gold': 3}},
    'ring_speed': {'speed_bonus': 1, 'cost': {'gold': 3}},
    'amulet_health': {'health_bonus': 25, 'cost': {'crystal': 2}},
    'amulet_luck': {'drop_chance_bonus': 0.15, 'cost': {'crystal': 2}},
    'belt_inventory': {'inventory_bonus': 5, 'cost': {'iron': 5, 'gold': 2}},
    'boots_speed': {'speed_bonus': 2, 'cost': {'iron': 4}},
    'gloves_mining': {'mining_bonus': 0.2, 'cost': {'iron': 3}},
    # Легендарные аксессуары из подземелья
    'legendary_crown': {'damage_bonus': 20, 'defense_bonus': 15, 'health_bonus': 50, 'cost': {}},
    'shadow_cloak': {'speed_bonus': 3, 'defense_bonus': 10, 'cost': {}},
    'demon_ring': {'damage_bonus': 25, 'health_bonus': 30, 'cost': {}},
    'void_amulet': {'drop_chance_bonus': 0.5, 'inventory_bonus': 10, 'cost': {}},
    # Аксессуары из ресурсов подземелья
    'shadow_boots': {'speed_bonus': 4, 'cost': {'shadow_essence': 3, 'iron': 2}},
    'demon_gloves': {'damage_bonus': 15, 'cost': {'demon_blood': 3, 'iron': 2}},
    'soul_amulet': {'health_bonus': 40, 'cost': {'soul_gem': 2, 'crystal': 1}},
    'void_ring': {'speed_bonus': 2, 'defense_bonus': 12, 'cost': {'void_crystal': 2, 'gold': 1}},
    'essence_belt': {'inventory_bonus': 8, 'mining_bonus': 0.3, 'cost': {'shadow_essence': 4, 'demon_blood': 2}},
    'blood_crown': {'damage_bonus': 18, 'health_bonus': 35, 'cost': {'demon_blood': 5, 'soul_gem': 1}}
}

# Настройки инвентаря
INVENTORY_SLOTS = 10
EQUIPMENT_SLOTS = {
    'weapon': {'x': 50, 'y': 50},
    'armor': {'x': 50, 'y': 100},
    'accessory1': {'x': 50, 'y': 150},
    'accessory2': {'x': 50, 'y': 200},
    'accessory3': {'x': 50, 'y': 250}
}

# Типы квестов
QUEST_TYPES = {
    'collect': 'Собрать ресурсы',
    'build': 'Построить здания',
    'kill': 'Убить врагов',
    'explore': 'Исследовать территорию'
}

# Награды за квесты
QUEST_REWARDS = {
    'small': {'gold': 5, 'crystal': 1},
    'medium': {'gold': 10, 'crystal': 3, 'iron': 5},
    'large': {'gold': 20, 'crystal': 8, 'iron': 10}
}

# Миры
WORLD_RESOURCE = 0  # Мир сбора ресурсов (PvP отключен)
WORLD_BASE = 1      # Мир базы (PvP включен)
WORLD_DUNGEON = 2   # Третье измерение с врагами и уникальными предметами

# Состояния игры
class GameState(Enum):
    MENU = 0
    PLAYING = 1
    SETTINGS = 2

# Цвета
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
PURPLE = (255, 0, 255)
CYAN = (0, 255, 255)
ORANGE = (255, 165, 0)
BROWN = (139, 69, 19)
GRAY = (128, 128, 128)
DARK_GREEN = (0, 128, 0)
LIGHT_BLUE = (173, 216, 230)
DARK_RED = (139, 0, 0)
GOLD = (255, 215, 0)

# ===============================================
# КЛАССЫ ИГРОВЫХ ОБЪЕКТОВ
# ===============================================

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

class Resource:
    """Ресурс для сбора"""
    def __init__(self, x, y, resource_type=None):
        self.x = x
        self.y = y
        self.size = RESOURCE_SIZE
        self.type = resource_type or random.choice(list(RESOURCE_TYPES.keys()))
        self.color = RESOURCE_TYPES[self.type]['color']
        self.amount = random.randint(1, 3)
        self.collected = False
    
    def draw(self, screen, camera):
        screen_x = self.x - camera.x
        screen_y = self.y - camera.y
        if -self.size <= screen_x <= SCREEN_WIDTH + self.size and -self.size <= screen_y <= SCREEN_HEIGHT + self.size:
            pygame.draw.circle(screen, self.color, (int(screen_x), int(screen_y)), self.size)
            # Показать количество
            font = pygame.font.Font(None, 16)
            text = font.render(str(self.amount), True, WHITE)
            screen.blit(text, (screen_x - 5, screen_y - 5))

class ScrollQuest:
    """Свиток с квестом"""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.size = 12
        self.quest_type = random.choice(list(QUEST_TYPES.keys()))
        self.reward_tier = random.choice(['small', 'medium', 'large'])
        self.collected = False
        
        # Генерируем задание
        if self.quest_type == 'collect':
            self.target_resource = random.choice(list(RESOURCE_TYPES.keys()))
            self.target_amount = random.randint(10, 30)
            self.description = f"Собрать {self.target_amount} {RESOURCE_TYPES[self.target_resource]['name']}"
        elif self.quest_type == 'build':
            self.target_building = random.choice(['wall', 'tower', 'barracks'])
            self.target_amount = random.randint(1, 3)
            self.description = f"Построить {self.target_amount} {self.target_building}"
        elif self.quest_type == 'kill':
            self.target_amount = random.randint(3, 10)
            self.description = f"Убить {self.target_amount} врагов"
        else:  # explore
            self.description = "Исследовать подземелье"
    
    def draw(self, screen, camera):
        if self.collected:
            return
            
        screen_x = self.x - camera.x
        screen_y = self.y - camera.y
        if -self.size <= screen_x <= SCREEN_WIDTH + self.size and -self.size <= screen_y <= SCREEN_HEIGHT + self.size:
            # Свиток
            pygame.draw.rect(screen, (255, 255, 200), 
                           (int(screen_x - self.size), int(screen_y - self.size), 
                            self.size * 2, self.size * 2))
            pygame.draw.rect(screen, (200, 200, 150), 
                           (int(screen_x - self.size), int(screen_y - self.size), 
                            self.size * 2, self.size * 2), 2)
            
            # Символ квеста
            font = pygame.font.Font(None, 16)
            text = font.render("Q", True, (100, 50, 0))
            screen.blit(text, (screen_x - 5, screen_y - 8))

class Item:
    """Базовый класс для предметов"""
    def __init__(self, x, y, item_type, item_name, rarity="common"):
        self.x = x
        self.y = y
        self.size = 10
        self.item_type = item_type  # weapon, armor, accessory
        self.item_name = item_name
        self.rarity = rarity
        self.collected = False
        
        # Цвета по редкости
        self.rarity_colors = {
            'common': WHITE,
            'rare': BLUE,
            'epic': PURPLE,
            'legendary': GOLD
        }
    
    def draw(self, screen, camera):
        if self.collected:
            return
            
        screen_x = self.x - camera.x
        screen_y = self.y - camera.y
        if -self.size <= screen_x <= SCREEN_WIDTH + self.size and -self.size <= screen_y <= SCREEN_HEIGHT + self.size:
            color = self.rarity_colors[self.rarity]
            pygame.draw.circle(screen, color, (int(screen_x), int(screen_y)), self.size)
            pygame.draw.circle(screen, BLACK, (int(screen_x), int(screen_y)), self.size, 2)

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

class ResourcePile:
    """Куча ресурсов с возможностью найти тиммейта или оружие"""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.size = 25
        self.resources = []
        self.has_teammate = random.random() < TEAMMATE_SPAWN_CHANCE
        self.has_weapon = random.random() < 0.1  # 10% шанс найти оружие
        self.weapon_type = random.choice(list(WEAPON_STATS.keys())) if self.has_weapon else None
        self.has_scroll = random.random() < 0.05  # 5% шанс найти свиток с квестом
        self.scroll_quest = ScrollQuest(x, y) if self.has_scroll else None
        
        # Генерируем ресурсы в куче
        for _ in range(random.randint(3, 8)):
            self.resources.append({
                'type': random.choice(list(RESOURCE_TYPES.keys())),
                'amount': random.randint(2, 5)
            })
    
    def collect(self):
        """Собрать все ресурсы из кучи"""
        collected = self.resources.copy()
        teammate = self.has_teammate
        weapon = self.weapon_type if self.has_weapon else None
        scroll = self.scroll_quest if self.has_scroll else None
        
        self.resources.clear()
        self.has_teammate = False
        self.has_weapon = False
        self.weapon_type = None
        self.has_scroll = False
        if self.scroll_quest:
            self.scroll_quest.collected = True
        
        return collected, teammate, weapon, scroll
    
    def is_empty(self):
        return len(self.resources) == 0 and not self.has_teammate and not self.has_weapon and not self.has_scroll
    
    def draw(self, screen, camera):
        screen_x = self.x - camera.x
        screen_y = self.y - camera.y
        if -self.size <= screen_x <= SCREEN_WIDTH + self.size and -self.size <= screen_y <= SCREEN_HEIGHT + self.size:
            # Основная куча
            pygame.draw.circle(screen, BROWN, (int(screen_x), int(screen_y)), self.size)
            
            # Индикаторы содержимого
            if self.has_teammate:
                pygame.draw.circle(screen, GREEN, (int(screen_x - 10), int(screen_y - 10)), 5)
            if self.has_weapon:
                pygame.draw.circle(screen, RED, (int(screen_x + 10), int(screen_y - 10)), 5)
            if self.has_scroll:
                pygame.draw.circle(screen, YELLOW, (int(screen_x), int(screen_y + 15)), 5)

class Player:
    """Игрок"""
    def __init__(self, x, y, player_id=0):
        self.x = x
        self.y = y
        self.size = PLAYER_SIZE
        self.speed = PLAYER_SPEED
        self.player_id = player_id
        
        # Система уровней и опыта
        self.level = 1
        self.experience = 0
        self.experience_to_next_level = 100
        
        # Ресурсы
        self.resources = {res_type: 0 for res_type in RESOURCE_TYPES.keys()}
        
        # Базовые характеристики
        self.base_max_hp = PLAYER_MAX_HP
        self.base_speed = PLAYER_SPEED
        self.max_hp = self.base_max_hp
        self.hp = self.max_hp
        self.speed = self.base_speed
        self.attack_cooldown = 0
        
        # Статистика для достижений
        self.stats = {
            'resources_collected': 0,
            'buildings_built': 0,
            'enemies_killed': 0,
            'distance_traveled': 0,
            'items_crafted': 0,
            'trades_completed': 0,
            'worlds_explored': set(),
            'play_time': 0
        }
        
        # Достижения
        self.achievements = set()
        self.last_position = (x, y)
        
        # Экипировка
        self.equipped = {
            'weapon': None,
            'armor': None,
            'accessory1': None,
            'accessory2': None,
            'accessory3': None
        }
        
        # Инвентарь (слоты для предметов)
        self.base_inventory_size = INVENTORY_SLOTS
        self.inventory_slots = [None] * self.base_inventory_size
        
        # Квесты
        self.active_quests = []
        self.completed_quests = []
        self.quest_progress = {}
        
        # Бонусы от экипировки
        self.damage_bonus = 0
        self.defense_bonus = 0
        self.speed_bonus = 0
        self.health_bonus = 0
        self.drop_chance_bonus = 0
        self.inventory_bonus = 0
        self.mining_bonus = 0
        
        # Цвет игрока
        self.color = [BLUE, RED, GREEN, YELLOW, PURPLE][player_id % 5]
    
    def update(self, keys):
        # Сохраняем старую позицию для подсчета пройденного расстояния
        old_x, old_y = self.x, self.y
        
        # Движение
        try:
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.x -= self.speed
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.x += self.speed
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                self.y -= self.speed
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                self.y += self.speed
        except (KeyError, TypeError):
            # Для ИИ игроков, которые передают пустой словарь
            pass
        
        # Ограничения мира
        self.x = max(self.size, min(self.x, WORLD_WIDTH - self.size))
        self.y = max(self.size, min(self.y, WORLD_HEIGHT - self.size))
        
        # Подсчет пройденного расстояния
        distance = math.sqrt((self.x - old_x)**2 + (self.y - old_y)**2)
        self.stats['distance_traveled'] += distance
        
        # Опыт за передвижение (очень мало)
        if distance > 0:
            self.gain_experience(distance * 0.01)
        
        # Обновление кулдауна атаки
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        
        # Увеличиваем время игры
        self.stats['play_time'] += 1/60  # Предполагаем 60 FPS
    
    def collect_resource(self, resource):
        """Собрать ресурс"""
        distance = math.sqrt((self.x - resource.x)**2 + (self.y - resource.y)**2)
        if distance < self.size + resource.size:
            self.resources[resource.type] += resource.amount
            self.stats['resources_collected'] += resource.amount
            # Опыт передается через игровой цикл
            return True
        return False
    
    def gain_experience(self, amount, game=None):
        """Получить опыт"""
        self.experience += amount
        
        # Проверка повышения уровня
        while self.experience >= self.experience_to_next_level:
            self.level_up(game)
    
    def level_up(self, game=None):
        """Повышение уровня"""
        self.experience -= self.experience_to_next_level
        self.level += 1
        
        # Увеличиваем характеристики при повышении уровня
        self.base_max_hp += 10
        self.base_speed += 0.1
        
        # Увеличиваем требования к следующему уровню
        self.experience_to_next_level = int(self.experience_to_next_level * 1.2)
        
        # Восстанавливаем здоровье при повышении уровня
        old_max_hp = self.max_hp
        self.update_stats()
        self.hp += (self.max_hp - old_max_hp)  # Добавляем разницу в максимальном здоровье
        
        # Создаем эффект повышения уровня
        if game:
            game.add_level_up_effect(self.x, self.y)
        
        print(f"Игрок {self.player_id + 1} достиг {self.level} уровня!")
        return True
    
    def check_achievements(self):
        """Проверка достижений"""
        new_achievements = []
        
        # Достижения за сбор ресурсов
        if self.stats['resources_collected'] >= 100 and 'collector_novice' not in self.achievements:
            self.achievements.add('collector_novice')
            new_achievements.append('Новичок сборщик: Собрано 100 ресурсов')
        
        if self.stats['resources_collected'] >= 1000 and 'collector_expert' not in self.achievements:
            self.achievements.add('collector_expert')
            new_achievements.append('Эксперт сборщик: Собрано 1000 ресурсов')
        
        # Достижения за строительство
        if self.stats['buildings_built'] >= 10 and 'builder_novice' not in self.achievements:
            self.achievements.add('builder_novice')
            new_achievements.append('Начинающий строитель: Построено 10 зданий')
        
        if self.stats['buildings_built'] >= 50 and 'builder_expert' not in self.achievements:
            self.achievements.add('builder_expert')
            new_achievements.append('Мастер строитель: Построено 50 зданий')
        
        # Достижения за бой
        if self.stats['enemies_killed'] >= 10 and 'warrior_novice' not in self.achievements:
            self.achievements.add('warrior_novice')
            new_achievements.append('Начинающий воин: Убито 10 врагов')
        
        if self.stats['enemies_killed'] >= 100 and 'warrior_expert' not in self.achievements:
            self.achievements.add('warrior_expert')
            new_achievements.append('Мастер войны: Убито 100 врагов')
        
        # Достижения за уровень
        if self.level >= 5 and 'level_5' not in self.achievements:
            self.achievements.add('level_5')
            new_achievements.append('Опытный игрок: Достигнут 5 уровень')
        
        if self.level >= 10 and 'level_10' not in self.achievements:
            self.achievements.add('level_10')
            new_achievements.append('Ветеран: Достигнут 10 уровень')
        
        # Достижения за исследование
        if len(self.stats['worlds_explored']) >= 3 and 'explorer' not in self.achievements:
            self.achievements.add('explorer')
            new_achievements.append('Исследователь: Посещены все миры')
        
        return new_achievements
    
    def collect_pile(self, pile):
        """Собрать кучу ресурсов"""
        distance = math.sqrt((self.x - pile.x)**2 + (self.y - pile.y)**2)
        if distance < self.size + pile.size:
            return pile.collect()
        return None, False, None, None
    
    def can_craft(self, recipe):
        """Проверить, можно ли создать предмет"""
        for resource, amount in recipe.items():
            if self.resources[resource] < amount:
                return False
        return True
    
    def craft_item(self, recipe):
        """Создать предмет, потратив ресурсы"""
        if self.can_craft(recipe):
            for resource, amount in recipe.items():
                self.resources[resource] -= amount
            return True
        return False
    
    def attack(self, target):
        """Атаковать цель"""
        if self.attack_cooldown > 0:
            return False
        
        weapon = self.equipped.get('weapon')
        if not weapon:
            # Атака без оружия (кулаками)
            distance = math.sqrt((self.x - target.x)**2 + (self.y - target.y)**2)
            if distance <= 25:  # Ближний бой без оружия
                base_damage = 10
                total_damage = base_damage + self.damage_bonus
                killed = target.take_damage(total_damage)
                if killed:
                    self.stats['enemies_killed'] += 1
                    self.gain_experience(25)  # Опыт за убийство
                self.attack_cooldown = 45  # Больший кулдаун без оружия
                return True
            return False
        
        weapon_stats = WEAPON_STATS.get(weapon, {'damage': 10, 'range': 25})
        distance = math.sqrt((self.x - target.x)**2 + (self.y - target.y)**2)
        
        if distance <= weapon_stats['range']:
            base_damage = weapon_stats['damage']
            total_damage = base_damage + self.damage_bonus
            killed = target.take_damage(total_damage)
            if killed:
                self.stats['enemies_killed'] += 1
                self.gain_experience(25)  # Опыт за убийство
            self.attack_cooldown = 30  # Кулдаун атаки
            return True
        
        return False
    
    def take_damage(self, damage):
        """Получить урон"""
        armor = self.equipped['armor']
        base_defense = 0
        if armor and armor in ARMOR_STATS:
            base_defense = ARMOR_STATS[armor]['defense']
        
        total_defense = base_defense + self.defense_bonus
        actual_damage = max(1, damage - total_defense)
        self.hp -= actual_damage
        
        if self.hp <= 0:
            self.hp = 0
            return True  # Игрок погиб
        return False
    
    def heal(self, amount):
        """Восстановить здоровье"""
        self.hp = min(self.max_hp, self.hp + amount)
    
    def update_stats(self):
        """Обновить характеристики на основе экипировки"""
        # Сброс бонусов
        self.damage_bonus = 0
        self.defense_bonus = 0
        self.speed_bonus = 0
        self.health_bonus = 0
        self.drop_chance_bonus = 0
        self.inventory_bonus = 0
        self.mining_bonus = 0
        
        # Применение бонусов от экипировки
        for slot, item in self.equipped.items():
            if item:
                if slot == 'weapon' and item in WEAPON_STATS:
                    self.damage_bonus += WEAPON_STATS[item].get('damage', 0)
                elif slot == 'armor' and item in ARMOR_STATS:
                    self.defense_bonus += ARMOR_STATS[item].get('defense', 0)
                elif 'accessory' in slot and item in ACCESSORY_STATS:
                    stats = ACCESSORY_STATS[item]
                    self.damage_bonus += stats.get('damage_bonus', 0)
                    self.defense_bonus += stats.get('defense_bonus', 0)
                    self.speed_bonus += stats.get('speed_bonus', 0)
                    self.health_bonus += stats.get('health_bonus', 0)
                    self.drop_chance_bonus += stats.get('drop_chance_bonus', 0)
                    self.inventory_bonus += stats.get('inventory_bonus', 0)
                    self.mining_bonus += stats.get('mining_bonus', 0)
        
        # Обновление характеристик
        self.max_hp = self.base_max_hp + self.health_bonus
        self.speed = self.base_speed + self.speed_bonus
        
        # Если здоровье больше нового максимума, подрезаем
        if self.hp > self.max_hp:
            self.hp = self.max_hp
        
        # Обновление размера инвентаря
        new_inventory_size = self.base_inventory_size + self.inventory_bonus
        if len(self.inventory_slots) < new_inventory_size:
            # Расширяем инвентарь
            self.inventory_slots.extend([None] * (new_inventory_size - len(self.inventory_slots)))
    
    def equip_item(self, item_name, item_type):
        """Экипировать предмет"""
        if item_type == 'weapon':
            old_item = self.equipped['weapon']
            self.equipped['weapon'] = item_name
        elif item_type == 'armor':
            old_item = self.equipped['armor']
            self.equipped['armor'] = item_name
        elif item_type == 'accessory':
            # Найти свободный слот для аксессуара
            for slot in ['accessory1', 'accessory2', 'accessory3']:
                if self.equipped[slot] is None:
                    self.equipped[slot] = item_name
                    old_item = None
                    break
            else:
                # Заменяем первый аксессуар
                old_item = self.equipped['accessory1']
                self.equipped['accessory1'] = item_name
        
        self.update_stats()
        return old_item
    
    def unequip_item(self, slot):
        """Снять предмет"""
        old_item = self.equipped.get(slot)
        if old_item:
            self.equipped[slot] = None
            self.update_stats()
        return old_item
    
    def add_to_inventory(self, item_name, item_type):
        """Добавить предмет в инвентарь"""
        for i, slot in enumerate(self.inventory_slots):
            if slot is None:
                self.inventory_slots[i] = {'name': item_name, 'type': item_type}
                return True
        return False  # Инвентарь полон
    
    def remove_from_inventory(self, slot_index):
        """Убрать предмет из инвентаря"""
        if 0 <= slot_index < len(self.inventory_slots):
            item = self.inventory_slots[slot_index]
            self.inventory_slots[slot_index] = None
            return item
        return None
    
    def draw(self, screen, camera):
        screen_x = self.x - camera.x
        screen_y = self.y - camera.y
        
        # Основной круг игрока
        pygame.draw.circle(screen, self.color, (int(screen_x), int(screen_y)), self.size)
        
        # Полоска здоровья
        bar_width = self.size * 2
        bar_height = 4
        bar_x = screen_x - bar_width // 2
        bar_y = screen_y - self.size - 10
        
        # Фон полоски
        pygame.draw.rect(screen, RED, (bar_x, bar_y, bar_width, bar_height))
        # Текущее здоровье
        hp_width = int((self.hp / self.max_hp) * bar_width)
        pygame.draw.rect(screen, GREEN, (bar_x, bar_y, hp_width, bar_height))
        
        # Индикатор оружия
        weapon = self.equipped['weapon']
        if weapon:
            weapon_color = {'sword': GRAY, 'bow': BROWN, 'axe': ORANGE, 'staff': PURPLE}.get(weapon, WHITE)
            pygame.draw.circle(screen, weapon_color, (int(screen_x + self.size//2), int(screen_y - self.size//2)), 3)

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

class Building:
    """Базовый класс для построек"""
    def __init__(self, x, y, width, height, color, owner_id=0, building_type="building"):
        # Привязка к сетке
        self.grid_x = x // GRID_SIZE
        self.grid_y = y // GRID_SIZE
        self.x = self.grid_x * GRID_SIZE
        self.y = self.grid_y * GRID_SIZE
        
        self.width = width
        self.height = height
        self.color = color
        self.owner_id = owner_id
        self.building_type = building_type
        self.hp = 100
        self.max_hp = 100
        
        # Размер в клетках сетки
        self.grid_width = width // GRID_SIZE
        self.grid_height = height // GRID_SIZE
    
    def get_occupied_cells(self):
        """Получить список занимаемых клеток сетки"""
        cells = []
        for gx in range(self.grid_x, self.grid_x + self.grid_width):
            for gy in range(self.grid_y, self.grid_y + self.grid_height):
                cells.append((gx, gy))
        return cells
    
    def take_damage(self, damage):
        """Получить урон"""
        self.hp -= damage
        return self.hp <= 0
    
    def draw(self, screen, camera):
        screen_x = self.x - camera.x
        screen_y = self.y - camera.y
        
        # Основная постройка
        pygame.draw.rect(screen, self.color, (screen_x, screen_y, self.width, self.height))
        
        # Полоска здоровья
        if self.hp < self.max_hp:
            bar_width = self.width
            bar_height = 4
            bar_x = screen_x
            bar_y = screen_y - 8
            
            pygame.draw.rect(screen, RED, (bar_x, bar_y, bar_width, bar_height))
            hp_width = int((self.hp / self.max_hp) * bar_width)
            pygame.draw.rect(screen, GREEN, (bar_x, bar_y, hp_width, bar_height))

class Wall(Building):
    """Стена"""
    def __init__(self, x, y, owner_id=0):
        super().__init__(x, y, GRID_SIZE, GRID_SIZE, BROWN, owner_id, "wall")
        self.hp = 150
        self.max_hp = 150

class Tower(Building):
    """Башня с автоатакой"""
    def __init__(self, x, y, owner_id=0):
        super().__init__(x, y, GRID_SIZE * 2, GRID_SIZE * 2, GRAY, owner_id, "tower")
        self.attack_timer = 0
        self.range = TOWER_RANGE
        self.hp = 200
        self.max_hp = 200
    
    def update(self, enemies, current_world):
        """Автоматическая атака врагов"""
        if current_world != WORLD_BASE:
            return
        
        self.attack_timer += 1
        
        if self.attack_timer >= TOWER_ATTACK_SPEED:
            self.attack_timer = 0
            
            # Найти врагов в радиусе
            center_x = self.x + self.width // 2
            center_y = self.y + self.height // 2
            
            for enemy in enemies:
                if hasattr(enemy, 'owner_id') and enemy.owner_id != self.owner_id:
                    distance = math.sqrt((center_x - enemy.x)**2 + (center_y - enemy.y)**2)
                    if distance <= self.range:
                        enemy.take_damage(TOWER_DAMAGE)
                        break  # Атакуем только одну цель за раз
                elif hasattr(enemy, 'player_id') and enemy.player_id != self.owner_id:
                    distance = math.sqrt((center_x - enemy.x)**2 + (center_y - enemy.y)**2)
                    if distance <= self.range:
                        enemy.take_damage(TOWER_DAMAGE)
                        break
    
    def draw(self, screen, camera):
        super().draw(screen, camera)
        # Показать радиус действия
        center_x = self.x + self.width // 2 - camera.x
        center_y = self.y + self.height // 2 - camera.y
        pygame.draw.circle(screen, (100, 100, 100), (int(center_x), int(center_y)), self.range, 1)

class Barracks(Building):
    """Казармы для создания тиммейтов"""
    def __init__(self, x, y, owner_id=0):
        super().__init__(x, y, GRID_SIZE * 3, GRID_SIZE * 2, DARK_GREEN, owner_id, "barracks")
        self.spawn_timer = 0
        self.hp = 180
        self.max_hp = 180
    
    def update(self):
        """Периодическое создание тиммейтов"""
        self.spawn_timer += 1
        
        if self.spawn_timer >= 600:  # Каждые 10 секунд
            self.spawn_timer = 0
            return True  # Сигнал для создания тиммейта
        return False

class Workshop(Building):
    """Мастерская для создания оружия и брони"""
    def __init__(self, x, y, owner_id=0):
        super().__init__(x, y, GRID_SIZE * 3, GRID_SIZE * 3, ORANGE, owner_id, "workshop")
        self.hp = 120
        self.max_hp = 120
        self.craft_timer = 0
    
    def can_use(self, player):
        """Проверить, может ли игрок использовать мастерскую"""
        distance = math.sqrt((player.x - (self.x + self.width//2))**2 + 
                           (player.y - (self.y + self.height//2))**2)
        return distance < 40
    
    def update(self):
        """Обновление мастерской (только анимация)"""
        self.craft_timer += 1
        # Мастерская больше не создает предметы автоматически
        # Крафт происходит только через интерфейс при нажатии E
    
    def draw(self, screen, camera):
        super().draw(screen, camera)
        # Символ мастерской
        screen_x = self.x - camera.x + self.width // 2
        screen_y = self.y - camera.y + self.height // 2
        
        font = pygame.font.Font(None, 20)
        text = font.render("⚒", True, WHITE)
        text_rect = text.get_rect(center=(screen_x, screen_y))
        screen.blit(text, text_rect)
    
    def draw_interaction_hint(self, screen, camera, player):
        """Отрисовка подсказки взаимодействия"""
        if self.can_use(player):
            screen_x = self.x - camera.x + self.width // 2
            screen_y = self.y - camera.y - 20
            
            font = pygame.font.Font(None, 16)
            text = font.render("E - Мастерская", True, (255, 255, 0))
            text_rect = text.get_rect(center=(screen_x, screen_y))
            
            # Фон для текста
            bg_rect = text_rect.inflate(10, 4)
            pygame.draw.rect(screen, (0, 0, 0, 180), bg_rect)
            screen.blit(text, text_rect)

class Portal(Building):
    """Портал между мирами"""
    def __init__(self, x, y, owner_id=0):
        super().__init__(x, y, GRID_SIZE * 2, GRID_SIZE * 2, PURPLE, owner_id, "portal")
        self.hp = 300
        self.max_hp = 300
        self.animation_timer = 0
    
    def update(self):
        self.animation_timer += 1
    
    def can_use(self, player):
        """Проверить, может ли игрок использовать портал"""
        distance = math.sqrt((player.x - (self.x + self.width//2))**2 + 
                           (player.y - (self.y + self.height//2))**2)
        return distance < 40
    
    def draw(self, screen, camera):
        super().draw(screen, camera)
        # Анимация портала
        screen_x = self.x - camera.x + self.width // 2
        screen_y = self.y - camera.y + self.height // 2
        
        radius = 20 + int(5 * math.sin(self.animation_timer * 0.1))
        pygame.draw.circle(screen, CYAN, (int(screen_x), int(screen_y)), radius, 3)

class DungeonPortal(Building):
    """Портал в подземелье"""
    def __init__(self, x, y, owner_id=0):
        super().__init__(x, y, GRID_SIZE * 3, GRID_SIZE * 3, (100, 0, 100), owner_id, "dungeon_portal")
        self.hp = 500
        self.max_hp = 500
        self.animation_timer = 0
    
    def update(self):
        self.animation_timer += 1
    
    def can_use(self, player):
        """Проверить, может ли игрок использовать портал"""
        distance = math.sqrt((player.x - (self.x + self.width//2))**2 + 
                           (player.y - (self.y + self.height//2))**2)
        return distance < 50
    
    def draw(self, screen, camera):
        super().draw(screen, camera)
        # Анимация портала в подземелье
        screen_x = self.x - camera.x + self.width // 2
        screen_y = self.y - camera.y + self.height // 2
        
        radius = 25 + int(8 * math.sin(self.animation_timer * 0.08))
        pygame.draw.circle(screen, (150, 0, 150), (int(screen_x), int(screen_y)), radius, 4)
        pygame.draw.circle(screen, (200, 0, 200), (int(screen_x), int(screen_y)), radius - 8, 2)

class Shop(Building):
    """Магазин для торговли"""
    def __init__(self, x, y, owner_id=0):
        super().__init__(x, y, GRID_SIZE * 4, GRID_SIZE * 3, (0, 150, 150), owner_id, "shop")
        self.hp = 150
        self.max_hp = 150
        
        # Товары в магазине
        self.shop_items = {
            'weapons': list(WEAPON_STATS.keys()),
            'armor': list(ARMOR_STATS.keys()),
            'accessories': list(ACCESSORY_STATS.keys())
        }
    
    def can_use(self, player):
        """Проверить, может ли игрок использовать магазин"""
        distance = math.sqrt((player.x - (self.x + self.width//2))**2 + 
                           (player.y - (self.y + self.height//2))**2)
        return distance < 40
    
    def buy_item(self, player, item_type, item_name):
        """Купить предмет"""
        if item_type == 'weapon' and item_name in WEAPON_STATS:
            cost = WEAPON_STATS[item_name]['cost']
        elif item_type == 'armor' and item_name in ARMOR_STATS:
            cost = ARMOR_STATS[item_name]['cost']
        elif item_type == 'accessory' and item_name in ACCESSORY_STATS:
            cost = ACCESSORY_STATS[item_name]['cost']
        else:
            return False
        
        if player.can_craft(cost):
            player.craft_item(cost)
            return player.add_to_inventory(item_name, item_type)
        return False
    
    def draw(self, screen, camera):
        super().draw(screen, camera)
        # Символ магазина
        screen_x = self.x - camera.x + self.width // 2
        screen_y = self.y - camera.y + self.height // 2
        
        font = pygame.font.Font(None, 24)
        text = font.render("$", True, GOLD)
        text_rect = text.get_rect(center=(screen_x, screen_y))
        screen.blit(text, text_rect)
    
    def draw_interaction_hint(self, screen, camera, player):
        """Отрисовка подсказки взаимодействия"""
        if self.can_use(player):
            screen_x = self.x - camera.x + self.width // 2
            screen_y = self.y - camera.y - 20
            
            font = pygame.font.Font(None, 16)
            text = font.render("E - Магазин", True, (255, 255, 0))
            text_rect = text.get_rect(center=(screen_x, screen_y))
            
            # Фон для текста
            bg_rect = text_rect.inflate(10, 4)
            pygame.draw.rect(screen, (0, 0, 0, 180), bg_rect)
            screen.blit(text, text_rect)

class Storage(Building):
    """Хранилище предметов"""
    def __init__(self, x, y, owner_id=0):
        super().__init__(x, y, GRID_SIZE * 3, GRID_SIZE * 2, (150, 100, 50), owner_id, "storage")
        self.hp = 200
        self.max_hp = 200
        self.stored_items = {'weapons': [], 'armor': [], 'accessories': []}
    
    def can_use(self, player):
        """Проверить, может ли игрок использовать хранилище"""
        distance = math.sqrt((player.x - (self.x + self.width//2))**2 + 
                           (player.y - (self.y + self.height//2))**2)
        return distance < 40
    
    def store_item(self, item_name, item_type):
        """Сохранить предмет в хранилище"""
        if item_type not in self.stored_items:
            self.stored_items[item_type] = []
        
        self.stored_items[item_type].append(item_name)
        return True
    
    def retrieve_item(self, item_type, item_name):
        """Взять предмет из хранилища"""
        if item_type in self.stored_items and item_name in self.stored_items[item_type]:
            self.stored_items[item_type].remove(item_name)
            return True
        return False
    
    def draw(self, screen, camera):
        super().draw(screen, camera)
        # Символ хранилища
        screen_x = self.x - camera.x + self.width // 2
        screen_y = self.y - camera.y + self.height // 2
        
        font = pygame.font.Font(None, 20)
        text = font.render("[]", True, WHITE)
        text_rect = text.get_rect(center=(screen_x, screen_y))
        screen.blit(text, text_rect)

class OllamaAI:
    """ИИ игрок на основе Ollama"""
    def __init__(self, player_id, model_name="qwen2.5-coder:1.5b"):
        self.player_id = player_id
        self.model_name = model_name
        self.last_decision_time = 0
        self.decision_cooldown = 2.0  # Секунды между решениями
        self.current_strategy = "explore"  # explore, build, attack
        self.target_position = None
        self.ollama_available = self.check_ollama()
        
    def check_ollama(self):
        """Проверить доступность Ollama и выбрать лучшую модель"""
        try:
            models_response = ollama.list()
            print(f"Ollama response: {models_response}")  # Отладка
            
            if hasattr(models_response, 'models'):
                available_models = [model.model for model in models_response.models]
            elif 'models' in models_response:
                available_models = [model['name'] for model in models_response['models']]
            else:
                available_models = []
            
            print(f"Доступные модели: {available_models}")  # Отладка
            
            # Приоритет моделей для игрового ИИ (от лучшей к худшей)
            preferred_models = [
                "qwen2.5-coder:1.5b",
                "gemma2:2b", 
                "gemma2:9b",
                "qwen2.5-coder:7b",
                "llama3.2:1b",
                "llama3.2:3b"
            ]
            
            # Выбираем первую доступную модель из списка приоритетов
            for model in preferred_models:
                if model in available_models:
                    self.model_name = model
                    print(f"ИИ игрок {self.player_id} использует модель: {model}")
                    return True
            
            # Если ни одна из предпочтительных моделей не найдена, используем первую доступную
            if available_models:
                self.model_name = available_models[0]
                print(f"ИИ игрок {self.player_id} использует модель: {self.model_name}")
                return True
            
            print(f"ИИ игрок {self.player_id}: Модели Ollama не найдены")
            return False
            
        except Exception as e:
            print(f"ИИ игрок {self.player_id}: Ollama недоступна - {e}")
            return False
    
    def get_game_state_description(self, game, player):
        """Получить описание текущего состояния игры"""
        # Проверяем наличие атрибута equipped (для совместимости со старыми сохранениями)
        if not hasattr(player, 'equipped'):
            player.equipped = {
                'weapon': None,
                'armor': None,
                'accessory1': None,
                'accessory2': None,
                'accessory3': None
            }
        
        state = {
            "world": "resource" if game.current_world == WORLD_RESOURCE else "base",
            "hp": f"{player.hp}/{player.max_hp}",
            "resources": dict(player.resources),
            "weapon": player.equipped['weapon'] or "none",
            "armor": player.equipped['armor'] or "none",
            "teammates": len(game.teammates[self.player_id]),
            "buildings": len(game.buildings[self.player_id]),
            "position": {"x": int(player.x), "y": int(player.y)}
        }
        
        # Найти ближайшие объекты
        nearby_resources = []
        nearby_enemies = []
        
        if game.current_world == WORLD_RESOURCE:
            for resource in game.resources[:5]:  # Только первые 5
                distance = math.sqrt((player.x - resource.x)**2 + (player.y - resource.y)**2)
                if distance < 200:
                    nearby_resources.append({
                        "type": resource.type,
                        "distance": int(distance),
                        "amount": resource.amount
                    })
        else:
            for i, enemy in enumerate(game.players):
                if i != self.player_id:
                    distance = math.sqrt((player.x - enemy.x)**2 + (player.y - enemy.y)**2)
                    if distance < 300:
                        nearby_enemies.append({
                            "hp": f"{enemy.hp}/{enemy.max_hp}",
                            "distance": int(distance),
                            "weapon": enemy.weapon or "none"
                        })
        
        state["nearby_resources"] = nearby_resources
        state["nearby_enemies"] = nearby_enemies
        
        return state
    
    def make_decision(self, game, player):
        """Принять решение на основе ИИ"""
        current_time = time.time()
        if current_time - self.last_decision_time < self.decision_cooldown:
            return self.execute_current_strategy(game, player)
        
        self.last_decision_time = current_time
        
        if not self.ollama_available:
            return self.fallback_ai(game, player)
        
        try:
            state = self.get_game_state_description(game, player)
            
            prompt = f"""You are an AI player in a strategy game. Analyze the situation and choose the best action.

GAME STATE:
World: {state['world']} (resource=safe, base=pvp)
Health: {state['hp']}
Resources: {state['resources']}
Equipment: weapon={state['weapon']}, armor={state['armor']}
Army: teammates={state['teammates']}, buildings={state['buildings']}
Nearby: resources={len(state['nearby_resources'])}, enemies={len(state['nearby_enemies'])}

DECISION LOGIC:
- If health < 30 → retreat
- If in resource world + low resources → explore  
- If in base world + have resources → build
- If enemy nearby + have weapon → attack
- If need to change worlds → switch_world

ACTIONS: explore, build, attack, switch_world, retreat

Choose ONE action:"""
            
            response = ollama.generate(
                model=self.model_name,
                prompt=prompt,
                options={
                    "temperature": 0.3,  # Меньше случайности для более предсказуемого ИИ
                    "num_predict": 5,    # Короткий ответ
                    "top_p": 0.9,        # Фокус на наиболее вероятных вариантах
                    "repeat_penalty": 1.1 # Избегаем повторений
                }
            )
            
            decision = response['response'].strip().lower()
            
            # Умная обработка ответа - ищем ключевые слова
            valid_actions = ['explore', 'build', 'attack', 'switch_world', 'retreat']
            
            # Прямое совпадение
            if decision in valid_actions:
                self.current_strategy = decision
            else:
                # Поиск ключевых слов в ответе
                found_action = None
                for action in valid_actions:
                    if action in decision:
                        found_action = action
                        break
                
                if found_action:
                    self.current_strategy = found_action
                else:
                    # Интеллектуальная интерпретация
                    if any(word in decision for word in ['collect', 'gather', 'resource', 'mine']):
                        self.current_strategy = "explore"
                    elif any(word in decision for word in ['construct', 'create', 'make', 'craft']):
                        self.current_strategy = "build"
                    elif any(word in decision for word in ['fight', 'combat', 'battle', 'kill']):
                        self.current_strategy = "attack"
                    elif any(word in decision for word in ['run', 'escape', 'flee', 'hide']):
                        self.current_strategy = "retreat"
                    elif any(word in decision for word in ['switch', 'change', 'move', 'portal']):
                        self.current_strategy = "switch_world"
                    else:
                        self.current_strategy = "explore"  # По умолчанию
                
                print(f"ИИ {self.player_id}: '{decision}' → {self.current_strategy}")
                
        except Exception as e:
            print(f"Ошибка ИИ: {e}")
            return self.fallback_ai(game, player)
        
        return self.execute_current_strategy(game, player)
    
    def fallback_ai(self, game, player):
        """Простой ИИ без Ollama"""
        # Простая логика как резерв
        if player.hp < 30:
            self.current_strategy = "retreat"
        elif game.current_world == WORLD_RESOURCE and sum(player.resources.values()) < 20:
            self.current_strategy = "explore"
        elif game.current_world == WORLD_BASE and sum(player.resources.values()) > 10:
            self.current_strategy = "build"
        else:
            self.current_strategy = "explore"
        
        return self.execute_current_strategy(game, player)
    
    def execute_current_strategy(self, game, player):
        """Выполнить текущую стратегию"""
        if self.current_strategy == "explore":
            return self.explore_strategy(game, player)
        elif self.current_strategy == "build":
            return self.build_strategy(game, player)
        elif self.current_strategy == "attack":
            return self.attack_strategy(game, player)
        elif self.current_strategy == "switch_world":
            return self.switch_world_strategy(game, player)
        elif self.current_strategy == "retreat":
            return self.retreat_strategy(game, player)
        
        return {"action": "wait"}
    
    def explore_strategy(self, game, player):
        """Стратегия исследования"""
        if game.current_world == WORLD_BASE:
            # Переключиться в мир ресурсов
            for building in game.buildings[self.player_id]:
                if isinstance(building, Portal) and building.can_use(player):
                    return {"action": "use_portal"}
        
        # Найти ближайший ресурс
        closest_resource = None
        closest_distance = float('inf')
        
        targets = game.resources + game.resource_piles
        for target in targets:
            distance = math.sqrt((player.x - target.x)**2 + (player.y - target.y)**2)
            if distance < closest_distance:
                closest_distance = distance
                closest_resource = target
        
        if closest_resource:
            return {
                "action": "move_to",
                "target": {"x": closest_resource.x, "y": closest_resource.y}
            }
        
        return {"action": "wander"}
    
    def build_strategy(self, game, player):
        """Стратегия строительства"""
        if game.current_world == WORLD_RESOURCE:
            # Переключиться в мир базы
            distance = math.sqrt((player.x - RESOURCE_SPAWN_CENTER_X)**2 + (player.y - RESOURCE_SPAWN_CENTER_Y)**2)
            if distance < 60:
                return {"action": "use_portal"}
            else:
                return {
                    "action": "move_to",
                    "target": {"x": RESOURCE_SPAWN_CENTER_X, "y": RESOURCE_SPAWN_CENTER_Y}
                }
        
        # Выбрать что строить
        building_priority = ["workshop", "barracks", "tower", "wall", "portal"]
        
        for building_type in building_priority:
            cost = BUILDING_COSTS.get(building_type, {})
            if player.can_craft(cost):
                base = game.player_bases[self.player_id]
                return {
                    "action": "build",
                    "building_type": building_type,
                    "position": {
                        "x": random.randint(base['x'] + 20, base['x'] + base['width'] - 50),
                        "y": random.randint(base['y'] + 20, base['y'] + base['height'] - 50)
                    }
                }
        
        return {"action": "wait"}
    
    def attack_strategy(self, game, player):
        """Стратегия атаки"""
        if not player.equipped['weapon']:
            return self.build_strategy(game, player)
        
        # Найти ближайшего врага
        closest_enemy = None
        closest_distance = float('inf')
        
        for i, enemy in enumerate(game.players):
            if i != self.player_id:
                distance = math.sqrt((player.x - enemy.x)**2 + (player.y - enemy.y)**2)
                if distance < closest_distance:
                    closest_distance = distance
                    closest_enemy = enemy
        
        if closest_enemy and closest_distance < 100:
            return {
                "action": "attack",
                "target": {"x": closest_enemy.x, "y": closest_enemy.y}
            }
        elif closest_enemy:
            return {
                "action": "move_to",
                "target": {"x": closest_enemy.x, "y": closest_enemy.y}
            }
        
        return self.explore_strategy(game, player)
    
    def switch_world_strategy(self, game, player):
        """Стратегия смены мира"""
        if game.current_world == WORLD_RESOURCE:
            distance = math.sqrt((player.x - RESOURCE_SPAWN_CENTER_X)**2 + (player.y - RESOURCE_SPAWN_CENTER_Y)**2)
            if distance < 60:
                return {"action": "use_portal"}
            else:
                return {
                    "action": "move_to",
                    "target": {"x": RESOURCE_SPAWN_CENTER_X, "y": RESOURCE_SPAWN_CENTER_Y}
                }
        else:
            for building in game.buildings[self.player_id]:
                if isinstance(building, Portal) and building.can_use(player):
                    return {"action": "use_portal"}
        
        return {"action": "wait"}
    
    def retreat_strategy(self, game, player):
        """Стратегия отступления"""
        base = game.player_bases[self.player_id]
        base_center_x = base['x'] + base['width'] // 2
        base_center_y = base['y'] + base['height'] // 2
        
        return {
            "action": "move_to",
            "target": {"x": base_center_x, "y": base_center_y}
        }

class Game:
    """Основной класс игры"""
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Многомировая игра: Ресурсы и PvP")
        self.clock = pygame.time.Clock()
        
        # Состояние игры
        self.game_state = GameState.MENU
        self.num_ai_players = 1
        self.selected_menu_item = 0
        
        # Игровые объекты
        self.camera = Camera()
        self.players = []
        self.ai_players = []
        self.current_player = 0
        
        # Миры
        self.current_world = WORLD_RESOURCE
        
        # Объекты мира ресурсов
        self.resources = []
        self.resource_piles = []
        
        # Объекты мира базы
        self.teammates = {i: [] for i in range(len(self.players))}
        self.buildings = {i: [] for i in range(len(self.players))}
        
        # Базы игроков
        self.player_bases = {
            0: {'x': 100, 'y': 100, 'width': 400, 'height': 300},
            1: {'x': WORLD_WIDTH - 500, 'y': WORLD_HEIGHT - 400, 'width': 400, 'height': 300}
        }
        
        # Режимы игры
        self.game_mode = "explore"  # "explore", "build", "combat"
        self.selected_building = "wall"
        self.selected_weapon = "sword"
        self.selected_armor = "leather"
        self.show_inventory = False
        self.show_left_panel = True  # Показывать ли левую панель
        
        # Интерфейсы зданий
        self.show_shop_interface = False
        self.selected_shop = None
        self.show_storage_interface = False
        self.selected_storage = None
        
        # Шрифт для UI
        self.font = pygame.font.Font(None, 28)
        self.small_font = pygame.font.Font(None, 20)
        
        # База данных для сохранений
        self.database = GameDatabase()
        
        # Диалоги
        self.current_dialog = None
        self.unsaved_changes = False
        self.last_autosave_time = 0
        self.autosave_interval = 300000  # 5 минут в миллисекундах
        
        # Интерфейсы зданий
        self.current_building_interface = None
        
        # Визуальные эффекты
        self.damage_indicators = []
        self.level_up_effects = []
        self.achievement_notifications = []
        
        # Инициализируем пустые структуры данных
        self.resources = []
        self.resource_piles = []
        self.scroll_quests = []
        self.items = []
        self.enemies = []
        self.dungeon_items = []
        self.teammates = {}
        self.buildings = {}
        self.player_bases = {}
        
        # Сетка строительства
        self.building_grids = {}  # Сетки занятых клеток для каждого игрока
        self.show_grid = False
        self.preview_building = None
        self.preview_position = None
    
    def spawn_initial_resources(self):
        """Создать начальные ресурсы"""
        # Только обычные ресурсы в мире ресурсов
        normal_resources = ['wood', 'stone', 'iron', 'gold', 'crystal']
        for _ in range(INITIAL_RESOURCES):
            x = random.randint(RESOURCE_SIZE, WORLD_WIDTH - RESOURCE_SIZE)
            y = random.randint(RESOURCE_SIZE, WORLD_HEIGHT - RESOURCE_SIZE)
            resource_type = random.choice(normal_resources)
            self.resources.append(Resource(x, y, resource_type))
    
    def spawn_initial_piles(self):
        """Создать начальные кучи ресурсов"""
        for _ in range(20):
            x = random.randint(50, WORLD_WIDTH - 50)
            y = random.randint(50, WORLD_HEIGHT - 50)
            self.resource_piles.append(ResourcePile(x, y))
    
    def create_initial_portals(self):
        """Создать начальные порталы"""
        # Порталы в базах игроков
        for player_id, base in self.player_bases.items():
            portal = Portal(base['x'] + base['width'] - 60, base['y'] + 10, player_id)
            self.buildings[player_id].append(portal)
            self.update_building_grid(player_id)
    
    def init_building_grids(self):
        """Инициализировать сетки строительства"""
        for player_id in range(len(self.players)):
            self.building_grids[player_id] = set()
    
    def update_building_grid(self, player_id):
        """Обновить сетку занятых клеток для игрока"""
        self.building_grids[player_id] = set()
        for building in self.buildings[player_id]:
            occupied_cells = building.get_occupied_cells()
            self.building_grids[player_id].update(occupied_cells)
    
    def can_place_building(self, player_id, building_type, grid_x, grid_y):
        """Проверить, можно ли разместить постройку"""
        base = self.player_bases[player_id]
        building_size = BUILDING_SIZES[building_type]
        
        # Проверка границ базы
        base_grid_x1 = base['x'] // GRID_SIZE
        base_grid_y1 = base['y'] // GRID_SIZE
        base_grid_x2 = (base['x'] + base['width']) // GRID_SIZE
        base_grid_y2 = (base['y'] + base['height']) // GRID_SIZE
        
        if (grid_x < base_grid_x1 or grid_y < base_grid_y1 or 
            grid_x + building_size['width'] > base_grid_x2 or 
            grid_y + building_size['height'] > base_grid_y2):
            return False
        
        # Проверка пересечения с существующими постройками
        occupied_grid = self.building_grids[player_id]
        for gx in range(grid_x, grid_x + building_size['width']):
            for gy in range(grid_y, grid_y + building_size['height']):
                if (gx, gy) in occupied_grid:
                    return False
        
        return True
    
    def expand_base(self, player_id, direction):
        """Расширить базу игрока"""
        player = self.players[player_id]
        expansion_cost = BUILDING_COSTS['base_expansion']
        
        if not player.can_craft(expansion_cost):
            return False
        
        base = self.player_bases[player_id]
        expansion_size = GRID_SIZE * 5  # Расширяем на 5 клеток
        
        if direction == 'right':
            base['width'] += expansion_size
        elif direction == 'down':
            base['height'] += expansion_size
        elif direction == 'left':
            base['x'] -= expansion_size
            base['width'] += expansion_size
        elif direction == 'up':
            base['y'] -= expansion_size
            base['height'] += expansion_size
        
        player.craft_item(expansion_cost)
        return True
    
    def switch_world(self, target_world):
        """Переключение между мирами"""
        player = self.players[self.current_player]
        
        if target_world == WORLD_BASE:
            self.current_world = WORLD_BASE
            # Перемещаем игрока на базу
            base = self.player_bases[self.current_player]
            player.x = base['x'] + 50
            player.y = base['y'] + 50
        elif target_world == WORLD_RESOURCE:
            self.current_world = WORLD_RESOURCE
            # Перемещаем игрока в центр мира ресурсов
            player.x = RESOURCE_SPAWN_CENTER_X
            player.y = RESOURCE_SPAWN_CENTER_Y
        elif target_world == WORLD_DUNGEON:
            self.current_world = WORLD_DUNGEON
            # Перемещаем игрока в начало подземелья
            player.x = 200
            player.y = 200
            # Спавним врагов если их нет
            if not self.enemies:
                self.spawn_dungeon_enemies()
    
    def spawn_resource_wave(self):
        """Создать волну ресурсов в центре"""
        if self.current_world != WORLD_RESOURCE:
            return
        
        if random.random() < RESOURCE_SPAWN_RATE:
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(0, RESOURCE_SPAWN_RADIUS)
            x = RESOURCE_SPAWN_CENTER_X + distance * math.cos(angle)
            y = RESOURCE_SPAWN_CENTER_Y + distance * math.sin(angle)
            
            x = max(RESOURCE_SIZE, min(x, WORLD_WIDTH - RESOURCE_SIZE))
            y = max(RESOURCE_SIZE, min(y, WORLD_HEIGHT - RESOURCE_SIZE))
            
            # ТОЛЬКО обычные ресурсы в мире ресурсов (исключаем уникальные)
            normal_resources = ['wood', 'stone', 'iron', 'gold', 'crystal']
            resource_type = random.choice(normal_resources)
            self.resources.append(Resource(x, y, resource_type))
    
    def handle_resource_collection(self):
        """Обработка сбора ресурсов"""
        if self.current_world != WORLD_RESOURCE:
            return
        
        player = self.players[self.current_player]
        
        # Игрок собирает обычные ресурсы
        for resource in self.resources[:]:
            if player.collect_resource(resource):
                # Добавляем опыт за сбор ресурса
                player.gain_experience(resource.amount * 2, self)
                print(f"Собран ресурс: {RESOURCE_TYPES[resource.type]['name']} x{resource.amount}")
                self.resources.remove(resource)
        
        # Игрок собирает кучи ресурсов
        for pile in self.resource_piles[:]:
            collected_resources, found_teammate, found_weapon, found_scroll = player.collect_pile(pile)
            
            if collected_resources:
                # Добавляем ресурсы
                for res_data in collected_resources:
                    player.resources[res_data['type']] += res_data['amount']
                
                # Добавляем тиммейта
                if found_teammate:
                    teammate = Teammate(pile.x, pile.y, self.current_player)
                    self.teammates[self.current_player].append(teammate)
                
                # Добавляем оружие
                if found_weapon and not player.equipped['weapon']:
                    player.add_to_inventory(found_weapon, 'weapon')
                
                # Добавляем квест
                if found_scroll:
                    player.active_quests.append(found_scroll)
                    print(f"Найден квест: {found_scroll.description}")
                
                # Удаляем пустую кучу
                if pile.is_empty():
                    self.resource_piles.remove(pile)
        
        # Тиммейты собирают только обычные ресурсы
        normal_resources = ['wood', 'stone', 'iron', 'gold', 'crystal']
        for teammate in self.teammates[self.current_player]:
            for resource in self.resources[:]:
                if resource.type in normal_resources and teammate.collect_resource(resource):
                    player.resources[resource.type] += resource.amount
                    self.resources.remove(resource)
                    break
    
    def handle_dungeon_collection(self):
        """Обработка сбора предметов в подземелье"""
        if self.current_world != WORLD_DUNGEON:
            return
        
        player = self.players[self.current_player]
        
        # Сбор предметов в подземелье
        for item in self.dungeon_items[:]:
            if not item.collected:
                distance = math.sqrt((player.x - item.x)**2 + (player.y - item.y)**2)
                if distance < player.size + item.size:
                    if isinstance(item, Resource):
                        # Ресурс
                        bonus_amount = int(item.amount * (1 + player.mining_bonus))
                        player.resources[item.type] += bonus_amount
                        item.collected = True
                        print(f"Собран ресурс: {RESOURCE_TYPES[item.type]['name']} x{bonus_amount}")
                    elif isinstance(item, Item):
                        # Предмет
                        if player.add_to_inventory(item.item_name, item.item_type):
                            item.collected = True
                            print(f"Найден предмет: {item.item_name} ({item.rarity})")
                        else:
                            print("Инвентарь полон!")
        
        # Удаляем собранные предметы
        self.dungeon_items = [item for item in self.dungeon_items if not item.collected]
    
    def spawn_enemy_loot(self, x, y):
        """Создать лут с убитого врага"""
        loot_type = random.choice(['resource', 'item'])
        
        if loot_type == 'resource':
            # Уникальный ресурс подземелья
            dungeon_resources = ['shadow_essence', 'demon_blood', 'soul_gem', 'void_crystal']
            resource_type = random.choice(dungeon_resources)
            resource = Resource(x, y, resource_type)
            resource.amount = random.randint(1, 3)
            self.dungeon_items.append(resource)
        else:
            # Предмет
            if random.random() < 0.1:  # 10% шанс легендарного предмета
                legendary_items = ['legendary_crown', 'shadow_cloak', 'demon_ring', 'void_amulet']
                item_name = random.choice(legendary_items)
                item = Item(x, y, 'accessory', item_name, 'legendary')
            else:
                # Обычный предмет
                item_types = ['weapon', 'armor', 'accessory']
                item_type = random.choice(item_types)
                
                if item_type == 'weapon':
                    item_name = random.choice(list(WEAPON_STATS.keys()))
                elif item_type == 'armor':
                    item_name = random.choice(list(ARMOR_STATS.keys()))
                else:
                    item_name = random.choice(list(ACCESSORY_STATS.keys()))
                
                rarity = random.choice(['common', 'rare', 'epic'])
                item = Item(x, y, item_type, item_name, rarity)
            
            self.dungeon_items.append(item)
    
    def handle_building_placement(self, mouse_pos):
        """Размещение построек"""
        if self.current_world != WORLD_BASE or self.game_mode != "build":
            return
        
        player = self.players[self.current_player]
        
        # Преобразуем координаты мыши в координаты сетки
        world_x = mouse_pos[0] + self.camera.x
        world_y = mouse_pos[1] + self.camera.y
        grid_x = world_x // GRID_SIZE
        grid_y = world_y // GRID_SIZE
        
        # Проверяем возможность размещения
        if not self.can_place_building(self.current_player, self.selected_building, grid_x, grid_y):
            return
        
        building_cost = BUILDING_COSTS.get(self.selected_building, {})
        
        if player.can_craft(building_cost):
            # Создаем постройку с привязкой к сетке
            building_x = grid_x * GRID_SIZE
            building_y = grid_y * GRID_SIZE
            
            if self.selected_building == "wall":
                building = Wall(building_x, building_y, self.current_player)
            elif self.selected_building == "tower":
                building = Tower(building_x, building_y, self.current_player)
            elif self.selected_building == "barracks":
                building = Barracks(building_x, building_y, self.current_player)
            elif self.selected_building == "workshop":
                building = Workshop(building_x, building_y, self.current_player)
            elif self.selected_building == "portal":
                building = Portal(building_x, building_y, self.current_player)
            elif self.selected_building == "dungeon_portal":
                building = DungeonPortal(building_x, building_y, self.current_player)
            elif self.selected_building == "shop":
                building = Shop(building_x, building_y, self.current_player)
            elif self.selected_building == "storage":
                building = Storage(building_x, building_y, self.current_player)
            else:
                return
            
            self.buildings[self.current_player].append(building)
            player.craft_item(building_cost)
            
            # Обновляем статистику строительства
            player.stats['buildings_built'] += 1
            player.gain_experience(15, self)  # 15 опыта за строительство
            
            self.update_building_grid(self.current_player)
            return True
    
    def handle_combat(self, mouse_pos):
        """Обработка боя и взаимодействия"""
        if self.current_world != WORLD_BASE or self.game_mode != "combat":
            return
        
        player = self.players[self.current_player]
        world_x = mouse_pos[0] + self.camera.x
        world_y = mouse_pos[1] + self.camera.y
        
        # Проверяем взаимодействие с собственными зданиями
        for building in self.buildings[self.current_player]:
            if isinstance(building, (Shop, Storage)):
                center_x = building.x + building.width // 2
                center_y = building.y + building.height // 2
                distance = math.sqrt((world_x - center_x)**2 + (world_y - center_y)**2)
                
                if distance <= 50:  # Радиус взаимодействия
                    if isinstance(building, Shop):
                        self.show_shop_interface = True
                        self.selected_shop = building
                    elif isinstance(building, Storage):
                        self.show_storage_interface = True
                        self.selected_storage = building
                    return
        
        # Атака других игроков
        for i, target in enumerate(self.players):
            if i != self.current_player:
                distance = math.sqrt((world_x - target.x)**2 + (world_y - target.y)**2)
                if distance <= PLAYER_ATTACK_RANGE:
                    player.attack(target)
                    break
        
        # Атака построек противника
        for player_id, buildings in self.buildings.items():
            if player_id != self.current_player:
                for building in buildings[:]:
                    center_x = building.x + building.width // 2
                    center_y = building.y + building.height // 2
                    distance = math.sqrt((world_x - center_x)**2 + (world_y - center_y)**2)
                    
                    if distance <= PLAYER_ATTACK_RANGE:
                        if player.equipped.get('weapon'):
                            damage = WEAPON_STATS[player.equipped['weapon']]['damage'] + player.damage_bonus
                            if building.take_damage(damage):
                                buildings.remove(building)
                        break
    
    def handle_crafting(self):
        """Обработка создания предметов"""
        player = self.players[self.current_player]
        
        # Проверяем, есть ли мастерская
        has_workshop = any(isinstance(b, Workshop) and b.owner_id == self.current_player 
                          for b in self.buildings[self.current_player])
        
        if not has_workshop:
            return
        
        # Создание оружия
        if not player.equipped['weapon']:
            for weapon_type, stats in WEAPON_STATS.items():
                if player.can_craft(stats['cost']):
                    player.craft_item(stats['cost'])
                    player.add_to_inventory(weapon_type, 'weapon')
                    break
        
        # Создание брони
        if not player.equipped['armor']:
            for armor_type, stats in ARMOR_STATS.items():
                if player.can_craft(stats['cost']):
                    player.craft_item(stats['cost'])
                    player.add_to_inventory(armor_type, 'armor')
                    break
    
    def update_ai_players(self):
        """Обновление ИИ игроков"""
        for i, ai_player in enumerate(self.ai_players):
            player = self.players[ai_player.player_id]
            
            # Даем ИИ ресурсы для тестирования (медленнее чем игроку)
            if random.random() < 0.05:
                for res_type in RESOURCE_TYPES.keys():
                    player.resources[res_type] += random.randint(0, 2)
            
            # Получить решение от ИИ
            try:
                action = ai_player.make_decision(self, player)
                self.execute_ai_action(ai_player, action, player)
            except Exception as e:
                print(f"Ошибка ИИ игрока {ai_player.player_id}: {e}")
            
            # Обновить игрока
            player.update({})  # Пустой словарь клавиш для ИИ
    
    def update(self):
        """Обновление игры"""
        if self.game_state != GameState.PLAYING:
            return
        
        # Автосохранение
        self.auto_save()
            
        player = self.players[self.current_player]
        
        # Обновление эффектов
        self.damage_indicators = [effect for effect in self.damage_indicators if effect.update()]
        self.level_up_effects = [effect for effect in self.level_up_effects if effect.update()]
        
        # Обновление уведомлений о достижениях
        for notification in self.achievement_notifications[:]:
            notification['timer'] -= 1
            if notification['timer'] <= 0:
                self.achievement_notifications.remove(notification)
        
        # Проверка достижений для текущего игрока
        new_achievements = player.check_achievements()
        for achievement in new_achievements:
            self.add_achievement_notification(achievement)
        
        # Отслеживание исследованных миров
        player.stats['worlds_explored'].add(self.current_world)
        
        # Обновление игрока
        keys = pygame.key.get_pressed()
        player.update(keys)
        
        # Обновление ИИ игроков
        self.update_ai_players()
        
        if self.current_world == WORLD_RESOURCE:
            # В мире ресурсов
            # Обновление тиммейтов
            for teammate in self.teammates[self.current_player]:
                teammate.update(self.resources, self.resource_piles, current_world=WORLD_RESOURCE)
            
            # Сбор ресурсов
            self.handle_resource_collection()
            
            # Спавн новых ресурсов
            self.spawn_resource_wave()
            
        elif self.current_world == WORLD_DUNGEON:
            # В подземелье
            # Обновление врагов
            for enemy in self.enemies[:]:
                if enemy.alive:
                    enemy.update([player])
                    
                    # Проверка атак игрока по врагам
                    if self.game_mode == "combat":
                        distance = math.sqrt((player.x - enemy.x)**2 + (player.y - enemy.y)**2)
                        if distance < 50 and player.equipped['weapon']:
                            if player.attack_cooldown == 0:
                                if player.attack(enemy):
                                    if not enemy.alive:
                                        # Враг убит, возможно выпадение предмета
                                        if random.random() < 0.3 + player.drop_chance_bonus:
                                            self.spawn_enemy_loot(enemy.x, enemy.y)
                else:
                    self.enemies.remove(enemy)
            
            # Обновление тиммейтов (боевой режим)
            for teammate in self.teammates[self.current_player]:
                teammate.update([], [], self.enemies, WORLD_DUNGEON)
            
            # Сбор предметов
            self.handle_dungeon_collection()
            
        elif self.current_world == WORLD_BASE:
            # В мире базы
            # Обновление тиммейтов (боевой режим)
            enemies = [p for i, p in enumerate(self.players) if i != self.current_player]
            for teammate in self.teammates[self.current_player]:
                teammate.update([], [], enemies, WORLD_BASE)
            
            # Обновление построек
            for player_id, buildings in self.buildings.items():
                for building in buildings:
                    if isinstance(building, Tower):
                        # Башни атакуют врагов
                        all_enemies = []
                        for i, p in enumerate(self.players):
                            if i != player_id:
                                all_enemies.append(p)
                        for i, teammates in self.teammates.items():
                            if i != player_id:
                                all_enemies.extend(teammates)
                        
                        building.update(all_enemies, self.current_world)
                    
                    elif isinstance(building, Barracks):
                        if building.update():  # Создать нового тиммейта
                            teammate = Teammate(building.x + building.width//2, 
                                              building.y + building.height//2, 
                                              player_id)
                            self.teammates[player_id].append(teammate)
                    
                    elif isinstance(building, Portal):
                        building.update()
                    
                    elif isinstance(building, DungeonPortal):
                        building.update()
                    
                    elif isinstance(building, Workshop):
                        # Мастерская больше не создает предметы автоматически
                        # Только обновляем таймер для анимации
                        building.update()
            
            # Автоматическое создание предметов отключено
            # Теперь крафт происходит только через интерфейс мастерской
        
        # Обновление камеры
        self.camera.update(player.x, player.y)
    
    def draw_world_resource(self):
        """Отрисовка мира ресурсов"""
        # Фон мира ресурсов
        self.screen.fill((50, 100, 50))  # Зеленоватый фон
        
        # Центральная зона спавна ресурсов
        center_x = RESOURCE_SPAWN_CENTER_X - self.camera.x
        center_y = RESOURCE_SPAWN_CENTER_Y - self.camera.y
        pygame.draw.circle(self.screen, (70, 120, 70), 
                          (int(center_x), int(center_y)), RESOURCE_SPAWN_RADIUS, 2)
        
        # Центральный портал в мире ресурсов
        portal_radius = 30 + int(8 * math.sin(pygame.time.get_ticks() * 0.005))
        pygame.draw.circle(self.screen, PURPLE, (int(center_x), int(center_y)), portal_radius, 4)
        pygame.draw.circle(self.screen, CYAN, (int(center_x), int(center_y)), portal_radius - 10, 2)
        
        # Подсказка для портала
        player = self.players[self.current_player]
        distance = math.sqrt((player.x - RESOURCE_SPAWN_CENTER_X)**2 + (player.y - RESOURCE_SPAWN_CENTER_Y)**2)
        if distance < 80:
            hint_text = self.small_font.render("Нажмите E для перехода в мир базы", True, WHITE)
            text_rect = hint_text.get_rect(center=(center_x, center_y - 60))
            pygame.draw.rect(self.screen, (0, 0, 0, 128), text_rect.inflate(10, 5))
            self.screen.blit(hint_text, text_rect)
        
        # Отрисовка ресурсов
        for resource in self.resources:
            resource.draw(self.screen, self.camera)
        
        # Отрисовка куч ресурсов
        for pile in self.resource_piles:
            pile.draw(self.screen, self.camera)
        
        # Отрисовка тиммейтов
        for teammate in self.teammates[self.current_player]:
            teammate.draw(self.screen, self.camera)
    
    def draw_world_base(self):
        """Отрисовка мира базы"""
        # Фон мира базы
        self.screen.fill((100, 50, 50))  # Красноватый фон
        
        # Отрисовка зон баз игроков
        for player_id, base in self.player_bases.items():
            base_screen_x = base['x'] - self.camera.x
            base_screen_y = base['y'] - self.camera.y
            
            color = (0, 100, 200) if player_id == self.current_player else (200, 100, 0)
            pygame.draw.rect(self.screen, color, 
                           (base_screen_x, base_screen_y, base['width'], base['height']), 3)
            
            # Отрисовка сетки строительства для текущего игрока
            if player_id == self.current_player and self.game_mode == "build":
                self.draw_building_grid(base, base_screen_x, base_screen_y)
        
        # Отрисовка построек
        for player_id, buildings in self.buildings.items():
            for building in buildings:
                building.draw(self.screen, self.camera)
                
                # Подсказки взаимодействия для зданий игрока
                if player_id == self.current_player:
                    player = self.players[self.current_player]
                    if hasattr(building, 'draw_interaction_hint'):
                        building.draw_interaction_hint(self.screen, self.camera, player)
                
                # Подписи к зданиям в режиме строительства при наведении
                if self.game_mode == "build" and player_id == self.current_player:
                    mouse_pos = pygame.mouse.get_pos()
                    world_x = mouse_pos[0] + self.camera.x
                    world_y = mouse_pos[1] + self.camera.y
                    
                    # Проверяем наведение на здание
                    if (building.x <= world_x <= building.x + building.width and 
                        building.y <= world_y <= building.y + building.height):
                        
                        # Отображаем название здания
                        building_names = {
                            'wall': 'Стена',
                            'tower': 'Башня',
                            'barracks': 'Казармы',
                            'workshop': 'Мастерская',
                            'portal': 'Портал',
                            'dungeon_portal': 'Портал в подземелье',
                            'shop': 'Магазин',
                            'storage': 'Хранилище'
                        }
                        
                        building_name = building_names.get(building.building_type, building.building_type)
                        label_text = self.small_font.render(building_name, True, WHITE)
                        label_x = building.x + building.width // 2 - self.camera.x
                        label_y = building.y - 25 - self.camera.y
                        
                        # Фон для текста
                        text_rect = label_text.get_rect(center=(label_x, label_y))
                        pygame.draw.rect(self.screen, (0, 0, 0, 180), text_rect.inflate(10, 5))
                        self.screen.blit(label_text, text_rect)
        
        # Отрисовка всех игроков в мире базы
        for player in self.players:
            player.draw(self.screen, self.camera)
        
        # Отрисовка тиммейтов
        for player_id, teammates in self.teammates.items():
            for teammate in teammates:
                teammate.draw(self.screen, self.camera)
        
        # Подсказки для порталов
        player = self.players[self.current_player]
        for building in self.buildings[self.current_player]:
            if isinstance(building, Portal) and building.can_use(player):
                portal_x = building.x + building.width // 2 - self.camera.x
                portal_y = building.y - 20 - self.camera.y
                hint_text = self.small_font.render("Нажмите E для перехода в мир ресурсов", True, WHITE)
                text_rect = hint_text.get_rect(center=(portal_x, portal_y))
                pygame.draw.rect(self.screen, (0, 0, 0, 128), text_rect.inflate(10, 5))
                self.screen.blit(hint_text, text_rect)
    
    def draw_building_grid(self, base, base_screen_x, base_screen_y):
        """Отрисовка сетки строительства"""
        # Рисуем сетку
        for x in range(0, base['width'], GRID_SIZE):
            pygame.draw.line(self.screen, GRAY, 
                           (base_screen_x + x, base_screen_y), 
                           (base_screen_x + x, base_screen_y + base['height']), 1)
        
        for y in range(0, base['height'], GRID_SIZE):
            pygame.draw.line(self.screen, GRAY, 
                           (base_screen_x, base_screen_y + y), 
                           (base_screen_x + base['width'], base_screen_y + y), 1)
        
        # Предпросмотр постройки
        mouse_pos = pygame.mouse.get_pos()
        world_x = mouse_pos[0] + self.camera.x
        world_y = mouse_pos[1] + self.camera.y
        
        # Проверяем, что мышь в зоне базы
        if (base['x'] <= world_x <= base['x'] + base['width'] and 
            base['y'] <= world_y <= base['y'] + base['height']):
            
            grid_x = world_x // GRID_SIZE
            grid_y = world_y // GRID_SIZE
            
            building_size = BUILDING_SIZES.get(self.selected_building, {'width': 1, 'height': 1})
            preview_x = (grid_x * GRID_SIZE) - self.camera.x
            preview_y = (grid_y * GRID_SIZE) - self.camera.y
            preview_width = building_size['width'] * GRID_SIZE
            preview_height = building_size['height'] * GRID_SIZE
            
            # Проверяем возможность размещения
            can_place = self.can_place_building(self.current_player, self.selected_building, grid_x, grid_y)
            player = self.players[self.current_player]
            building_cost = BUILDING_COSTS.get(self.selected_building, {})
            has_resources = player.can_craft(building_cost)
            
            # Цвет предпросмотра
            if can_place and has_resources:
                preview_color = (0, 255, 0, 100)  # Зеленый полупрозрачный
            elif can_place:
                preview_color = (255, 255, 0, 100)  # Желтый (нет ресурсов)
            else:
                preview_color = (255, 0, 0, 100)  # Красный (нельзя разместить)
            
            # Рисуем предпросмотр
            preview_surface = pygame.Surface((preview_width, preview_height), pygame.SRCALPHA)
            preview_surface.fill(preview_color)
            self.screen.blit(preview_surface, (preview_x, preview_y))
            
            # Рамка предпросмотра
            border_color = (0, 255, 0) if can_place and has_resources else (255, 0, 0)
            pygame.draw.rect(self.screen, border_color, 
                           (preview_x, preview_y, preview_width, preview_height), 2)
            
            # Показываем стоимость
            if building_cost:
                cost_y = preview_y - 30
                cost_text = f"Стоимость: "
                for i, (resource, amount) in enumerate(building_cost.items()):
                    if i > 0:
                        cost_text += ", "
                    cost_text += f"{RESOURCE_TYPES[resource]['name']}: {amount}"
                
                cost_surface = self.small_font.render(cost_text, True, WHITE)
                cost_rect = cost_surface.get_rect()
                cost_rect.centerx = preview_x + preview_width // 2
                cost_rect.y = cost_y
                
                # Фон для текста
                pygame.draw.rect(self.screen, (0, 0, 0, 180), cost_rect.inflate(10, 5))
                self.screen.blit(cost_surface, cost_rect)
        
        # Показываем подписи к существующим зданиям при наведении
        for building in self.buildings[self.current_player]:
            building_screen_x = building.x - self.camera.x
            building_screen_y = building.y - self.camera.y
            
            # Проверяем наведение мыши на здание
            if (building_screen_x <= mouse_pos[0] <= building_screen_x + building.width and
                building_screen_y <= mouse_pos[1] <= building_screen_y + building.height):
                
                # Определяем название здания
                building_names = {
                    'Wall': 'Стена',
                    'Tower': 'Башня',
                    'Barracks': 'Казармы',
                    'Workshop': 'Мастерская',
                    'Portal': 'Портал',
                    'DungeonPortal': 'Портал в подземелье',
                    'Shop': 'Магазин',
                    'Storage': 'Хранилище'
                }
                
                building_name = building_names.get(building.__class__.__name__, building.__class__.__name__)
                
                # Показываем подпись
                name_text = self.small_font.render(building_name, True, WHITE)
                name_rect = name_text.get_rect()
                name_rect.centerx = building_screen_x + building.width // 2
                name_rect.y = building_screen_y - 25
                
                # Фон для подписи
                pygame.draw.rect(self.screen, (0, 0, 0, 180), name_rect.inflate(10, 5))
                self.screen.blit(name_text, name_rect)
                
                # Показываем здоровье
                hp_text = f"HP: {building.hp}/{building.max_hp}"
                hp_surface = self.small_font.render(hp_text, True, GREEN if building.hp > building.max_hp * 0.5 else RED)
                hp_rect = hp_surface.get_rect()
                hp_rect.centerx = building_screen_x + building.width // 2
                hp_rect.y = building_screen_y - 10
                
                pygame.draw.rect(self.screen, (0, 0, 0, 180), hp_rect.inflate(10, 5))
                self.screen.blit(hp_surface, hp_rect)
    
    def draw(self):
        """Отрисовка игры"""
        if self.game_state == GameState.MENU:
            self.draw_menu()
        elif self.game_state == GameState.PLAYING:
            if self.current_world == WORLD_RESOURCE:
                self.draw_world_resource()
                # Отрисовка только текущего игрока в мире ресурсов
                self.players[self.current_player].draw(self.screen, self.camera)
            elif self.current_world == WORLD_BASE:
                self.draw_world_base()
            elif self.current_world == WORLD_DUNGEON:
                self.draw_world_dungeon()
                # Отрисовка только текущего игрока в подземелье
                self.players[self.current_player].draw(self.screen, self.camera)
            
            # UI
            self.draw_ui()
            
            # Инвентарь
            self.draw_inventory()
        
        # Визуальные эффекты
        for effect in self.damage_indicators:
            effect.draw(self.screen, self.camera)
        
        for effect in self.level_up_effects:
            effect.draw(self.screen, self.camera)
        
        # Уведомления о достижениях
        for i, notification in enumerate(self.achievement_notifications):
            alpha = min(255, notification['timer'] * 2)  # Плавное исчезновение
            
            font = pygame.font.Font(None, 24)
            text = font.render(f"🏆 {notification['text']}", True, (255, 215, 0))
            
            # Фон уведомления
            bg_rect = pygame.Rect(10, 100 + i * 35, text.get_width() + 20, 30)
            bg_surface = pygame.Surface(bg_rect.size, pygame.SRCALPHA)
            bg_surface.fill((0, 0, 0, min(180, alpha)))
            self.screen.blit(bg_surface, bg_rect.topleft)
            
            # Текст уведомления
            text_surface = pygame.Surface(text.get_size(), pygame.SRCALPHA)
            text_surface.set_alpha(alpha)
            text_surface.blit(text, (0, 0))
            self.screen.blit(text_surface, (20, 105 + i * 35))
        
        # Интерфейсы зданий
        if self.current_building_interface:
            self.current_building_interface.draw(self.screen)
        
        # Диалоги (поверх всего)
        if self.current_dialog:
            self.current_dialog.draw(self.screen)
        
        pygame.display.flip()
    
    def draw_ui(self):
        """Отрисовка интерфейса"""
        player = self.players[self.current_player]
        
        # Левая панель - основная информация (только если включена)
        if self.show_left_panel:
            self.draw_left_panel(player)
        else:
            # Минимальная информация если панель скрыта
            self.draw_minimal_ui(player)
        
        # Правая панель - статус ИИ и дополнительная информация
        self.draw_right_panel()
        
        # Нижняя панель - инструкции
        self.draw_bottom_panel()
    
    def draw_left_panel(self, player):
        """Отрисовка левой панели с основной информацией"""
        # Делаем панель более прозрачной и компактной
        panel_width = 280
        panel_height = min(350, SCREEN_HEIGHT - 250)  # Уменьшаем высоту
        
        # Создаем полупрозрачную поверхность
        panel_surface = pygame.Surface((panel_width, panel_height))
        panel_surface.set_alpha(180)  # Делаем более прозрачной
        panel_surface.fill((0, 0, 0))
        self.screen.blit(panel_surface, (5, 5))
        
        # Тонкая рамка
        pygame.draw.rect(self.screen, (255, 255, 255, 100), (5, 5, panel_width, panel_height), 1)
        
        y_offset = 15
        
        # Информация о мире
        world_names = {
            WORLD_RESOURCE: "МИР РЕСУРСОВ (PvP выкл.)",
            WORLD_BASE: "МИР БАЗЫ (PvP вкл.)",
            WORLD_DUNGEON: "ПОДЗЕМЕЛЬЕ (Опасно!)"
        }
        world_name = world_names.get(self.current_world, "НЕИЗВЕСТНЫЙ МИР")
        world_color = WHITE if self.current_world != WORLD_DUNGEON else RED
        world_text = self.font.render(world_name, True, world_color)
        self.screen.blit(world_text, (10, y_offset))
        y_offset += 35
        
        # Уровень и опыт
        level_text = self.font.render(f"Уровень: {player.level}", True, (255, 215, 0))
        self.screen.blit(level_text, (10, y_offset))
        y_offset += 25
        
        # Полоска опыта
        exp_bar_width = 200
        exp_bar_height = 8
        exp_progress = player.experience / player.experience_to_next_level
        
        pygame.draw.rect(self.screen, (50, 50, 50), (15, y_offset, exp_bar_width, exp_bar_height))
        pygame.draw.rect(self.screen, (0, 150, 255), (15, y_offset, int(exp_bar_width * exp_progress), exp_bar_height))
        pygame.draw.rect(self.screen, WHITE, (15, y_offset, exp_bar_width, exp_bar_height), 1)
        
        exp_text = self.small_font.render(f"Опыт: {player.experience}/{player.experience_to_next_level}", True, WHITE)
        self.screen.blit(exp_text, (220, y_offset - 2))
        y_offset += 25
        
        # Здоровье
        hp_text = self.font.render(f"HP: {player.hp}/{player.max_hp}", True, WHITE)
        self.screen.blit(hp_text, (10, y_offset))
        y_offset += 30
        
        # Режим игры
        mode_names = {"explore": "ИССЛЕДОВАНИЕ", "build": "СТРОИТЕЛЬСТВО", "combat": "БОЙ"}
        mode_text = self.font.render(f"Режим: {mode_names[self.game_mode]}", True, WHITE)
        self.screen.blit(mode_text, (10, y_offset))
        y_offset += 35
        
        # Экипировка
        if player.equipped['weapon'] or player.equipped['armor']:
            equip_title = self.small_font.render("ЭКИПИРОВКА:", True, YELLOW)
            self.screen.blit(equip_title, (10, y_offset))
            y_offset += 20
            
            if player.equipped['weapon']:
                weapon_text = self.small_font.render(f"• Оружие: {player.equipped['weapon']}", True, WHITE)
                self.screen.blit(weapon_text, (15, y_offset))
                y_offset += 18
            
            if player.equipped['armor']:
                armor_text = self.small_font.render(f"• Броня: {player.equipped['armor']}", True, WHITE)
                self.screen.blit(armor_text, (15, y_offset))
                y_offset += 18
            
            y_offset += 10
        
        # Тиммейты
        teammates_count = len(self.teammates[self.current_player])
        if teammates_count > 0:
            teammates_text = self.small_font.render(f"Тиммейты: {teammates_count}", True, GREEN)
            self.screen.blit(teammates_text, (10, y_offset))
            y_offset += 25
        
        # Ресурсы - компактное отображение
        resources_with_amounts = [(res_type, amount) for res_type, amount in player.resources.items() if amount > 0]
        if resources_with_amounts:
            res_title = self.small_font.render("РЕСУРСЫ:", True, YELLOW)
            self.screen.blit(res_title, (10, y_offset))
            y_offset += 18
            
            # Разделяем на обычные и уникальные
            normal_resources = ['wood', 'stone', 'iron', 'gold', 'crystal']
            unique_resources = ['shadow_essence', 'demon_blood', 'soul_gem', 'void_crystal']
            
            # Обычные ресурсы - очень компактно
            normal_res = [(res_type, amount) for res_type, amount in resources_with_amounts if res_type in normal_resources]
            if normal_res:
                # Показываем в одну строку через запятую
                res_strings = []
                for res_type, amount in normal_res:
                    short_names = {
                        'wood': 'Дер', 'stone': 'Кам', 'iron': 'Жел', 
                        'gold': 'Зол', 'crystal': 'Крис'
                    }
                    short_name = short_names.get(res_type, res_type[:3])
                    res_strings.append(f"{short_name}:{amount}")
                
                # Разбиваем на строки если слишком длинно
                res_text = ", ".join(res_strings)
                if len(res_text) > 35:
                    # Разбиваем пополам
                    mid = len(res_strings) // 2
                    line1 = ", ".join(res_strings[:mid])
                    line2 = ", ".join(res_strings[mid:])
                    
                    text1 = self.small_font.render(line1, True, WHITE)
                    self.screen.blit(text1, (15, y_offset))
                    y_offset += 16
                    
                    text2 = self.small_font.render(line2, True, WHITE)
                    self.screen.blit(text2, (15, y_offset))
                    y_offset += 16
                else:
                    text = self.small_font.render(res_text, True, WHITE)
                    self.screen.blit(text, (15, y_offset))
                    y_offset += 16
                
                y_offset += 5
            
            # Уникальные ресурсы - если есть
            unique_res = [(res_type, amount) for res_type, amount in resources_with_amounts if res_type in unique_resources]
            if unique_res:
                unique_title = self.small_font.render("Подземелье:", True, PURPLE)
                self.screen.blit(unique_title, (10, y_offset))
                y_offset += 16
                
                # Тоже компактно
                unique_strings = []
                for res_type, amount in unique_res:
                    short_names = {
                        'shadow_essence': 'Тень', 'demon_blood': 'Кровь',
                        'soul_gem': 'Душа', 'void_crystal': 'Пустота'
                    }
                    short_name = short_names.get(res_type, res_type[:4])
                    unique_strings.append(f"{short_name}:{amount}")
                
                unique_text = ", ".join(unique_strings)
                text = self.small_font.render(unique_text, True, PURPLE)
                self.screen.blit(text, (15, y_offset))
                y_offset += 16
        
        # Информация о строительстве
        if self.game_mode == "build" and self.current_world == WORLD_BASE:
            y_offset += 10
            build_title = self.small_font.render("СТРОИТЕЛЬСТВО:", True, YELLOW)
            self.screen.blit(build_title, (10, y_offset))
            y_offset += 20
            
            building_text = self.small_font.render(f"Постройка: {self.selected_building}", True, WHITE)
            self.screen.blit(building_text, (15, y_offset))
            y_offset += 18
            
            cost = BUILDING_COSTS.get(self.selected_building, {})
            if cost:
                cost_items = [f"{RESOURCE_TYPES[res]['name']}: {amount}" for res, amount in cost.items()]
                cost_str = ", ".join(cost_items)
                # Разбиваем длинную строку
                if len(cost_str) > 35:
                    words = cost_str.split(", ")
                    line1 = ", ".join(words[:len(words)//2])
                    line2 = ", ".join(words[len(words)//2:])
                    
                    cost_text1 = self.small_font.render(f"Стоимость: {line1}", True, WHITE)
                    self.screen.blit(cost_text1, (15, y_offset))
                    y_offset += 16
                    
                    cost_text2 = self.small_font.render(line2, True, WHITE)
                    self.screen.blit(cost_text2, (15, y_offset))
                    y_offset += 18
                else:
                    cost_text = self.small_font.render(f"Стоимость: {cost_str}", True, WHITE)
                    self.screen.blit(cost_text, (15, y_offset))
                    y_offset += 18
    
    def draw_minimal_ui(self, player):
        """Минимальный UI когда левая панель скрыта"""
        # Только самая важная информация
        y_offset = 10
        
        # Мир
        world_names = {
            WORLD_RESOURCE: "РЕСУРСЫ",
            WORLD_BASE: "БАЗА", 
            WORLD_DUNGEON: "ПОДЗЕМЕЛЬЕ"
        }
        world_name = world_names.get(self.current_world, "???")
        world_color = WHITE if self.current_world != WORLD_DUNGEON else RED
        world_text = self.small_font.render(world_name, True, world_color)
        self.screen.blit(world_text, (10, y_offset))
        y_offset += 25
        
        # Здоровье
        hp_text = self.small_font.render(f"HP: {player.hp}/{player.max_hp}", True, WHITE)
        self.screen.blit(hp_text, (10, y_offset))
        y_offset += 25
        
        # Режим
        mode_names = {"explore": "ИССЛЕД", "build": "СТРОЙКА", "combat": "БОЙ"}
        mode_text = self.small_font.render(f"Режим: {mode_names[self.game_mode]}", True, WHITE)
        self.screen.blit(mode_text, (10, y_offset))
        y_offset += 25
        
        # Подсказка
        hint_text = self.small_font.render("H - показать панель", True, GRAY)
        self.screen.blit(hint_text, (10, y_offset))
    
    def draw_right_panel(self):
        """Отрисовка правой панели"""
        # Статус ИИ
        ai_status = "ИИ: Ollama" if any(ai.ollama_available for ai in self.ai_players) else "ИИ: Простой"
        ai_text = self.small_font.render(ai_status, True, GREEN if "Ollama" in ai_status else YELLOW)
        self.screen.blit(ai_text, (SCREEN_WIDTH - 150, 10))
        
        # Мини-карта
        self.draw_minimap()
    
    def draw_minimap(self):
        """Отрисовка мини-карты"""
        minimap_size = 150
        minimap_x = SCREEN_WIDTH - minimap_size - 10
        minimap_y = 40
        
        # Фон мини-карты
        minimap_surface = pygame.Surface((minimap_size, minimap_size), pygame.SRCALPHA)
        minimap_surface.fill((0, 0, 0, 180))
        
        # Масштаб мини-карты
        scale_x = minimap_size / WORLD_WIDTH
        scale_y = minimap_size / WORLD_HEIGHT
        
        # Отрисовка игроков на мини-карте
        for i, player in enumerate(self.players):
            player_x = int(player.x * scale_x)
            player_y = int(player.y * scale_y)
            
            color = player.color if i == self.current_player else (100, 100, 100)
            pygame.draw.circle(minimap_surface, color, (player_x, player_y), 3)
            
            # Выделяем текущего игрока
            if i == self.current_player:
                pygame.draw.circle(minimap_surface, WHITE, (player_x, player_y), 5, 1)
        
        # Отрисовка построек на мини-карте
        if self.current_world == WORLD_BASE:
            for player_id, buildings in self.buildings.items():
                for building in buildings:
                    building_x = int(building.x * scale_x)
                    building_y = int(building.y * scale_y)
                    
                    if isinstance(building, Portal):
                        color = PURPLE
                    elif isinstance(building, DungeonPortal):
                        color = (100, 0, 100)
                    elif isinstance(building, Workshop):
                        color = ORANGE
                    elif isinstance(building, Shop):
                        color = CYAN
                    else:
                        color = (150, 150, 150)
                    
                    pygame.draw.rect(minimap_surface, color, (building_x-1, building_y-1, 3, 3))
        
        # Отрисовка ресурсов на мини-карте (только крупные кучи)
        elif self.current_world == WORLD_RESOURCE:
            for pile in self.resource_piles:
                if not pile.is_empty():
                    pile_x = int(pile.x * scale_x)
                    pile_y = int(pile.y * scale_y)
                    pygame.draw.circle(minimap_surface, BROWN, (pile_x, pile_y), 2)
        
        # Отрисовка врагов в подземелье
        elif self.current_world == WORLD_DUNGEON:
            for enemy in self.enemies:
                if enemy.alive:
                    enemy_x = int(enemy.x * scale_x)
                    enemy_y = int(enemy.y * scale_y)
                    pygame.draw.circle(minimap_surface, RED, (enemy_x, enemy_y), 2)
        
        # Рамка мини-карты
        pygame.draw.rect(minimap_surface, WHITE, (0, 0, minimap_size, minimap_size), 2)
        
        # Название мира
        world_names = {
            WORLD_RESOURCE: "Ресурсы",
            WORLD_BASE: "База", 
            WORLD_DUNGEON: "Подземелье"
        }
        world_name = world_names.get(self.current_world, "???")
        world_text = self.small_font.render(world_name, True, WHITE)
        minimap_surface.blit(world_text, (5, 5))
        
        self.screen.blit(minimap_surface, (minimap_x, minimap_y))
    
    def draw_bottom_panel(self):
        """Отрисовка нижней панели с инструкциями"""
        # Фон панели
        panel_height = 120
        panel_y = SCREEN_HEIGHT - panel_height
        pygame.draw.rect(self.screen, (0, 0, 0, 128), (0, panel_y, SCREEN_WIDTH, panel_height))
        pygame.draw.rect(self.screen, WHITE, (0, panel_y, SCREEN_WIDTH, panel_height), 1)
        
        # Инструкции в зависимости от режима
        if self.game_mode == "build" and self.current_world == WORLD_BASE:
            instructions = [
                "WASD - движение, E - здания/портал, ЛКМ - построить",
                "1-8 - тип постройки, R - расширить базу, TAB - инвентарь, H - панель",
                "F5 - быстрое сохранение, F9 - быстрая загрузка",
                "Ctrl+S - сохранить как, Ctrl+O - загрузить, ESC - выход"
            ]
        else:
            instructions = [
                "WASD - движение, E - здания/портал, Пробел - режим",
                "ЛКМ - действие, 1-8 - выбор постройки, TAB - инвентарь, H - панель", 
                "F5 - быстрое сохранение, F9 - быстрая загрузка",
                "Ctrl+S - сохранить как, Ctrl+O - загрузить, ESC - выход"
            ]
        
        for i, instruction in enumerate(instructions):
            text_surface = self.small_font.render(instruction, True, WHITE)
            self.screen.blit(text_surface, (10, panel_y + 10 + i * 20))
    
    def handle_building_interaction(self):
        """Обработка взаимодействия со зданиями"""
        if self.current_world != WORLD_BASE:
            return False
        
        player = self.players[self.current_player]
        
        # Проверяем все здания игрока
        for building in self.buildings.get(self.current_player, []):
            distance = math.sqrt((player.x - building.x)**2 + (player.y - building.y)**2)
            
            if distance < 60:  # Радиус взаимодействия
                if isinstance(building, Workshop):
                    self.current_building_interface = WorkshopInterface(building, player)
                    print("Открыта мастерская!")
                    return True
                elif isinstance(building, Shop):
                    self.current_building_interface = ShopInterface(building, player, self.players)
                    print("Открыт магазин!")
                    return True
        
        return False
    
    def handle_portal_interaction(self):
        """Обработка взаимодействия с порталом"""
        player = self.players[self.current_player]
        
        if self.current_world == WORLD_BASE:
            # Проверяем обычные порталы в базе
            for building in self.buildings[self.current_player]:
                if isinstance(building, Portal) and building.can_use(player):
                    print("Используем портал для перехода в мир ресурсов!")
                    self.switch_world(WORLD_RESOURCE)
                    return
                elif isinstance(building, DungeonPortal) and building.can_use(player):
                    print("Используем портал для перехода в подземелье!")
                    self.switch_world(WORLD_DUNGEON)
                    return
        elif self.current_world == WORLD_RESOURCE:
            # В мире ресурсов проверяем центральный портал
            center_x = RESOURCE_SPAWN_CENTER_X
            center_y = RESOURCE_SPAWN_CENTER_Y
            distance = math.sqrt((player.x - center_x)**2 + (player.y - center_y)**2)
            if distance < 60:  # Радиус взаимодействия с центральным порталом
                print("Используем портал для перехода в мир базы!")
                self.switch_world(WORLD_BASE)
                return
        elif self.current_world == WORLD_DUNGEON:
            # В подземелье проверяем портал выхода
            exit_x = 100
            exit_y = 100
            distance = math.sqrt((player.x - exit_x)**2 + (player.y - exit_y)**2)
            if distance < 60:
                print("Используем портал для выхода из подземелья!")
                self.switch_world(WORLD_BASE)
                return
    
    def init_game(self):
        """Инициализация новой игры"""
        # Создаем игроков
        self.players = [Player(200, 200, 0)]  # Основной игрок
        
        # Создаем ИИ игроков
        self.ai_players = []
        for i in range(self.num_ai_players):
            ai_player = Player(WORLD_WIDTH - 200 - i * 100, WORLD_HEIGHT - 200 - i * 100, i + 1)
            self.players.append(ai_player)
            self.ai_players.append(OllamaAI(i + 1))
        
        # Миры
        self.current_world = WORLD_RESOURCE
        
        # Объекты мира ресурсов
        self.resources = []
        self.resource_piles = []
        
        # Объекты мира базы
        self.teammates = {i: [] for i in range(len(self.players))}
        self.buildings = {i: [] for i in range(len(self.players))}
        
        # Базы игроков
        self.player_bases = {}
        for i in range(len(self.players)):
            if i == 0:
                self.player_bases[i] = {'x': 100, 'y': 100, 'width': 400, 'height': 300}
            else:
                # Размещаем базы ИИ в разных углах
                if i == 1:
                    self.player_bases[i] = {'x': WORLD_WIDTH - 500, 'y': 100, 'width': 400, 'height': 300}
                elif i == 2:
                    self.player_bases[i] = {'x': 100, 'y': WORLD_HEIGHT - 400, 'width': 400, 'height': 300}
                else:
                    self.player_bases[i] = {'x': WORLD_WIDTH - 500, 'y': WORLD_HEIGHT - 400, 'width': 400, 'height': 300}
        
        # Режимы игры
        self.game_mode = "explore"
        self.selected_building = "wall"
        self.selected_weapon = "sword"
        self.selected_armor = "leather"
        self.show_inventory = False
        
        # Генерация начальных объектов
        self.spawn_initial_resources()
        self.spawn_initial_piles()
        
        # Инициализация сеток строительства
        self.init_building_grids()
        
        # Создание начальных порталов
        self.create_initial_portals()
        
        print(f"Игра инициализирована с {len(self.players)} игроками ({self.num_ai_players} ИИ)")
    
    def spawn_dungeon_enemies(self):
        """Создать врагов в подземелье"""
        enemy_types = ['goblin', 'orc', 'skeleton', 'demon']
        for _ in range(15):  # 15 врагов
            x = random.randint(300, WORLD_WIDTH - 100)
            y = random.randint(300, WORLD_HEIGHT - 100)
            enemy_type = random.choice(enemy_types)
            self.enemies.append(Enemy(x, y, enemy_type))
        
        # Создаем уникальные предметы в подземелье
        legendary_items = ['legendary_crown', 'shadow_cloak', 'demon_ring', 'void_amulet']
        for _ in range(5):  # 5 легендарных предметов
            x = random.randint(100, WORLD_WIDTH - 100)
            y = random.randint(100, WORLD_HEIGHT - 100)
            item_name = random.choice(legendary_items)
            self.dungeon_items.append(Item(x, y, 'accessory', item_name, 'legendary'))
        
        # Создаем уникальные ресурсы
        dungeon_resources = ['shadow_essence', 'demon_blood', 'soul_gem', 'void_crystal']
        for _ in range(20):
            x = random.randint(100, WORLD_WIDTH - 100)
            y = random.randint(100, WORLD_HEIGHT - 100)
            resource_type = random.choice(dungeon_resources)
            self.dungeon_items.append(Resource(x, y, resource_type))
    
    def draw_world_dungeon(self):
        """Отрисовка подземелья"""
        # Темный фон подземелья
        self.screen.fill((20, 20, 30))  # Очень темный фон
        
        # Портал выхода
        exit_x = 100 - self.camera.x
        exit_y = 100 - self.camera.y
        radius = 25 + int(6 * math.sin(pygame.time.get_ticks() * 0.01))
        pygame.draw.circle(self.screen, (100, 100, 200), (int(exit_x), int(exit_y)), radius, 4)
        pygame.draw.circle(self.screen, (150, 150, 255), (int(exit_x), int(exit_y)), radius - 8, 2)
        
        # Подсказка для портала выхода
        player = self.players[self.current_player]
        distance = math.sqrt((player.x - 100)**2 + (player.y - 100)**2)
        if distance < 80:
            hint_text = self.small_font.render("Нажмите E для выхода из подземелья", True, WHITE)
            text_rect = hint_text.get_rect(center=(exit_x, exit_y - 40))
            pygame.draw.rect(self.screen, (0, 0, 0, 128), text_rect.inflate(10, 5))
            self.screen.blit(hint_text, text_rect)
        
        # Отрисовка врагов
        for enemy in self.enemies:
            if enemy.alive:
                enemy.draw(self.screen, self.camera)
        
        # Отрисовка предметов подземелья
        for item in self.dungeon_items:
            if not item.collected:
                item.draw(self.screen, self.camera)
        
        # Отрисовка тиммейтов
        for teammate in self.teammates[self.current_player]:
            teammate.draw(self.screen, self.camera)
    
    def draw_menu(self):
        """Отрисовка главного меню"""
        self.screen.fill(BLACK)
        
        # Заголовок
        title = pygame.font.Font(None, 72).render("МНОГОМИРОВАЯ ИГРА", True, WHITE)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 150))
        self.screen.blit(title, title_rect)
        
        subtitle = self.font.render("Ресурсы, строительство и PvP", True, GRAY)
        subtitle_rect = subtitle.get_rect(center=(SCREEN_WIDTH // 2, 200))
        self.screen.blit(subtitle, subtitle_rect)
        
        # Меню
        menu_items = [
            "Начать игру",
            f"Количество ИИ: {self.num_ai_players}",
            "Загрузить игру",
            "Выход"
        ]
        
        menu_y = 300
        for i, item in enumerate(menu_items):
            color = YELLOW if i == self.selected_menu_item else WHITE
            text = self.font.render(item, True, color)
            text_rect = text.get_rect(center=(SCREEN_WIDTH // 2, menu_y + i * 60))
            self.screen.blit(text, text_rect)
        
        # Статус Ollama
        try:
            ollama.list()
            ollama_status = "Ollama: Подключена (Умный ИИ)"
            status_color = GREEN
        except:
            ollama_status = "Ollama: Не найдена (Простой ИИ)"
            status_color = YELLOW
        
        status_text = self.small_font.render(ollama_status, True, status_color)
        status_rect = status_text.get_rect(center=(SCREEN_WIDTH // 2, 550))
        self.screen.blit(status_text, status_rect)
        
        # Инструкции
        instructions = [
            "Стрелки вверх/вниз - навигация",
            "Enter - выбрать",
            "Влево/вправо - изменить количество ИИ"
        ]
        
        for i, instruction in enumerate(instructions):
            text = self.small_font.render(instruction, True, GRAY)
            text_rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100 + i * 25))
            self.screen.blit(text, text_rect)
    
    def handle_menu_events(self, event):
        """Обработка событий меню"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected_menu_item = (self.selected_menu_item - 1) % 4
            elif event.key == pygame.K_DOWN:
                self.selected_menu_item = (self.selected_menu_item + 1) % 4
            elif event.key == pygame.K_LEFT and self.selected_menu_item == 1:
                self.num_ai_players = max(1, self.num_ai_players - 1)
            elif event.key == pygame.K_RIGHT and self.selected_menu_item == 1:
                self.num_ai_players = min(4, self.num_ai_players + 1)
            elif event.key == pygame.K_RETURN:
                if self.selected_menu_item == 0:  # Начать игру
                    self.init_game()
                    self.game_state = GameState.PLAYING
                elif self.selected_menu_item == 1:  # Количество ИИ
                    pass  # Уже обрабатывается стрелками
                elif self.selected_menu_item == 2:  # Загрузить игру
                    self.show_load_dialog()
                elif self.selected_menu_item == 3:  # Выход
                    return False
        return True
    
    def execute_ai_action(self, ai_player, action, player):
        """Выполнить действие ИИ"""
        if action["action"] == "move_to":
            target = action["target"]
            dx = target["x"] - player.x
            dy = target["y"] - player.y
            distance = math.sqrt(dx**2 + dy**2)
            
            if distance > 5:
                move_speed = player.speed
                player.x += (dx / distance) * move_speed
                player.y += (dy / distance) * move_speed
                
                # Ограничения мира
                player.x = max(player.size, min(player.x, WORLD_WIDTH - player.size))
                player.y = max(player.size, min(player.y, WORLD_HEIGHT - player.size))
        
        elif action["action"] == "use_portal":
            if self.current_world == WORLD_BASE:
                for building in self.buildings[ai_player.player_id]:
                    if isinstance(building, Portal) and building.can_use(player):
                        # Переключаем мир только для этого ИИ (упрощенно)
                        pass
            elif self.current_world == WORLD_RESOURCE:
                distance = math.sqrt((player.x - RESOURCE_SPAWN_CENTER_X)**2 + (player.y - RESOURCE_SPAWN_CENTER_Y)**2)
                if distance < 60:
                    # Переключаем мир (упрощенно)
                    pass
        
        elif action["action"] == "build":
            building_type = action["building_type"]
            position = action["position"]
            building_cost = BUILDING_COSTS.get(building_type, {})
            
            if player.can_craft(building_cost):
                if building_type == "wall":
                    building = Wall(position["x"], position["y"], ai_player.player_id)
                elif building_type == "tower":
                    building = Tower(position["x"], position["y"], ai_player.player_id)
                elif building_type == "barracks":
                    building = Barracks(position["x"], position["y"], ai_player.player_id)
                elif building_type == "workshop":
                    building = Workshop(position["x"], position["y"], ai_player.player_id)
                elif building_type == "portal":
                    building = Portal(position["x"], position["y"], ai_player.player_id)
                else:
                    return
                
                self.buildings[ai_player.player_id].append(building)
                player.craft_item(building_cost)
        
        elif action["action"] == "attack":
            target = action["target"]
            # Найти цель для атаки
            for i, enemy in enumerate(self.players):
                if i != ai_player.player_id:
                    distance = math.sqrt((player.x - enemy.x)**2 + (player.y - enemy.y)**2)
                    if distance < 50 and player.equipped['weapon']:
                        player.attack(enemy)
                        break
        
        elif action["action"] == "wander":
            # Случайное движение
            angle = random.uniform(0, 2 * math.pi)
            move_distance = 20
            new_x = player.x + move_distance * math.cos(angle)
            new_y = player.y + move_distance * math.sin(angle)
            
            player.x = max(player.size, min(new_x, WORLD_WIDTH - player.size))
            player.y = max(player.size, min(new_y, WORLD_HEIGHT - player.size))

    def get_game_data(self):
        """Получить данные игры для сохранения"""
        save_data = {
            'current_world': self.current_world,
            'current_player': self.current_player,
            'players': [],
            'teammates': {},
            'buildings': {},
            'resources': [],
            'resource_piles': [],
            'scroll_quests': [],
            'items': [],
            'enemies': [],
            'dungeon_items': []
        }
        
        # Сохраняем игроков
        for i, player in enumerate(self.players):
            player_data = {
                'x': player.x,
                'y': player.y,
                'hp': player.hp,
                'max_hp': player.max_hp,
                'resources': player.resources,
                'equipped': player.equipped,
                'inventory_slots': player.inventory_slots,
                'active_quests': player.active_quests,
                'completed_quests': player.completed_quests,
                'quest_progress': player.quest_progress
            }
            save_data['players'].append(player_data)
        
        # Сохраняем тиммейтов
        for player_id, teammates in self.teammates.items():
            save_data['teammates'][str(player_id)] = []
            for teammate in teammates:
                teammate_data = {
                    'x': teammate.x,
                    'y': teammate.y,
                    'hp': teammate.hp,
                    'max_hp': teammate.max_hp,
                    'weapon': teammate.weapon
                }
                save_data['teammates'][str(player_id)].append(teammate_data)
        
        # Сохраняем постройки
        for player_id, buildings in self.buildings.items():
            save_data['buildings'][str(player_id)] = []
            for building in buildings:
                building_data = {
                    'type': building.__class__.__name__,
                    'x': building.x,
                    'y': building.y,
                    'hp': building.hp,
                    'max_hp': getattr(building, 'max_hp', building.hp)
                }
                save_data['buildings'][str(player_id)].append(building_data)
        
        # Сохраняем ресурсы
        for resource in self.resources:
            if not resource.collected:
                resource_data = {
                    'x': resource.x,
                    'y': resource.y,
                    'type': resource.type,
                    'amount': resource.amount
                }
                save_data['resources'].append(resource_data)
        
        # Сохраняем кучи ресурсов
        for pile in self.resource_piles:
            if not pile.is_empty():
                pile_data = {
                    'x': pile.x,
                    'y': pile.y,
                    'resources': pile.resources,
                    'has_teammate': pile.has_teammate,
                    'has_weapon': pile.has_weapon,
                    'weapon_type': pile.weapon_type
                }
                save_data['resource_piles'].append(pile_data)
        
        # Сохраняем квесты
        for quest in self.scroll_quests:
            if not quest.collected:
                quest_data = {
                    'x': quest.x,
                    'y': quest.y,
                    'quest_type': quest.quest_type,
                    'reward_tier': quest.reward_tier,
                    'description': quest.description
                }
                save_data['scroll_quests'].append(quest_data)
        
        # Сохраняем предметы
        for item in self.items:
            if not item.collected:
                item_data = {
                    'x': item.x,
                    'y': item.y,
                    'item_type': item.item_type,
                    'item_name': item.item_name,
                    'rarity': item.rarity
                }
                save_data['items'].append(item_data)
        
        # Сохраняем врагов
        for enemy in self.enemies:
            if enemy.alive:
                enemy_data = {
                    'x': enemy.x,
                    'y': enemy.y,
                    'enemy_type': enemy.enemy_type,
                    'hp': enemy.hp,
                    'max_hp': enemy.max_hp
                }
                save_data['enemies'].append(enemy_data)
        
        return save_data
    
    def save_game_to_db(self, save_name, overwrite=False):
        """Сохранить игру в базу данных"""
        try:
            game_data = self.get_game_data()
            success, message = self.database.save_game(save_name, game_data, overwrite=overwrite)
            
            if success:
                self.unsaved_changes = False
                print(f"Игра сохранена как '{save_name}'")
            else:
                print(f"Ошибка сохранения: {message}")
            
            return success, message
            
        except Exception as e:
            error_msg = f"Ошибка сохранения: {str(e)}"
            print(error_msg)
            return False, error_msg
    
    def auto_save(self):
        """Автосохранение"""
        current_time = pygame.time.get_ticks()
        if current_time - self.last_autosave_time >= self.autosave_interval:
            self.database.auto_save(self.get_game_data())
            self.last_autosave_time = current_time
            print("Автосохранение выполнено")
    
    def load_game_from_db(self, save_name):
        """Загрузить игру из базы данных"""
        try:
            success, save_data, updated_at = self.database.load_game(save_name)
            
            if not success:
                print(f"Не удалось загрузить сохранение '{save_name}'")
                return False
            
            # Очищаем текущие данные
            self.resources.clear()
            self.resource_piles.clear()
            self.scroll_quests.clear()
            self.items.clear()
            self.enemies.clear()
            self.dungeon_items.clear()
            self.teammates.clear()
            self.buildings.clear()
            
            # Загружаем основные параметры
            self.current_world = save_data.get('current_world', WORLD_RESOURCE)
            self.current_player = save_data.get('current_player', 0)
            
            # Загружаем игроков
            if 'players' in save_data:
                for i, player_data in enumerate(save_data['players']):
                    if i < len(self.players):
                        self.players[i].x = player_data.get('x', self.players[i].x)
                        self.players[i].y = player_data.get('y', self.players[i].y)
                        self.players[i].hp = player_data.get('hp', self.players[i].hp)
                        self.players[i].max_hp = player_data.get('max_hp', self.players[i].max_hp)
                        self.players[i].resources = player_data.get('resources', self.players[i].resources)
                        
                        # Загружаем экипировку
                        equipped = player_data.get('equipped', {})
                        for slot, item in equipped.items():
                            self.players[i].equipped[slot] = item
                        
                        # Загружаем инвентарь
                        inventory = player_data.get('inventory_slots', [])
                        self.players[i].inventory_slots = inventory + [None] * (len(self.players[i].inventory_slots) - len(inventory))
                        
                        # Загружаем квесты
                        self.players[i].active_quests = player_data.get('active_quests', [])
                        self.players[i].completed_quests = player_data.get('completed_quests', [])
                        self.players[i].quest_progress = player_data.get('quest_progress', {})
                        
                        self.players[i].update_stats()
            
            # Загружаем тиммейтов
            if 'teammates' in save_data:
                for player_id_str, teammates_data in save_data['teammates'].items():
                    player_id = int(player_id_str)
                    self.teammates[player_id] = []
                    for teammate_data in teammates_data:
                        teammate = Teammate(teammate_data['x'], teammate_data['y'], player_id)
                        teammate.hp = teammate_data.get('hp', teammate.hp)
                        teammate.max_hp = teammate_data.get('max_hp', teammate.max_hp)
                        teammate.weapon = teammate_data.get('weapon', teammate.weapon)
                        self.teammates[player_id].append(teammate)
            
            # Загружаем постройки
            if 'buildings' in save_data:
                for player_id_str, buildings_data in save_data['buildings'].items():
                    player_id = int(player_id_str)
                    self.buildings[player_id] = []
                    for building_data in buildings_data:
                        building_type = building_data['type']
                        x, y = building_data['x'], building_data['y']
                        
                        if building_type == 'Wall':
                            building = Wall(x, y, player_id)
                        elif building_type == 'Tower':
                            building = Tower(x, y, player_id)
                        elif building_type == 'Barracks':
                            building = Barracks(x, y, player_id)
                        elif building_type == 'Workshop':
                            building = Workshop(x, y, player_id)
                        elif building_type == 'Portal':
                            building = Portal(x, y, player_id)
                        else:
                            continue
                        
                        building.hp = building_data.get('hp', building.hp)
                        self.buildings[player_id].append(building)
            
            # Загружаем ресурсы
            if 'resources' in save_data:
                self.resources = []
                for resource_data in save_data['resources']:
                    resource = Resource(resource_data['x'], resource_data['y'], resource_data['type'])
                    resource.amount = resource_data.get('amount', resource.amount)
                    self.resources.append(resource)
            
            # Загружаем кучи ресурсов
            if 'resource_piles' in save_data:
                self.resource_piles = []
                for pile_data in save_data['resource_piles']:
                    pile = ResourcePile(pile_data['x'], pile_data['y'])
                    pile.resources = pile_data.get('resources', pile.resources)
                    pile.has_teammate = pile_data.get('has_teammate', pile.has_teammate)
                    pile.has_weapon = pile_data.get('has_weapon', pile.has_weapon)
                    pile.weapon_type = pile_data.get('weapon_type', pile.weapon_type)
                    self.resource_piles.append(pile)
            
            print("Игра загружена!")
            
        except Exception as e:
            print(f"Ошибка загрузки: {e}")
            print("Начинаем новую игру")
    
    def draw_inventory(self):
        """Отрисовка улучшенного инвентаря"""
        if not self.show_inventory:
            return
        
        player = self.players[self.current_player]
        
        # Фон инвентаря
        inventory_width = 600
        inventory_height = 600
        inventory_x = SCREEN_WIDTH - inventory_width - 20
        inventory_y = 20
        
        pygame.draw.rect(self.screen, (40, 40, 40), 
                        (inventory_x, inventory_y, inventory_width, inventory_height))
        pygame.draw.rect(self.screen, WHITE, 
                        (inventory_x, inventory_y, inventory_width, inventory_height), 2)
        
        # Заголовок
        title = self.font.render("ИНВЕНТАРЬ И ЭКИПИРОВКА", True, WHITE)
        self.screen.blit(title, (inventory_x + 10, inventory_y + 10))
        
        # Слоты экипировки (левая сторона)
        equip_x = inventory_x + 20
        equip_y = inventory_y + 50
        slot_size = 40
        
        # Отрисовка слотов экипировки
        equipment_labels = {
            'weapon': 'Оружие',
            'armor': 'Броня', 
            'accessory1': 'Аксессуар 1',
            'accessory2': 'Аксессуар 2',
            'accessory3': 'Аксессуар 3'
        }
        
        for i, (slot, label) in enumerate(equipment_labels.items()):
            slot_y = equip_y + i * (slot_size + 10)
            
            # Слот
            slot_color = (60, 60, 60) if player.equipped[slot] else (30, 30, 30)
            pygame.draw.rect(self.screen, slot_color, 
                           (equip_x, slot_y, slot_size, slot_size))
            pygame.draw.rect(self.screen, WHITE, 
                           (equip_x, slot_y, slot_size, slot_size), 1)
            
            # Название слота
            label_text = self.small_font.render(label, True, WHITE)
            self.screen.blit(label_text, (equip_x + slot_size + 10, slot_y + 5))
            
            # Экипированный предмет
            if player.equipped[slot]:
                item_text = self.small_font.render(player.equipped[slot], True, YELLOW)
                self.screen.blit(item_text, (equip_x + slot_size + 10, slot_y + 20))
        
        # Слоты инвентаря (правая сторона)
        inv_start_x = inventory_x + 300
        inv_start_y = inventory_y + 50
        slots_per_row = 5
        
        for i, item in enumerate(player.inventory_slots):
            row = i // slots_per_row
            col = i % slots_per_row
            
            slot_x = inv_start_x + col * (slot_size + 5)
            slot_y = inv_start_y + row * (slot_size + 5)
            
            # Слот
            slot_color = (60, 60, 60) if item else (30, 30, 30)
            pygame.draw.rect(self.screen, slot_color, 
                           (slot_x, slot_y, slot_size, slot_size))
            pygame.draw.rect(self.screen, WHITE, 
                           (slot_x, slot_y, slot_size, slot_size), 1)
            
            # Предмет в слоте
            if item:
                # Цвет по типу предмета
                item_color = {'weapon': RED, 'armor': BLUE, 'accessory': PURPLE}.get(item['type'], WHITE)
                pygame.draw.circle(self.screen, item_color, 
                                 (slot_x + slot_size//2, slot_y + slot_size//2), 8)
        
        # Статистика игрока - в две колонки
        stats_y = inventory_y + 350
        stats_title = self.small_font.render("ХАРАКТЕРИСТИКИ:", True, YELLOW)
        self.screen.blit(stats_title, (inventory_x + 20, stats_y))
        stats_y += 25
        
        stats_left = [
            f"Здоровье: {player.hp}/{player.max_hp} (+{player.health_bonus})",
            f"Урон: {player.damage_bonus}",
            f"Защита: {player.defense_bonus}"
        ]
        
        stats_right = [
            f"Скорость: {player.speed:.1f} (+{player.speed_bonus})",
            f"Шанс дропа: +{player.drop_chance_bonus*100:.0f}%",
            f"Слотов инвентаря: {len(player.inventory_slots)} (+{player.inventory_bonus})"
        ]
        
        # Левая колонка статистики
        for i, stat in enumerate(stats_left):
            stat_text = self.small_font.render(stat, True, WHITE)
            self.screen.blit(stat_text, (inventory_x + 20, stats_y + i * 18))
        
        # Правая колонка статистики
        for i, stat in enumerate(stats_right):
            stat_text = self.small_font.render(stat, True, WHITE)
            self.screen.blit(stat_text, (inventory_x + 300, stats_y + i * 18))
        
        # Ресурсы (внизу) - компактное отображение
        resources_y = inventory_y + 420
        
        # Обычные ресурсы
        normal_resources = ['wood', 'stone', 'iron', 'gold', 'crystal']
        normal_res_with_amounts = [(res_type, player.resources.get(res_type, 0)) for res_type in normal_resources if player.resources.get(res_type, 0) > 0]
        
        if normal_res_with_amounts:
            normal_title = self.small_font.render("ОБЫЧНЫЕ РЕСУРСЫ:", True, YELLOW)
            self.screen.blit(normal_title, (inventory_x + 20, resources_y))
            resources_y += 20
            
            # Отображаем в 3 колонки
            for i, (res_type, amount) in enumerate(normal_res_with_amounts):
                res_name = RESOURCE_TYPES[res_type]['name']
                res_color = RESOURCE_TYPES[res_type]['color']
                text = self.small_font.render(f"{res_name}: {amount}", True, res_color)
                
                col = i % 3
                row = i // 3
                x_pos = inventory_x + 20 + col * 180
                y_pos = resources_y + row * 16
                
                self.screen.blit(text, (x_pos, y_pos))
            
            resources_y += ((len(normal_res_with_amounts) - 1) // 3 + 1) * 16 + 10
        
        # Уникальные ресурсы подземелья
        unique_resources = ['shadow_essence', 'demon_blood', 'soul_gem', 'void_crystal']
        unique_res_with_amounts = [(res_type, player.resources.get(res_type, 0)) for res_type in unique_resources if player.resources.get(res_type, 0) > 0]
        
        if unique_res_with_amounts:
            unique_title = self.small_font.render("РЕСУРСЫ ПОДЗЕМЕЛЬЯ:", True, PURPLE)
            self.screen.blit(unique_title, (inventory_x + 20, resources_y))
            resources_y += 20
            
            # Отображаем в 2 колонки
            for i, (res_type, amount) in enumerate(unique_res_with_amounts):
                res_name = RESOURCE_TYPES[res_type]['name']
                res_color = RESOURCE_TYPES[res_type]['color']
                text = self.small_font.render(f"{res_name}: {amount}", True, res_color)
                
                col = i % 2
                row = i // 2
                x_pos = inventory_x + 20 + col * 270
                y_pos = resources_y + row * 16
                
                self.screen.blit(text, (x_pos, y_pos))
        
        # Инструкции - в нижней части окна
        instructions = [
            "ЛКМ на слот - экипировать/снять",
            "ПКМ на предмет - использовать", 
            "TAB - закрыть инвентарь"
        ]
        
        inst_y = inventory_y + inventory_height - 50
        for i, instruction in enumerate(instructions):
            text_surface = self.small_font.render(instruction, True, GRAY)
            # Размещаем инструкции в одну строку через разделители
            if i == 0:
                self.screen.blit(text_surface, (inventory_x + 20, inst_y))
            elif i == 1:
                self.screen.blit(text_surface, (inventory_x + 220, inst_y))
            else:
                self.screen.blit(text_surface, (inventory_x + 420, inst_y))
    
    def handle_inventory_click(self, mouse_pos):
        """Обработка кликов в инвентаре"""
        if not self.show_inventory:
            return
        
        player = self.players[self.current_player]
        inventory_width = 600
        inventory_x = SCREEN_WIDTH - inventory_width - 20
        inventory_y = 20
        
        # Проверка кликов по слотам экипировки
        equip_x = inventory_x + 20
        equip_y = inventory_y + 50
        slot_size = 40
        
        equipment_slots = ['weapon', 'armor', 'accessory1', 'accessory2', 'accessory3']
        
        for i, slot in enumerate(equipment_slots):
            slot_y = equip_y + i * (slot_size + 10)
            
            if (equip_x <= mouse_pos[0] <= equip_x + slot_size and 
                slot_y <= mouse_pos[1] <= slot_y + slot_size):
                # Клик по слоту экипировки - снимаем предмет
                if player.equipped[slot]:
                    item_name = player.unequip_item(slot)
                    item_type = self.get_item_type(item_name)
                    if not player.add_to_inventory(item_name, item_type):
                        # Инвентарь полон, возвращаем предмет
                        player.equipped[slot] = item_name
                        player.update_stats()
                        print("Инвентарь полон!")
                return
        
        # Проверка кликов по слотам инвентаря
        inv_start_x = inventory_x + 300
        inv_start_y = inventory_y + 50
        slots_per_row = 5
        
        for i, item in enumerate(player.inventory_slots):
            row = i // slots_per_row
            col = i % slots_per_row
            
            slot_x = inv_start_x + col * (slot_size + 5)
            slot_y = inv_start_y + row * (slot_size + 5)
            
            if (slot_x <= mouse_pos[0] <= slot_x + slot_size and 
                slot_y <= mouse_pos[1] <= slot_y + slot_size):
                # Клик по слоту инвентаря - экипируем предмет
                if item:
                    old_item = player.equip_item(item['name'], item['type'])
                    player.remove_from_inventory(i)
                    
                    # Если был заменен предмет, добавляем его в инвентарь
                    if old_item:
                        old_item_type = self.get_item_type(old_item)
                        if not player.add_to_inventory(old_item, old_item_type):
                            print("Инвентарь полон! Предмет потерян.")
                return
    
    def get_item_type(self, item_name):
        """Определить тип предмета по названию"""
        if item_name in WEAPON_STATS:
            return 'weapon'
        elif item_name in ARMOR_STATS:
            return 'armor'
        elif item_name in ACCESSORY_STATS:
            return 'accessory'
        return 'unknown'

    def handle_events(self):
        """Обработка событий"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # Показываем диалог подтверждения выхода
                if self.game_state == GameState.PLAYING and not self.current_dialog:
                    self.current_dialog = show_exit_confirmation()
                    continue
                return False
            
            # Обработка диалогов (приоритет)
            if self.current_dialog:
                result = self.current_dialog.handle_event(event)
                if result is not None:
                    self.handle_dialog_result(result)
                continue
            
            # Обработка интерфейсов зданий
            if self.current_building_interface:
                result = self.current_building_interface.handle_event(event)
                if result == 'close':
                    self.current_building_interface = None
                continue
            
            if self.game_state == GameState.MENU:
                if not self.handle_menu_events(event):
                    return False
            
            elif self.game_state == GameState.PLAYING:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        # Показываем диалог подтверждения выхода
                        self.current_dialog = show_exit_confirmation()
                    elif event.key == pygame.K_SPACE:
                        # Переключение режимов
                        modes = ["explore", "build", "combat"]
                        current_index = modes.index(self.game_mode)
                        self.game_mode = modes[(current_index + 1) % len(modes)]
                        self.unsaved_changes = True
                    elif event.key == pygame.K_e:
                        if not self.handle_building_interaction():
                            self.handle_portal_interaction()
                    elif event.key == pygame.K_TAB:
                        self.show_inventory = not self.show_inventory
                    elif event.key == pygame.K_h:
                        # H - скрыть/показать левую панель
                        self.show_left_panel = not self.show_left_panel
                    elif event.key == pygame.K_F5:
                        # Быстрое сохранение
                        self.save_game_to_db("quicksave", overwrite=True)
                    elif event.key == pygame.K_F9:
                        # Быстрая загрузка
                        self.load_game_from_db("quicksave")
                    elif event.key == pygame.K_s and pygame.key.get_pressed()[pygame.K_LCTRL]:
                        # Ctrl+S - диалог сохранения
                        self.show_save_dialog()
                    elif event.key == pygame.K_o and pygame.key.get_pressed()[pygame.K_LCTRL]:
                        # Ctrl+O - диалог загрузки
                        self.show_load_dialog()
                    elif event.key == pygame.K_1:
                        self.selected_building = "wall"
                    elif event.key == pygame.K_2:
                        self.selected_building = "tower"
                    elif event.key == pygame.K_3:
                        self.selected_building = "barracks"
                    elif event.key == pygame.K_4:
                        self.selected_building = "workshop"
                    elif event.key == pygame.K_5:
                        self.selected_building = "portal"
                    elif event.key == pygame.K_6:
                        self.selected_building = "dungeon_portal"
                    elif event.key == pygame.K_7:
                        self.selected_building = "shop"
                    elif event.key == pygame.K_8:
                        self.selected_building = "storage"
                    elif event.key == pygame.K_r and self.game_mode == "build" and self.current_world == WORLD_BASE:
                        # Расширение базы (пока просто вправо)
                        if self.expand_base(self.current_player, 'right'):
                            print("База расширена!")
                            self.unsaved_changes = True
                
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = pygame.mouse.get_pos()
                    if event.button == 1:  # ЛКМ
                        if self.show_inventory:
                            self.handle_inventory_click(mouse_pos)
                        elif self.game_mode == "build":
                            if self.handle_building_placement(mouse_pos):
                                self.unsaved_changes = True
                        elif self.game_mode == "combat":
                            self.handle_combat(mouse_pos)
        
        return True
    
    def show_save_dialog(self):
        """Показать диалог сохранения"""
        saves_list = self.database.get_saves_list()
        self.current_dialog = SaveDialog(saves_list)
    
    def show_load_dialog(self):
        """Показать диалог загрузки"""
        saves_list = self.database.get_saves_list()
        self.current_dialog = LoadDialog(saves_list)
    
    def add_damage_indicator(self, x, y, damage, color=(255, 0, 0)):
        """Добавить индикатор урона"""
        self.damage_indicators.append(DamageIndicator(x, y, damage, color))
    
    def add_level_up_effect(self, x, y):
        """Добавить эффект повышения уровня"""
        self.level_up_effects.append(LevelUpEffect(x, y))
    
    def add_achievement_notification(self, achievement_text):
        """Добавить уведомление о достижении"""
        self.achievement_notifications.append({
            'text': achievement_text,
            'timer': 300,  # 5 секунд
            'y_offset': len(self.achievement_notifications) * 30
        })
    
    def handle_dialog_result(self, result):
        """Обработать результат диалога"""
        if not result:
            return
        
        if isinstance(result, dict):
            action = result.get('action')
            
            if action == 'save':
                save_name = result.get('name')
                if save_name:
                    # Проверяем, существует ли сохранение
                    saves_list = self.database.get_saves_list()
                    existing_save = any(save['name'] == save_name for save in saves_list)
                    
                    if existing_save:
                        # Показываем диалог подтверждения перезаписи
                        self.current_dialog = show_overwrite_confirmation(save_name)
                        self.pending_save_name = save_name
                    else:
                        # Сохраняем сразу
                        success, message = self.save_game_to_db(save_name)
                        if success:
                            self.current_dialog = None
            
            elif action == 'load':
                save_name = result.get('name')
                if save_name:
                    success = self.load_game_from_db(save_name)
                    if success:
                        self.current_dialog = None
                        self.game_state = GameState.PLAYING
            
            elif action == 'delete':
                save_name = result.get('name')
                if save_name:
                    success, message = self.database.delete_save(save_name)
                    if success:
                        # Обновляем диалог загрузки
                        self.show_load_dialog()
        
        elif result == 'yes' and hasattr(self, 'pending_save_name'):
            # Подтверждение перезаписи
            success, message = self.save_game_to_db(self.pending_save_name, overwrite=True)
            if success:
                self.current_dialog = None
            delattr(self, 'pending_save_name')
        
        elif result == 'no' and hasattr(self, 'pending_save_name'):
            # Отмена перезаписи - возвращаемся к диалогу сохранения
            self.show_save_dialog()
            delattr(self, 'pending_save_name')
        
        elif result == 'save_and_exit':
            # Быстрое сохранение и выход
            success, message = self.save_game_to_db("quicksave_exit", overwrite=True)
            pygame.quit()
            sys.exit()
        
        elif result == 'exit':
            # Выход без сохранения
            pygame.quit()
            sys.exit()
        
        elif result == 'cancel':
            # Отмена любого диалога
            self.current_dialog = None
    
    def run(self):
        """Основной игровой цикл"""
        running = True
        
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(60)
        
        pygame.quit()
        sys.exit()

# ===============================================
# ЗАПУСК ИГРЫ
# ===============================================

if __name__ == "__main__":
    game = Game()
    game.run()