import pygame
from enum import Enum

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
