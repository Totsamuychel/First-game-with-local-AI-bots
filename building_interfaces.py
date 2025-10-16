"""
Интерфейсы для взаимодействия со зданиями
"""
# -*- coding: utf-8 -*-
import pygame
import math

class BuildingInterface:
    """Базовый класс для интерфейсов зданий"""
    def __init__(self, building, player):
        self.building = building
        self.player = player
        self.active = True
        self.selected_item = 0
        self.scroll_offset = 0
        
        # Размеры интерфейса
        self.width = 800
        self.height = 600
        self.x = (1200 - self.width) // 2  # SCREEN_WIDTH
        self.y = (800 - self.height) // 2   # SCREEN_HEIGHT
        
        # Цвета
        self.bg_color = (40, 40, 40)
        self.border_color = (100, 100, 100)
        self.text_color = (255, 255, 255)
        self.selected_color = (80, 80, 120)
        self.button_color = (70, 70, 70)
        self.button_hover_color = (100, 100, 100)
        
        # Шрифты
        self.title_font = pygame.font.Font(None, 28)
        self.font = pygame.font.Font(None, 20)
        self.small_font = pygame.font.Font(None, 16)
        
        self.hovered_button = -1
    
    def handle_event(self, event):
        """Обработка событий"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE or event.key == pygame.K_e:
                self.active = False
                return 'close'
            elif event.key == pygame.K_UP:
                self.selected_item = max(0, self.selected_item - 1)
            elif event.key == pygame.K_DOWN:
                self.selected_item = min(len(self.get_items()) - 1, self.selected_item + 1)
            elif event.key == pygame.K_RETURN:
                return self.use_selected_item()
        
        elif event.type == pygame.MOUSEMOTION:
            self.handle_mouse_motion(event.pos)
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # ЛКМ
                return self.handle_mouse_click(event.pos)
        
        return None
    
    def handle_mouse_motion(self, mouse_pos):
        """Обработка движения мыши"""
        pass
    
    def handle_mouse_click(self, mouse_pos):
        """Обработка клика мыши"""
        pass
    
    def get_items(self):
        """Получить список доступных предметов"""
        return []
    
    def use_selected_item(self):
        """Использовать выбранный предмет"""
        pass
    
    def draw(self, screen):
        """Отрисовка интерфейса"""
        # Полупрозрачный фон
        overlay = pygame.Surface((1200, 800))  # SCREEN_WIDTH, SCREEN_HEIGHT
        overlay.set_alpha(128)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))
        
        # Основной прямоугольник
        pygame.draw.rect(screen, self.bg_color, (self.x, self.y, self.width, self.height))
        pygame.draw.rect(screen, self.border_color, (self.x, self.y, self.width, self.height), 2)


class WorkshopInterface(BuildingInterface):
    """Интерфейс мастерской для крафта"""
    def __init__(self, building, player):
        super().__init__(building, player)
        self.category = 'weapons'  # weapons, armor, accessories
        self.categories = ['weapons', 'armor', 'accessories']
        self.category_names = {
            'weapons': 'ОРУЖИЕ',
            'armor': 'БРОНЯ', 
            'accessories': 'АКСЕССУАРЫ'
        }
    
    def get_items(self):
        """Получить список предметов для крафта"""
        from main import WEAPON_STATS, ARMOR_STATS, ACCESSORY_STATS
        
        if self.category == 'weapons':
            return list(WEAPON_STATS.keys())
        elif self.category == 'armor':
            return list(ARMOR_STATS.keys())
        else:
            return list(ACCESSORY_STATS.keys())
    
    def can_craft(self, item_name):
        """Проверить, можно ли создать предмет"""
        from main import WEAPON_STATS, ARMOR_STATS, ACCESSORY_STATS
        
        if self.category == 'weapons':
            cost = WEAPON_STATS.get(item_name, {}).get('cost', {})
        elif self.category == 'armor':
            cost = ARMOR_STATS.get(item_name, {}).get('cost', {})
        else:
            cost = ACCESSORY_STATS.get(item_name, {}).get('cost', {})
        
        for resource, amount in cost.items():
            if self.player.resources.get(resource, 0) < amount:
                return False
        return True
    
    def craft_item(self, item_name):
        """Создать предмет"""
        from main import WEAPON_STATS, ARMOR_STATS, ACCESSORY_STATS
        
        if not self.can_craft(item_name):
            return False
        
        # Определяем тип и стоимость
        if self.category == 'weapons':
            cost = WEAPON_STATS.get(item_name, {}).get('cost', {})
            item_type = 'weapon'
        elif self.category == 'armor':
            cost = ARMOR_STATS.get(item_name, {}).get('cost', {})
            item_type = 'armor'
        else:
            cost = ACCESSORY_STATS.get(item_name, {}).get('cost', {})
            item_type = 'accessory'
        
        # Тратим ресурсы
        for resource, amount in cost.items():
            self.player.resources[resource] -= amount
        
        # Добавляем предмет в инвентарь
        if self.player.add_to_inventory(item_name, item_type):
            # Обновляем статистику крафта
            self.player.stats['items_crafted'] += 1
            # Добавляем опыт за крафт
            if hasattr(self.player, 'gain_experience'):
                self.player.gain_experience(10)  # 10 опыта за крафт
            print(f"Создан предмет: {item_name}")
            return True
        else:
            # Возвращаем ресурсы если инвентарь полон
            for resource, amount in cost.items():
                self.player.resources[resource] += amount
            print("Инвентарь полон!")
            return False
    
    def handle_event(self, event):
        """Обработка событий мастерской"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                current_idx = self.categories.index(self.category)
                self.category = self.categories[(current_idx - 1) % len(self.categories)]
                self.selected_item = 0
            elif event.key == pygame.K_RIGHT:
                current_idx = self.categories.index(self.category)
                self.category = self.categories[(current_idx + 1) % len(self.categories)]
                self.selected_item = 0
        
        return super().handle_event(event)
    
    def use_selected_item(self):
        """Создать выбранный предмет"""
        items = self.get_items()
        if 0 <= self.selected_item < len(items):
            item_name = items[self.selected_item]
            self.craft_item(item_name)
        return None
    
    def handle_mouse_click(self, mouse_pos):
        """Обработка клика мыши в мастерской"""
        # Проверяем клик по категориям
        for i, category in enumerate(self.categories):
            tab_x = self.x + 20 + i * 120
            tab_y = self.y + 50
            tab_rect = pygame.Rect(tab_x, tab_y, 110, 30)
            
            if tab_rect.collidepoint(mouse_pos):
                self.category = category
                self.selected_item = 0
                return None
        
        # Проверяем клик по предметам
        items = self.get_items()
        for i, item in enumerate(items):
            item_y = self.y + 120 + i * 40
            item_rect = pygame.Rect(self.x + 20, item_y, self.width - 40, 35)
            
            if item_rect.collidepoint(mouse_pos):
                self.selected_item = i
                self.craft_item(item)
                return None
        
        return None
    
    def draw(self, screen):
        """Отрисовка интерфейса мастерской"""
        super().draw(screen)
        
        # Заголовок
        title = self.title_font.render("МАСТЕРСКАЯ", True, self.text_color)
        screen.blit(title, (self.x + 20, self.y + 10))
        
        # Вкладки категорий
        for i, category in enumerate(self.categories):
            tab_x = self.x + 20 + i * 120
            tab_y = self.y + 50
            tab_color = self.selected_color if category == self.category else self.button_color
            
            pygame.draw.rect(screen, tab_color, (tab_x, tab_y, 110, 30))
            pygame.draw.rect(screen, self.border_color, (tab_x, tab_y, 110, 30), 1)
            
            tab_text = self.font.render(self.category_names[category], True, self.text_color)
            text_x = tab_x + (110 - tab_text.get_width()) // 2
            screen.blit(tab_text, (text_x, tab_y + 5))
        
        # Список предметов
        items = self.get_items()
        for i, item in enumerate(items):
            item_y = self.y + 120 + i * 40
            
            # Фон предмета
            item_color = self.selected_color if i == self.selected_item else self.bg_color
            pygame.draw.rect(screen, item_color, (self.x + 20, item_y, self.width - 40, 35))
            pygame.draw.rect(screen, self.border_color, (self.x + 20, item_y, self.width - 40, 35), 1)
            
            # Название предмета
            item_text = self.font.render(item.replace('_', ' ').title(), True, self.text_color)
            screen.blit(item_text, (self.x + 30, item_y + 5))
            
            # Стоимость
            from main import WEAPON_STATS, ARMOR_STATS, ACCESSORY_STATS
            
            if self.category == 'weapons':
                cost = WEAPON_STATS.get(item, {}).get('cost', {})
                stats = WEAPON_STATS.get(item, {})
                stats_text = f"Урон: {stats.get('damage', 0)}, Дальность: {stats.get('range', 0)}"
            elif self.category == 'armor':
                cost = ARMOR_STATS.get(item, {}).get('cost', {})
                stats = ARMOR_STATS.get(item, {})
                stats_text = f"Защита: {stats.get('defense', 0)}"
            else:
                cost = ACCESSORY_STATS.get(item, {}).get('cost', {})
                stats = ACCESSORY_STATS.get(item, {})
                bonuses = []
                if stats.get('damage_bonus'): bonuses.append(f"Урон +{stats['damage_bonus']}")
                if stats.get('defense_bonus'): bonuses.append(f"Защита +{stats['defense_bonus']}")
                if stats.get('speed_bonus'): bonuses.append(f"Скорость +{stats['speed_bonus']}")
                if stats.get('health_bonus'): bonuses.append(f"Здоровье +{stats['health_bonus']}")
                stats_text = ", ".join(bonuses) if bonuses else "Особые свойства"
            
            # Статистики предмета
            stats_surface = self.small_font.render(stats_text, True, (200, 200, 200))
            screen.blit(stats_surface, (self.x + 30, item_y + 20))
            
            # Стоимость
            cost_items = []
            can_craft = True
            for resource, amount in cost.items():
                from main import RESOURCE_TYPES
                res_name = RESOURCE_TYPES.get(resource, {}).get('name', resource)
                player_amount = self.player.resources.get(resource, 0)
                
                if player_amount < amount:
                    can_craft = False
                    color = (255, 100, 100)  # Красный если не хватает
                else:
                    color = (100, 255, 100)  # Зеленый если хватает
                
                cost_items.append((f"{res_name}: {amount}", color))
            
            # Отображаем стоимость
            cost_x = self.x + 400
            for j, (cost_text, color) in enumerate(cost_items):
                cost_surface = self.small_font.render(cost_text, True, color)
                screen.blit(cost_surface, (cost_x, item_y + 5 + j * 12))
            
            # Индикатор возможности крафта
            if can_craft:
                craft_text = self.small_font.render("✓ Можно создать", True, (100, 255, 100))
            else:
                craft_text = self.small_font.render("✗ Не хватает ресурсов", True, (255, 100, 100))
            
            screen.blit(craft_text, (self.x + 600, item_y + 10))
        
        # Инструкции
        instructions = [
            "← → - переключение категорий",
            "↑ ↓ - выбор предмета",
            "Enter или ЛКМ - создать предмет",
            "E или ESC - закрыть"
        ]
        
        for i, instruction in enumerate(instructions):
            inst_surface = self.small_font.render(instruction, True, (150, 150, 150))
            screen.blit(inst_surface, (self.x + 20, self.y + self.height - 80 + i * 15))


class ShopInterface(BuildingInterface):
    """Интерфейс магазина для торговли"""
    def __init__(self, building, player, all_players):
        super().__init__(building, player)
        self.all_players = all_players
        self.mode = 'buy'  # buy, sell
        self.selected_player = 0
        self.trade_offers = []  # Предложения торговли
    
    def get_other_players(self):
        """Получить список других игроков"""
        return [p for p in self.all_players if p.player_id != self.player.player_id]
    
    def get_trade_items(self):
        """Получить предметы для торговли"""
        if self.mode == 'sell':
            # Показываем предметы игрока для продажи
            items = []
            for slot in self.player.inventory_slots:
                if slot:
                    items.append(slot)
            return items
        else:
            # Показываем предметы других игроков для покупки
            other_players = self.get_other_players()
            if other_players and self.selected_player < len(other_players):
                player = other_players[self.selected_player]
                items = []
                for slot in player.inventory_slots:
                    if slot:
                        items.append(slot)
                return items
            return []
    
    def handle_event(self, event):
        """Обработка событий магазина"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                self.mode = 'sell' if self.mode == 'buy' else 'buy'
                self.selected_item = 0
            elif event.key == pygame.K_LEFT and self.mode == 'buy':
                other_players = self.get_other_players()
                if other_players:
                    self.selected_player = (self.selected_player - 1) % len(other_players)
                    self.selected_item = 0
            elif event.key == pygame.K_RIGHT and self.mode == 'buy':
                other_players = self.get_other_players()
                if other_players:
                    self.selected_player = (self.selected_player + 1) % len(other_players)
                    self.selected_item = 0
        
        return super().handle_event(event)
    
    def use_selected_item(self):
        """Торговать выбранным предметом"""
        items = self.get_trade_items()
        if 0 <= self.selected_item < len(items):
            item = items[self.selected_item]
            
            if self.mode == 'sell':
                # Продаем предмет за золото
                gold_value = self.get_item_value(item)
                self.player.resources['gold'] += gold_value
                
                # Удаляем предмет из инвентаря
                for i, slot in enumerate(self.player.inventory_slots):
                    if slot == item:
                        self.player.inventory_slots[i] = None
                        break
                
                # Обновляем статистику торговли
                self.player.stats['trades_completed'] += 1
                print(f"Продан предмет {item['name']} за {gold_value} золота")
            
            else:
                # Покупаем предмет у другого игрока
                other_players = self.get_other_players()
                if other_players and self.selected_player < len(other_players):
                    seller = other_players[self.selected_player]
                    gold_value = self.get_item_value(item)
                    
                    if self.player.resources.get('gold', 0) >= gold_value:
                        # Покупаем предмет
                        if self.player.add_to_inventory(item['name'], item['type']):
                            self.player.resources['gold'] -= gold_value
                            seller.resources['gold'] += gold_value
                            
                            # Удаляем предмет у продавца
                            for i, slot in enumerate(seller.inventory_slots):
                                if slot == item:
                                    seller.inventory_slots[i] = None
                                    break
                            
                            # Обновляем статистику торговли
                            self.player.stats['trades_completed'] += 1
                            print(f"Куплен предмет {item['name']} за {gold_value} золота")
                        else:
                            print("Инвентарь полон!")
                    else:
                        print("Не хватает золота!")
        
        return None
    
    def get_item_value(self, item):
        """Получить стоимость предмета в золоте"""
        from main import WEAPON_STATS, ARMOR_STATS, ACCESSORY_STATS
        
        if item['type'] == 'weapon':
            stats = WEAPON_STATS.get(item['name'], {})
            return stats.get('damage', 10) * 2
        elif item['type'] == 'armor':
            stats = ARMOR_STATS.get(item['name'], {})
            return stats.get('defense', 5) * 3
        else:
            # Аксессуары дороже
            return 50
    
    def draw(self, screen):
        """Отрисовка интерфейса магазина"""
        super().draw(screen)
        
        # Заголовок
        title = self.title_font.render("МАГАЗИН", True, self.text_color)
        screen.blit(title, (self.x + 20, self.y + 10))
        
        # Режимы торговли
        buy_color = self.selected_color if self.mode == 'buy' else self.button_color
        sell_color = self.selected_color if self.mode == 'sell' else self.button_color
        
        pygame.draw.rect(screen, buy_color, (self.x + 20, self.y + 50, 100, 30))
        pygame.draw.rect(screen, self.border_color, (self.x + 20, self.y + 50, 100, 30), 1)
        buy_text = self.font.render("ПОКУПКА", True, self.text_color)
        screen.blit(buy_text, (self.x + 35, self.y + 55))
        
        pygame.draw.rect(screen, sell_color, (self.x + 130, self.y + 50, 100, 30))
        pygame.draw.rect(screen, self.border_color, (self.x + 130, self.y + 50, 100, 30), 1)
        sell_text = self.font.render("ПРОДАЖА", True, self.text_color)
        screen.blit(sell_text, (self.x + 145, self.y + 55))
        
        # Информация о золоте игрока
        gold_text = self.font.render(f"Ваше золото: {self.player.resources.get('gold', 0)}", True, (255, 215, 0))
        screen.blit(gold_text, (self.x + 400, self.y + 55))
        
        if self.mode == 'buy':
            # Выбор игрока для покупки
            other_players = self.get_other_players()
            if other_players:
                if self.selected_player < len(other_players):
                    player = other_players[self.selected_player]
                    player_text = self.font.render(f"Игрок {player.player_id + 1} (← →)", True, self.text_color)
                    screen.blit(player_text, (self.x + 20, self.y + 90))
                    
                    player_gold_text = self.small_font.render(f"Золото: {player.resources.get('gold', 0)}", True, (255, 215, 0))
                    screen.blit(player_gold_text, (self.x + 200, self.y + 95))
            else:
                no_players_text = self.font.render("Нет других игроков", True, (150, 150, 150))
                screen.blit(no_players_text, (self.x + 20, self.y + 90))
        
        # Список предметов
        items = self.get_trade_items()
        start_y = self.y + 120
        
        if not items:
            no_items_text = self.font.render("Нет предметов для торговли", True, (150, 150, 150))
            screen.blit(no_items_text, (self.x + 20, start_y))
        else:
            for i, item in enumerate(items):
                item_y = start_y + i * 40
                
                # Фон предмета
                item_color = self.selected_color if i == self.selected_item else self.bg_color
                pygame.draw.rect(screen, item_color, (self.x + 20, item_y, self.width - 40, 35))
                pygame.draw.rect(screen, self.border_color, (self.x + 20, item_y, self.width - 40, 35), 1)
                
                # Название предмета
                item_text = self.font.render(f"{item['name'].replace('_', ' ').title()} ({item['type']})", True, self.text_color)
                screen.blit(item_text, (self.x + 30, item_y + 5))
                
                # Стоимость
                value = self.get_item_value(item)
                value_text = self.font.render(f"{value} золота", True, (255, 215, 0))
                screen.blit(value_text, (self.x + 400, item_y + 10))
                
                # Статистики предмета
                from main import WEAPON_STATS, ARMOR_STATS, ACCESSORY_STATS
                
                if item['type'] == 'weapon':
                    stats = WEAPON_STATS.get(item['name'], {})
                    stats_text = f"Урон: {stats.get('damage', 0)}, Дальность: {stats.get('range', 0)}"
                elif item['type'] == 'armor':
                    stats = ARMOR_STATS.get(item['name'], {})
                    stats_text = f"Защита: {stats.get('defense', 0)}"
                else:
                    stats_text = "Аксессуар"
                
                stats_surface = self.small_font.render(stats_text, True, (200, 200, 200))
                screen.blit(stats_surface, (self.x + 30, item_y + 20))
        
        # Инструкции
        if self.mode == 'buy':
            instructions = [
                "← → - выбор игрока",
                "↑ ↓ - выбор предмета",
                "Enter - купить предмет",
                "Tab - режим продажи",
                "E - закрыть"
            ]
        else:
            instructions = [
                "↑ ↓ - выбор предмета",
                "Enter - продать предмет",
                "Tab - режим покупки",
                "E - закрыть"
            ]
        
        for i, instruction in enumerate(instructions):
            inst_surface = self.small_font.render(instruction, True, (150, 150, 150))
            screen.blit(inst_surface, (self.x + 20, self.y + self.height - 80 + i * 15))