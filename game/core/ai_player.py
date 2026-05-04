import pygame
import math
import random
import time
import ollama
from game.config import *
from game.world.buildings import *

class OllamaAI:
    """AI player based on Ollama"""
    def __init__(self, player_id, model_name="qwen2.5-coder:1.5b"):
        self.player_id = player_id
        self.model_name = model_name
        self.last_decision_time = 0
        self.decision_cooldown = 2.0  
        self.current_strategy = "explore"  # explore, build, attack
        self.target_position = None
        self.ollama_available = self.check_ollama()
        
    def check_ollama(self):
        """Проверить доступность Ollama и выбрать лучшую модель"""
        try:
            models_response = ollama.list()
            print(f"Ollama response: {models_response}")  # Debugging
            
            if hasattr(models_response, 'models'):
                available_models = [model.model for model in models_response.models]
            elif 'models' in models_response:
                available_models = [model['name'] for model in models_response['models']]
            else:
                available_models = []
            
            print(f"Доступные модели: {available_models}")  
            
            # Priority of models for game AI (from best to worst)
            preferred_models = [
                "qwen2.5-coder:1.5b",
                "gemma2:2b", 
                "gemma2:9b",
                "qwen2.5-coder:7b",
                "llama3.2:1b",
                "llama3.2:3b"
            ]
            
            # We select the first available model from the priority list
            for model in preferred_models:
                if model in available_models:
                    self.model_name = model
                    print(f"ИИ игрок {self.player_id} использует модель: {model}")
                    return True
            
            # If none of the preferred models are found, we use the first available one.
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
        """Get a description of the current game state"""
        # Check for the presence of the equipped attribute (for compatibility with old saves)
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
        
        # НFind nearby objects
        nearby_resources = []
        nearby_enemies = []
        
        if game.current_world == WORLD_RESOURCE:
            for resource in game.resources[:5]: 
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
        """Make a decision based on AI"""
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
                    "temperature": 0.3,  
                    "num_predict": 5,    
                    "top_p": 0.9,        
                    "repeat_penalty": 1.1 
                }
            )
            
            decision = response['response'].strip().lower()
            
            # Smart response processing - searching for keywords
            valid_actions = ['explore', 'build', 'attack', 'switch_world', 'retreat']
            
            # A direct match
            if decision in valid_actions:
                self.current_strategy = decision
            else:
                # Search for keywords in the answer
                found_action = None
                for action in valid_actions:
                    if action in decision:
                        found_action = action
                        break
                
                if found_action:
                    self.current_strategy = found_action
                else:
                    # Intelligent interpretation
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
                        self.current_strategy = "explore"  
                
                print(f"ИИ {self.player_id}: '{decision}' → {self.current_strategy}")
                
        except Exception as e:
            print(f"Ошибка ИИ: {e}")
            return self.fallback_ai(game, player)
        
        return self.execute_current_strategy(game, player)
    
    def fallback_ai(self, game, player):
        """Simple AI without Ollama"""
        # Simple logic as a reserve
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
        """Execute the current strategy"""
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
        """Research strategy"""
        if game.current_world == WORLD_BASE:
            # Switch to the world of resources
            for building in game.buildings[self.player_id]:
                if isinstance(building, Portal) and building.can_use(player):
                    return {"action": "use_portal"}
        
        # Find the nearest resource
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
        """Construction Strategy"""
        if game.current_world == WORLD_RESOURCE:
            # switch to the base world
            distance = math.sqrt((player.x - RESOURCE_SPAWN_CENTER_X)**2 + (player.y - RESOURCE_SPAWN_CENTER_Y)**2)
            if distance < 60:
                return {"action": "use_portal"}
            else:
                return {
                    "action": "move_to",
                    "target": {"x": RESOURCE_SPAWN_CENTER_X, "y": RESOURCE_SPAWN_CENTER_Y}
                }
        
        # Choose what to build
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
        """Attack strategy"""
        if not player.equipped['weapon']:
            return self.build_strategy(game, player)
        
        # Find the nearest enemy
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
        """Strategy for changing the world"""
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
        """Retreat strategy"""
        base = game.player_bases[self.player_id]
        base_center_x = base['x'] + base['width'] // 2
        base_center_y = base['y'] + base['height'] // 2
        
        return {
            "action": "move_to",
            "target": {"x": base_center_x, "y": base_center_y}
        }

