import pygame
import math
from game.config import *

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

