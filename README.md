# Ostraka: Aether & Iron
**A Grim-Steampunk RPG Simulation Engine**

Ostraka is a high-performance, asynchronous RPG engine built with Python and Pygame. It utilizes a "Dual-State" architecture that separates deterministic tactical physics from non-deterministic AI-driven narration and quest generation.

## 🏗️ Architecture
The engine follows a strict 4-step pipeline:
1.  **Intent Resolution**: Translates player input into structural JSON actions.
2.  **Deterministic Engine**: Calculates physics, combat results, and world changes via the B.R.U.T.A.L Engine logic.
3.  **Narrative Weaver**: An asynchronous AI pipeline (powered by Ollama/Llama 3.1) that provides gritty, immersive descriptions of events.
4.  **World Simulation**: A macro-level autonomous layer handling trade routes, resource decay, and faction expansion via SQLite.

## 🛠️ Key Technologies
- **Language**: Python 3.10+
- **Rendering**: Pygame (Tactical Grid & UI)
- **Data Modeling**: Pydantic (Strict type-safety and serialization)
- **Storage**: SQLite3 (Grid-based map chunks and campaign persistence)
- **AI Backend**: Ollama (Asynchronous narrative and quest generation)

## 📁 Repository Structure
- `src/`: Consolidated source code for the engine, entities, actions, and UI.
- `data/`: Static assets, item/skill databases, and campaign saves.
- `state/`: Persistent world state (SQLite database and local JSON cache).
- `tests/`: Automated and manual test scripts.
- `run_game.py`: The main entry point for the application.

## 🚀 Getting Started
1. Ensure [Ollama](https://ollama.com/) is running locally with `llama3.1:8b-instruct-q3_K_L`.
2. Install dependencies: `pip install pygame aiohttp pydantic`
3. Run the game: `python run_game.py`

## ⚔️ Mechanics: B.R.U.T.A.L Engine
The **B.R.U.T.A.L Engine** (Biometric Real-time Universal Tactical Action Logic) focuses on resource management:
- **Beats**: Every turn, entities receive Move, Stamina, and Focus beats.
- **Attrition**: Damage isn't just HP loss; it triggers Trauma (Bleeding, Maimed) that impacts tactical performance.
- **Precision**: Actions are resolved via d20 stat checks with situational Advantage/Disadvantage.
