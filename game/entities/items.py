import pygame
import random
from game.config import *

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

