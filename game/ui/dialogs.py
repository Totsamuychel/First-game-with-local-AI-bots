"""
Система диалогов для игры
"""
# -*- coding: utf-8 -*-
import pygame

class Dialog:
    def __init__(self, title, message, buttons, width=400, height=200):
        self.title = title
        self.message = message
        self.buttons = buttons  # список кнопок: [{'text': 'Да', 'action': 'yes'}, ...]
        self.width = width
        self.height = height
        self.result = None
        self.active = True
        
        # Цвета
        self.bg_color = (50, 50, 50, 200)
        self.dialog_color = (30, 30, 30)
        self.border_color = (100, 100, 100)
        self.text_color = (255, 255, 255)
        self.button_color = (70, 70, 70)
        self.button_hover_color = (100, 100, 100)
        self.button_text_color = (255, 255, 255)
        
        # Шрифты
        self.title_font = pygame.font.Font(None, 24)
        self.message_font = pygame.font.Font(None, 18)
        self.button_font = pygame.font.Font(None, 16)
        
        # Позиция диалога (центр экрана)
        self.x = (1200 - width) // 2  # SCREEN_WIDTH
        self.y = (800 - height) // 2   # SCREEN_HEIGHT
        
        # Кнопки
        self.button_rects = []
        self.hovered_button = -1
        self._setup_buttons()
    
    def _setup_buttons(self):
        """Настройка кнопок"""
        # Динамический размер кнопок в зависимости от текста
        button_height = 30
        button_spacing = 10
        
        # Вычисляем ширину каждой кнопки на основе текста
        button_widths = []
        for button in self.buttons:
            text_width = self.button_font.size(button['text'])[0]
            button_width = max(80, text_width + 20)  # Минимум 80px, плюс отступы
            button_widths.append(button_width)
        
        total_width = sum(button_widths) + (len(self.buttons) - 1) * button_spacing
        start_x = self.x + (self.width - total_width) // 2
        button_y = self.y + self.height - 50
        
        self.button_rects = []
        current_x = start_x
        for i, (button, width) in enumerate(zip(self.buttons, button_widths)):
            rect = pygame.Rect(current_x, button_y, width, button_height)
            self.button_rects.append(rect)
            current_x += width + button_spacing
    
    def handle_event(self, event):
        """Обработка событий"""
        if not self.active:
            return None
        
        if event.type == pygame.MOUSEMOTION:
            # Проверяем наведение на кнопки
            mouse_pos = event.pos
            self.hovered_button = -1
            for i, rect in enumerate(self.button_rects):
                if rect.collidepoint(mouse_pos):
                    self.hovered_button = i
                    break
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # ЛКМ
                mouse_pos = event.pos
                for i, rect in enumerate(self.button_rects):
                    if rect.collidepoint(mouse_pos):
                        self.result = self.buttons[i]['action']
                        self.active = False
                        return self.result
        
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                # ESC закрывает диалог с результатом 'cancel'
                self.result = 'cancel'
                self.active = False
                return self.result
            elif event.key == pygame.K_RETURN:
                # Enter нажимает первую кнопку
                if self.buttons:
                    self.result = self.buttons[0]['action']
                    self.active = False
                    return self.result
        
        return None
    
    def draw(self, screen):
        """Отрисовка диалога"""
        if not self.active:
            return
        
        # Полупрозрачный фон
        overlay = pygame.Surface((1200, 800))  # SCREEN_WIDTH, SCREEN_HEIGHT
        overlay.set_alpha(128)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))
        
        # Основной прямоугольник диалога
        dialog_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        pygame.draw.rect(screen, self.dialog_color, dialog_rect)
        pygame.draw.rect(screen, self.border_color, dialog_rect, 2)
        
        # Заголовок
        title_surface = self.title_font.render(self.title, True, self.text_color)
        title_x = self.x + (self.width - title_surface.get_width()) // 2
        title_y = self.y + 15
        screen.blit(title_surface, (title_x, title_y))
        
        # Сообщение (многострочное)
        message_lines = self.message.split('\n')
        line_height = self.message_font.get_height()
        total_text_height = len(message_lines) * line_height
        start_y = self.y + 50
        
        for i, line in enumerate(message_lines):
            line_surface = self.message_font.render(line, True, self.text_color)
            line_x = self.x + (self.width - line_surface.get_width()) // 2
            line_y = start_y + i * line_height
            screen.blit(line_surface, (line_x, line_y))
        
        # Кнопки
        for i, (button, rect) in enumerate(zip(self.buttons, self.button_rects)):
            # Цвет кнопки (с подсветкой при наведении)
            button_color = self.button_hover_color if i == self.hovered_button else self.button_color
            
            pygame.draw.rect(screen, button_color, rect)
            pygame.draw.rect(screen, self.border_color, rect, 1)
            
            # Текст кнопки
            button_text = self.button_font.render(button['text'], True, self.button_text_color)
            text_x = rect.x + (rect.width - button_text.get_width()) // 2
            text_y = rect.y + (rect.height - button_text.get_height()) // 2
            screen.blit(button_text, (text_x, text_y))


class SaveDialog(Dialog):
    """Диалог сохранения игры"""
    def __init__(self, saves_list):
        self.saves_list = saves_list
        self.save_name = ""
        self.selected_save = -1
        self.input_active = True
        
        super().__init__(
            "Сохранить игру",
            "Введите имя сохранения:",
            [
                {'text': 'Сохранить', 'action': 'save'},
                {'text': 'Отмена', 'action': 'cancel'}
            ],
            width=500,
            height=400
        )
        
        # Поле ввода
        self.input_rect = pygame.Rect(self.x + 20, self.y + 80, self.width - 40, 30)
        self.input_color = (60, 60, 60)
        self.input_border_color = (120, 120, 120)
        
        # Список сохранений
        self.saves_rect = pygame.Rect(self.x + 20, self.y + 130, self.width - 40, 200)
        self.save_item_height = 25
        self.scroll_offset = 0
    
    def handle_event(self, event):
        """Обработка событий диалога сохранения"""
        if not self.active:
            return None
        
        if event.type == pygame.KEYDOWN:
            if self.input_active:
                if event.key == pygame.K_BACKSPACE:
                    self.save_name = self.save_name[:-1]
                elif event.key == pygame.K_RETURN:
                    if self.save_name.strip():
                        self.result = {'action': 'save', 'name': self.save_name.strip()}
                        self.active = False
                        return self.result
                elif event.unicode.isprintable():
                    if len(self.save_name) < 30:
                        self.save_name += event.unicode
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # ЛКМ
                mouse_pos = event.pos
                
                # Проверяем клик по полю ввода
                if self.input_rect.collidepoint(mouse_pos):
                    self.input_active = True
                else:
                    self.input_active = False
                
                # Проверяем клик по списку сохранений
                if self.saves_rect.collidepoint(mouse_pos):
                    relative_y = mouse_pos[1] - self.saves_rect.y
                    save_index = (relative_y + self.scroll_offset) // self.save_item_height
                    if 0 <= save_index < len(self.saves_list):
                        self.selected_save = save_index
                        self.save_name = self.saves_list[save_index]['name']
        
        # Обработка кнопок
        result = super().handle_event(event)
        if result == 'save':
            if self.save_name.strip():
                return {'action': 'save', 'name': self.save_name.strip()}
            else:
                return None  # Не закрываем диалог, если имя пустое
        
        return result
    
    def draw(self, screen):
        """Отрисовка диалога сохранения"""
        if not self.active:
            return
        
        # Базовая отрисовка
        super().draw(screen)
        
        # Поле ввода
        input_border_color = (150, 150, 255) if self.input_active else self.input_border_color
        pygame.draw.rect(screen, self.input_color, self.input_rect)
        pygame.draw.rect(screen, input_border_color, self.input_rect, 2)
        
        # Текст в поле ввода
        input_text = self.message_font.render(self.save_name, True, self.text_color)
        screen.blit(input_text, (self.input_rect.x + 5, self.input_rect.y + 5))
        
        # Курсор в поле ввода
        if self.input_active and pygame.time.get_ticks() % 1000 < 500:
            cursor_x = self.input_rect.x + 5 + input_text.get_width()
            cursor_y = self.input_rect.y + 5
            pygame.draw.line(screen, self.text_color, 
                           (cursor_x, cursor_y), 
                           (cursor_x, cursor_y + input_text.get_height()), 1)
        
        # Список сохранений
        pygame.draw.rect(screen, (40, 40, 40), self.saves_rect)
        pygame.draw.rect(screen, self.border_color, self.saves_rect, 1)
        
        # Элементы списка
        for i, save in enumerate(self.saves_list):
            item_y = self.saves_rect.y + i * self.save_item_height - self.scroll_offset
            
            if item_y < self.saves_rect.y - self.save_item_height:
                continue
            if item_y > self.saves_rect.bottom:
                break
            
            item_rect = pygame.Rect(self.saves_rect.x, item_y, 
                                  self.saves_rect.width, self.save_item_height)
            
            # Подсветка выбранного элемента
            if i == self.selected_save:
                pygame.draw.rect(screen, (80, 80, 120), item_rect)
            
            # Текст сохранения
            save_text = f"{save['name']} ({save['updated_at']})"
            text_surface = self.message_font.render(save_text, True, self.text_color)
            screen.blit(text_surface, (item_rect.x + 5, item_rect.y + 2))


class LoadDialog(Dialog):
    """Диалог загрузки игры"""
    def __init__(self, saves_list):
        self.saves_list = saves_list
        self.selected_save = -1
        
        super().__init__(
            "Загрузить игру",
            "Выберите сохранение для загрузки:",
            [
                {'text': 'Загрузить', 'action': 'load'},
                {'text': 'Удалить', 'action': 'delete'},
                {'text': 'Отмена', 'action': 'cancel'}
            ],
            width=500,
            height=400
        )
        
        # Список сохранений
        self.saves_rect = pygame.Rect(self.x + 20, self.y + 80, self.width - 40, 250)
        self.save_item_height = 30
        self.scroll_offset = 0
    
    def handle_event(self, event):
        """Обработка событий диалога загрузки"""
        if not self.active:
            return None
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # ЛКМ
                mouse_pos = event.pos
                
                # Проверяем клик по списку сохранений
                if self.saves_rect.collidepoint(mouse_pos):
                    relative_y = mouse_pos[1] - self.saves_rect.y
                    save_index = (relative_y + self.scroll_offset) // self.save_item_height
                    if 0 <= save_index < len(self.saves_list):
                        self.selected_save = save_index
        
        # Обработка кнопок
        result = super().handle_event(event)
        if result in ['load', 'delete']:
            if self.selected_save >= 0:
                save_name = self.saves_list[self.selected_save]['name']
                return {'action': result, 'name': save_name}
            else:
                return None  # Не закрываем диалог, если ничего не выбрано
        
        return result
    
    def draw(self, screen):
        """Отрисовка диалога загрузки"""
        if not self.active:
            return
        
        # Базовая отрисовка
        super().draw(screen)
        
        # Список сохранений
        pygame.draw.rect(screen, (40, 40, 40), self.saves_rect)
        pygame.draw.rect(screen, self.border_color, self.saves_rect, 1)
        
        if not self.saves_list:
            # Если нет сохранений
            no_saves_text = self.message_font.render("Нет сохранений", True, (150, 150, 150))
            text_x = self.saves_rect.x + (self.saves_rect.width - no_saves_text.get_width()) // 2
            text_y = self.saves_rect.y + (self.saves_rect.height - no_saves_text.get_height()) // 2
            screen.blit(no_saves_text, (text_x, text_y))
            return
        
        # Элементы списка
        for i, save in enumerate(self.saves_list):
            item_y = self.saves_rect.y + i * self.save_item_height - self.scroll_offset
            
            if item_y < self.saves_rect.y - self.save_item_height:
                continue
            if item_y > self.saves_rect.bottom:
                break
            
            item_rect = pygame.Rect(self.saves_rect.x, item_y, 
                                  self.saves_rect.width, self.save_item_height)
            
            # Подсветка выбранного элемента
            if i == self.selected_save:
                pygame.draw.rect(screen, (80, 80, 120), item_rect)
            
            # Информация о сохранении
            save_name = save['name']
            save_date = save['updated_at']
            save_stats = f"Ресурсов: {save['resources_collected']}, Построек: {save['buildings_built']}"
            
            # Название сохранения
            name_surface = self.message_font.render(save_name, True, self.text_color)
            screen.blit(name_surface, (item_rect.x + 5, item_rect.y + 2))
            
            # Дата и статистика
            info_text = f"{save_date} | {save_stats}"
            info_surface = pygame.font.Font(None, 14).render(info_text, True, (180, 180, 180))
            screen.blit(info_surface, (item_rect.x + 5, item_rect.y + 16))


def show_exit_confirmation():
    """Показать диалог подтверждения выхода"""
    return Dialog(
        "Подтверждение выхода",
        "Вы уверены, что хотите выйти?\nНесохраненный прогресс будет потерян!",
        [
            {'text': 'Сохранить и выйти', 'action': 'save_and_exit'},
            {'text': 'Выйти без сохранения', 'action': 'exit'},
            {'text': 'Отмена', 'action': 'cancel'}
        ],
        width=550,  # Увеличиваем ширину
        height=180
    )


def show_overwrite_confirmation(save_name):
    """Показать диалог подтверждения перезаписи"""
    return Dialog(
        "Подтверждение перезаписи",
        f"Сохранение '{save_name}' уже существует.\nПерезаписать его?",
        [
            {'text': 'Да', 'action': 'yes'},
            {'text': 'Нет', 'action': 'no'}
        ],
        width=400,
        height=150
    )