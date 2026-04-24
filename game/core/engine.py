import pygame
import math
import random
import sys
import time
from game.config import *
from game.core.camera import Camera
from game.core.ai_player import OllamaAI
from game.entities.player import Player
from game.entities.teammate import Teammate
from game.entities.enemy import Enemy
from game.entities.items import Resource, ResourcePile, ScrollQuest, Item
from game.world.buildings import *
from game.world.effects import DamageIndicator, LevelUpEffect
from game.utils.database import GameDatabase
from game.ui.dialogs import Dialog, SaveDialog, LoadDialog, show_exit_confirmation, show_overwrite_confirmation
from game.ui.interfaces import WorkshopInterface, ShopInterface

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

