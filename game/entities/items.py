import pygame
import random
from game.config import *

class Resource:
    """Collectible resource"""
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
            # Show amount
            font = pygame.font.Font(None, 16)
            text = font.render(str(self.amount), True, WHITE)
            screen.blit(text, (screen_x - 5, screen_y - 5))

class ScrollQuest:
    """Quest scroll"""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.size = 12
        self.quest_type = random.choice(list(QUEST_TYPES.keys()))
        self.reward_tier = random.choice(['small', 'medium', 'large'])
        self.collected = False

        # Generate quest task
        if self.quest_type == 'collect':
            self.target_resource = random.choice(list(RESOURCE_TYPES.keys()))
            self.target_amount = random.randint(10, 30)
            self.description = f"Collect {self.target_amount} {RESOURCE_TYPES[self.target_resource]['name']}"
        elif self.quest_type == 'build':
            self.target_building = random.choice(['wall', 'tower', 'barracks'])
            self.target_amount = random.randint(1, 3)
            self.description = f"Build {self.target_amount} {self.target_building}"
        elif self.quest_type == 'kill':
            self.target_amount = random.randint(3, 10)
            self.description = f"Kill {self.target_amount} enemies"
        else:  # explore
            self.description = "Explore the dungeon"

    def draw(self, screen, camera):
        if self.collected:
            return
        screen_x = self.x - camera.x
        screen_y = self.y - camera.y
        if -self.size <= screen_x <= SCREEN_WIDTH + self.size and -self.size <= screen_y <= SCREEN_HEIGHT + self.size:
            # Scroll
            pygame.draw.rect(screen, (255, 255, 200),
                            (int(screen_x - self.size), int(screen_y - self.size),
                             self.size * 2, self.size * 2))
            pygame.draw.rect(screen, (200, 200, 150),
                            (int(screen_x - self.size), int(screen_y - self.size),
                             self.size * 2, self.size * 2), 2)
            # Quest symbol
            font = pygame.font.Font(None, 16)
            text = font.render("Q", True, (100, 50, 0))
            screen.blit(text, (screen_x - 5, screen_y - 8))

class Item:
    """Base class for items"""
    def __init__(self, x, y, item_type, item_name, rarity="common"):
        self.x = x
        self.y = y
        self.size = 10
        self.item_type = item_type  # weapon, armor, accessory
        self.item_name = item_name
        self.rarity = rarity
        self.collected = False

        # Colors by rarity
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
    """Resource pile — may contain a teammate or weapon"""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.size = 25
        self.resources = []
        self.has_teammate = random.random() < TEAMMATE_SPAWN_CHANCE
        self.has_weapon = random.random() < 0.1  # 10% chance to find a weapon
        self.weapon_type = random.choice(list(WEAPON_STATS.keys())) if self.has_weapon else None
        self.has_scroll = random.random() < 0.05  # 5% chance to find a quest scroll
        self.scroll_quest = ScrollQuest(x, y) if self.has_scroll else None

        # Generate resources in the pile
        for _ in range(random.randint(3, 8)):
            self.resources.append({
                'type': random.choice(list(RESOURCE_TYPES.keys())),
                'amount': random.randint(2, 5)
            })

    def collect(self):
        """Collect all resources from the pile"""
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
            # Main pile
            pygame.draw.circle(screen, BROWN, (int(screen_x), int(screen_y)), self.size)
            # Content indicators
            if self.has_teammate:
                pygame.draw.circle(screen, GREEN, (int(screen_x - 10), int(screen_y - 10)), 5)
            if self.has_weapon:
                pygame.draw.circle(screen, RED, (int(screen_x + 10), int(screen_y - 10)), 5)
            if self.has_scroll:
                pygame.draw.circle(screen, YELLOW, (int(screen_x), int(screen_y + 15)), 5)
