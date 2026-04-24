"""
Система базы данных для сохранения игры
"""
# -*- coding: utf-8 -*-
import sqlite3
import json
import os
from datetime import datetime

class GameDatabase:
    def __init__(self, db_path="game_saves.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица сохранений
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS saves (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                save_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                game_data TEXT NOT NULL,
                screenshot BLOB
            )
        ''')
        
        # Таблица настроек
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')
        
        # Таблица статистики
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                save_id INTEGER,
                play_time INTEGER DEFAULT 0,
                resources_collected INTEGER DEFAULT 0,
                buildings_built INTEGER DEFAULT 0,
                enemies_killed INTEGER DEFAULT 0,
                FOREIGN KEY (save_id) REFERENCES saves (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_game(self, save_name, game_data, screenshot=None, overwrite=False):
        """Сохранить игру"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Проверяем, существует ли сохранение с таким именем
            cursor.execute("SELECT id FROM saves WHERE save_name = ?", (save_name,))
            existing_save = cursor.fetchone()
            
            if existing_save and not overwrite:
                conn.close()
                return False, "Сохранение с таким именем уже существует"
            
            game_data_json = json.dumps(game_data, ensure_ascii=False, indent=2)
            
            if existing_save:
                # Обновляем существующее сохранение
                cursor.execute('''
                    UPDATE saves 
                    SET game_data = ?, updated_at = CURRENT_TIMESTAMP, screenshot = ?
                    WHERE save_name = ?
                ''', (game_data_json, screenshot, save_name))
                save_id = existing_save[0]
            else:
                # Создаем новое сохранение
                cursor.execute('''
                    INSERT INTO saves (save_name, game_data, screenshot)
                    VALUES (?, ?, ?)
                ''', (save_name, game_data_json, screenshot))
                save_id = cursor.lastrowid
            
            # Обновляем статистику
            self._update_statistics(cursor, save_id, game_data)
            
            conn.commit()
            conn.close()
            return True, "Игра успешно сохранена"
            
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, f"Ошибка сохранения: {str(e)}"
    
    def load_game(self, save_name):
        """Загрузить игру"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT game_data, updated_at FROM saves 
                WHERE save_name = ?
            ''', (save_name,))
            
            result = cursor.fetchone()
            if result:
                game_data = json.loads(result[0])
                updated_at = result[1]
                conn.close()
                return True, game_data, updated_at
            else:
                conn.close()
                return False, None, None
                
        except Exception as e:
            conn.close()
            return False, None, str(e)
    
    def get_saves_list(self):
        """Получить список всех сохранений"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT s.save_name, s.created_at, s.updated_at, 
                       st.play_time, st.resources_collected, st.buildings_built
                FROM saves s
                LEFT JOIN statistics st ON s.id = st.save_id
                ORDER BY s.updated_at DESC
            ''')
            
            saves = []
            for row in cursor.fetchall():
                saves.append({
                    'name': row[0],
                    'created_at': row[1],
                    'updated_at': row[2],
                    'play_time': row[3] or 0,
                    'resources_collected': row[4] or 0,
                    'buildings_built': row[5] or 0
                })
            
            conn.close()
            return saves
            
        except Exception as e:
            conn.close()
            return []
    
    def delete_save(self, save_name):
        """Удалить сохранение"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Получаем ID сохранения
            cursor.execute("SELECT id FROM saves WHERE save_name = ?", (save_name,))
            save_id = cursor.fetchone()
            
            if save_id:
                # Удаляем статистику
                cursor.execute("DELETE FROM statistics WHERE save_id = ?", (save_id[0],))
                # Удаляем сохранение
                cursor.execute("DELETE FROM saves WHERE save_name = ?", (save_name,))
                
                conn.commit()
                conn.close()
                return True, "Сохранение удалено"
            else:
                conn.close()
                return False, "Сохранение не найдено"
                
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, f"Ошибка удаления: {str(e)}"
    
    def _update_statistics(self, cursor, save_id, game_data):
        """Обновить статистику игры"""
        # Подсчитываем статистику из данных игры
        total_resources = 0
        total_buildings = 0
        
        # Подсчет ресурсов у всех игроков
        for player in game_data.get('players', []):
            for resource_type, amount in player.get('resources', {}).items():
                total_resources += amount
        
        # Подсчет построек у всех игроков
        for player_id, buildings in game_data.get('buildings', {}).items():
            total_buildings += len(buildings)
        
        # Обновляем или создаем запись статистики
        cursor.execute('''
            INSERT OR REPLACE INTO statistics 
            (save_id, resources_collected, buildings_built)
            VALUES (?, ?, ?)
        ''', (save_id, total_resources, total_buildings))
    
    def get_setting(self, key, default=None):
        """Получить настройку"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return json.loads(result[0])
            return default
            
        except Exception:
            conn.close()
            return default
    
    def set_setting(self, key, value):
        """Установить настройку"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            value_json = json.dumps(value)
            cursor.execute('''
                INSERT OR REPLACE INTO settings (key, value)
                VALUES (?, ?)
            ''', (key, value_json))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception:
            conn.rollback()
            conn.close()
            return False
    
    def auto_save(self, game_data, slot_name="autosave"):
        """Автосохранение"""
        return self.save_game(slot_name, game_data, overwrite=True)
    
    def get_quick_saves(self):
        """Получить быстрые сохранения"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT save_name, updated_at FROM saves 
                WHERE save_name LIKE 'quicksave_%' OR save_name = 'autosave'
                ORDER BY updated_at DESC
                LIMIT 5
            ''')
            
            saves = []
            for row in cursor.fetchall():
                saves.append({
                    'name': row[0],
                    'updated_at': row[1]
                })
            
            conn.close()
            return saves
            
        except Exception:
            conn.close()
            return []