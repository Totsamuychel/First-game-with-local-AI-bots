# 🎮 First Game with Local AI Bots

A 2D top-down strategy game built with **Python + Pygame** where AI bots powered by a **locally running LLM via Ollama** compete alongside or against the human player. Bots think, plan strategies, and make real-time decisions using a language model running entirely on your machine — no internet or API keys required.

---

## 📖 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [How It Works](#how-it-works)
- [Project Structure](#project-structure)
- [Game Worlds & Mechanics](#game-worlds--mechanics)
- [Controls](#controls)
- [Resources, Buildings & Equipment](#resources-buildings--equipment)
- [AI Bot System](#ai-bot-system)
- [Installation](#installation)
- [Running the Game](#running-the-game)
- [Configuration & Tweaking](#configuration--tweaking)
- [Requirements](#requirements)

---

## Overview

This is an experimental project combining classic 2D game mechanics with local LLM inference. Each AI-controlled player uses Ollama to query a small language model every few seconds, passing the current game state as a prompt and receiving a strategic decision (`explore`, `build`, `attack`, `switch_world`, or `retreat`). If Ollama is unavailable, bots fall back to a simple rule-based AI automatically.

The game world is split into **three dimensions**: a safe resource-gathering world, a PvP base-building world, and a dangerous dungeon world with unique loot.

---

## Features

- 🤖 **Local LLM AI bots** — powered by Ollama (qwen2.5-coder, gemma2, llama3.2, or any available model)
- 🌍 **3 distinct worlds** — Resource World, Base World (PvP), and Dungeon World
- ⛏️ **5 standard + 4 dungeon resource types** to collect
- 🏗️ **9 building types** — walls, towers, barracks, workshops, portals, shops, and more
- ⚔️ **8 weapons** — from basic sword/bow to legendary dungeon weapons
- 🛡️ **9 armor types** and **18 accessories** with stat bonuses
- 📜 **Quest system** with rewards
- 🎒 **Inventory system** with equipment slots
- 📷 **Scrollable camera** that follows the player
- ⚙️ **Fully configurable** game balance via `game/config.py`

---

## How It Works

### Game Loop (`game/core/engine.py`)

The `Game` class in `engine.py` is the heart of the project. On each frame it:
1. Processes player input (keyboard + mouse)
2. Updates all entities — player, AI bots, resources, buildings, projectiles
3. Calls `ai.make_decision()` for each AI-controlled player
4. Renders everything to the screen via Pygame
5. Manages world switching when a player uses a portal

The entry point `main.py` simply instantiates `Game()` and calls `game.run()`.

### Camera (`game/core/camera.py`)

A simple offset-based camera that centers on the player. All world objects are drawn at `(object.x - camera.x, object.y - camera.y)` so the viewport follows the player across the 2000×1500 world.

### AI Decision Loop (`game/core/ai_player.py`)

This is the most unique part of the project. The `OllamaAI` class:

1. **Checks Ollama availability** on startup and auto-selects the best available model from a priority list:
   ```
   qwen2.5-coder:1.5b → gemma2:2b → gemma2:9b → qwen2.5-coder:7b → llama3.2:1b → llama3.2:3b
   ```
2. **Builds a game-state snapshot** every 2 seconds containing: current world, HP, resources, equipment, nearby enemies/resources, number of teammates and buildings.
3. **Sends a structured prompt** to the local LLM asking it to pick one of 5 actions.
4. **Parses the response** — first looking for an exact keyword match, then scanning for synonyms (e.g. "gather" → `explore`, "fight" → `attack`), and defaulting to `explore` if nothing matches.
5. **Executes the chosen strategy** using one of 5 strategy methods.

If Ollama is not running, `fallback_ai()` takes over with simple rule-based logic (low HP → retreat, low resources → explore, has resources in base world → build).

### Strategy Methods

| Strategy | What the bot does |
|---|---|
| `explore` | Finds the nearest resource or pile and moves toward it |
| `build` | Navigates to the base world and constructs buildings by priority |
| `attack` | Finds the nearest enemy and chases/attacks them |
| `switch_world` | Navigates to the portal and switches dimensions |
| `retreat` | Moves back to the center of the bot's own base |

---

## Project Structure

```
First-game-with-local-AI-bots/
├── main.py                  # Entry point — creates Game() and runs it
├── requirements.txt         # Python dependencies
├── .gitignore
└── game/
    ├── __init__.py
    ├── config.py            # All game constants and balance settings
    ├── core/
    │   ├── engine.py        # Main game loop, rendering, event handling
    │   ├── ai_player.py     # OllamaAI class — LLM-powered bot logic
    │   └── camera.py        # Viewport/camera offset system
    ├── entities/            # Player, bots, projectiles, teammates
    ├── world/
    │   └── buildings.py     # Building classes (Wall, Tower, Portal, etc.)
    ├── ui/                  # HUD, inventory screen, quest panel
    └── utils/               # Helper functions
```

---

## Game Worlds & Mechanics

### 🌿 World 0 — Resource World (PvP disabled)

The safe starting world. Your goal here is to gather resources before heading back to your base.

- Resources spawn in clusters near the world center (configurable radius)
- Piles of resources occasionally contain **teammates** or **weapons**
- Use the **portal** to return to your base world
- No player-vs-player damage in this world

### 🏰 World 1 — Base World (PvP enabled)

Your home base and the competitive battlefield.

- Build and expand your base using collected resources
- Craft weapons and armor at the **Workshop**
- Train soldiers at the **Barracks**
- Defend with **Towers** and **Walls**
- Attack other players' bases
- Build a **Dungeon Portal** to access World 2

### 🌑 World 2 — Dungeon World

A dangerous third dimension with powerful enemies and unique loot.

- Contains 4 exclusive resources: `shadow_essence`, `demon_blood`, `soul_gem`, `void_crystal`
- Used to craft the most powerful weapons (`void_sword`, `soul_staff`) and armor (`void_armor`, `soul_armor`)
- Legendary accessories drop here with no crafting cost

---

## Controls

| Key / Button | Action |
|---|---|
| `WASD` or Arrow Keys | Move player |
| `Left Click` | Place building / Attack / Collect resource |
| `Right Click` | Use weapon ability / Secondary action |
| `E` | Interact with portal (switch worlds) |
| `Space` | Switch mode: Explore → Build → Combat |
| `1` – `5` | Select building type or weapon slot |
| `TAB` | Open / close inventory |
| `ESC` | Quit game |

---

## Resources, Buildings & Equipment

### Resources

| Resource | Color | Where to find |
|---|---|---|
| Wood 🟫 | Brown | Resource World |
| Stone ⬜ | Gray | Resource World |
| Iron 🩶 | Light gray | Resource World |
| Gold 🟡 | Yellow | Resource World |
| Crystal 🟣 | Purple | Resource World |
| Shadow Essence | Dark purple | Dungeon |
| Demon Blood | Dark red | Dungeon |
| Soul Gem | Cyan | Dungeon |
| Void Crystal | Purple-black | Dungeon |

### Building Costs (examples)

| Building | Cost |
|---|---|
| Wall | 3 Wood + 2 Stone |
| Tower | 5 Stone + 3 Iron |
| Workshop | 10 Wood + 8 Iron + 3 Gold |
| Portal | 5 Crystal + 10 Gold |
| Dungeon Portal | 50 Crystal + 30 Gold + 20 Iron |

### Weapons

| Weapon | Damage | Range | Tier |
|---|---|---|---|
| Sword | 25 | 30 | Basic |
| Bow | 15 | 80 | Basic |
| Axe | 35 | 25 | Basic |
| Staff | 40 | 60 | Basic |
| Shadow Blade | 50 | 35 | Dungeon |
| Demon Axe | 60 | 30 | Dungeon |
| Soul Staff | 70 | 70 | Dungeon |
| Void Sword | 80 | 40 | Dungeon |

---

## AI Bot System

### Supported Ollama Models (priority order)

1. `qwen2.5-coder:1.5b` ← recommended (fast, good reasoning)
2. `gemma2:2b`
3. `gemma2:9b`
4. `qwen2.5-coder:7b`
5. `llama3.2:1b`
6. `llama3.2:3b`

The bot auto-detects which models are installed and picks the best one. You can also manually set the model in `ai_player.py`.

### Decision Frequency

Bots query the LLM every **2 seconds** (`decision_cooldown = 2.0`). Between decisions, they continue executing the previous strategy. This keeps the game smooth while still using real AI reasoning.

### LLM Prompt Format

The bot sends a structured text prompt with the game state and a list of valid actions. The model responds with a single word. Low `temperature=0.3` and `num_predict=5` keep responses fast and deterministic.

### Fallback Behavior

If Ollama is not installed or no models are found, the game still runs normally. Each bot uses simple rule-based logic:
- HP < 30 → `retreat`
- In resource world + low resources → `explore`
- In base world + enough resources → `build`
- Default → `explore`

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Totsamuychel/First-game-with-local-AI-bots.git
cd First-game-with-local-AI-bots
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate      # Linux / macOS
venv\Scripts\activate          # Windows
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Ollama and pull a model

Download Ollama from [https://ollama.com](https://ollama.com), then pull at least one model:

```bash
# Recommended — fast and lightweight
ollama pull qwen2.5-coder:1.5b

# Alternatives
ollama pull gemma2:2b
ollama pull llama3.2:1b
```

> **Note:** Ollama is optional. The game runs fine without it using the built-in fallback AI.

---

## Running the Game

```bash
python main.py
```

Make sure Ollama is running in the background before launching if you want LLM-powered bots:

```bash
ollama serve   # Start the Ollama server (usually auto-starts)
```

---

## Configuration & Tweaking

All game balance is centralized in `game/config.py`. Key settings you can change:

| Constant | Default | Effect |
|---|---|---|
| `SCREEN_WIDTH / SCREEN_HEIGHT` | 1200 × 800 | Window size |
| `WORLD_WIDTH / WORLD_HEIGHT` | 2000 × 1500 | Map size |
| `PLAYER_SPEED` | 3 | Human player movement speed |
| `BOT_SPEED` | 2 | AI bot movement speed |
| `PLAYER_MAX_HP` | 100 | Starting HP |
| `INITIAL_RESOURCES` | 150 | Resources spawned at game start |
| `RESOURCE_SPAWN_RATE` | 0.03 | Chance of new resource spawning per frame |
| `TOWER_DAMAGE` | 20 | Damage per tower shot |
| `TOWER_RANGE` | 100 | Tower attack radius |
| `decision_cooldown` (in `ai_player.py`) | 2.0s | How often bots query the LLM |

You can also add new weapon/armor/building types by extending the dictionaries in `config.py` — no code changes needed elsewhere.

---

## Requirements

- Python 3.10+
- `pygame >= 2.5.0`
- `ollama >= 0.1.0` (Python client library)
- `sqlite3` (built into Python stdlib)
- [Ollama](https://ollama.com) desktop app / server (optional but recommended)
- A pulled LLM model (e.g. `qwen2.5-coder:1.5b`) — only needed for AI bots

---

## License

This project is open source. Feel free to fork, mod, and experiment!
