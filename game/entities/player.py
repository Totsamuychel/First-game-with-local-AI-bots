import pygame
import math
from game.config import *

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

