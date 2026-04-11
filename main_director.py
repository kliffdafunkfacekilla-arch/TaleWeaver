import sqlite3
import json
import random
from pydantic_ai import Agent, RunContext
from dataclasses import dataclass

# ============================================================
# 1. CONFIGURATION
# ============================================================
# Connect directly via string format for Pydantic-AI 1.70.0
# Using the q3_K_L model that fits perfectly in your VRAM
ollama_model = "ollama:llama3.1:8b-instruct-q3_K_L"

@dataclass
class GameDeps:
    db_path: str = "shatterlands.db"

# ============================================================
# 2. THE DIRECTOR AGENT
# ============================================================
director = Agent(
    model=ollama_model,
    deps_type=GameDeps,
    system_prompt=(
        "You are the GM of the Shatterlands. You are grounded by a unified SQLite database. "
        "The world is corrupted by Chaos Magic. NPCs, animals, and plants move and react. "
        "\n\nCRITICAL DIRECTIVES:"
        "\n1. ALWAYS use 'get_world_state' first to understand the current scene and time."
        "\n2. For combat/actions: Use 'roll_dice' to determine success, then 'update_map_token' to apply damage/movement."
        "\n3. Use 'simulate_time' to advance the world clock based on player actions (e.g., 1 min for combat, 60 mins for resting)."
        "\n4. NEVER output raw JSON, tool syntax, or internal logic to the player."
        "\n5. ALWAYS respond with immersive, natural language narrative describing the outcome."
    )
)

# ============================================================
# 3. DATABASE UTILITIES
# ============================================================
def query_db(db_path, query, params=(), fetchone=False):
    with sqlite3.connect(db_path, timeout=10) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchone() if fetchone else cursor.fetchall()

def update_db(db_path, query, params=()):
    with sqlite3.connect(db_path, timeout=10) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()

# ============================================================
# 4. SIMULATION & DIRECTOR TOOLS
# ============================================================

@director.tool
def get_world_state(ctx: RunContext[GameDeps]) -> str:
    """Retrieves the current Map, Quest, Players, and Time data."""
    states = query_db(ctx.deps.db_path, "SELECT key, value FROM state")
    return "\n".join([f"[{s[0].upper()}]: {s[1]}" for s in states])

@director.tool
def roll_dice(ctx: RunContext[GameDeps], sides: int, bonus: int = 0) -> str:
    """Rolls a die (e.g., 20) and adds a bonus. Use for all combat and skill checks."""
    roll = random.randint(1, sides)
    total = roll + bonus
    return f"Rolled {roll} + {bonus} = {total}"

@director.tool
def simulate_time(ctx: RunContext[GameDeps], minutes_passed: int) -> str:
    """Updates the world clock and triggers environmental changes/resource depletion."""
    result = query_db(ctx.deps.db_path, "SELECT value FROM state WHERE key='world_time'", fetchone=True)
    current_time = int(result[0]) if result else 0
    new_time = current_time + minutes_passed
    update_db(ctx.deps.db_path, "UPDATE state SET value=? WHERE key='world_time'", (str(new_time),))

    # Chaos Corruption Pulse (Simulate random world reaction)
    corruption_event = ""
    if random.random() < (minutes_passed / 600): # 10% chance per hour
        corruption_event = " | WARNING: A Chaos surge has mutated a nearby resource."

    return f"Time advanced by {minutes_passed} mins. Total game time: {new_time} mins.{corruption_event}"

@director.tool
def update_map_token(ctx: RunContext[GameDeps], name: str, hp: int = None, x: int = None, y: int = None) -> str:
    """Updates a token's HP or Position in the database map."""
    result = query_db(ctx.deps.db_path, "SELECT value FROM state WHERE key='map'", fetchone=True)
    if not result: return "Map state not found."
    map_data = json.loads(result[0])

    found = False
    for t in map_data['tokens']:
        if t['name'].lower() == name.lower():
            found = True
            if hp is not None: t['hp'] = hp
            if x is not None and y is not None: t['pos'] = [x, y]

    if found:
        update_db(ctx.deps.db_path, "UPDATE state SET value=? WHERE key='map'", (json.dumps(map_data),))
        return f"Updated {name} in the unified database."
    return f"Token '{name}' not found."

# ============================================================
# 5. GAME ENGINE
# ============================================================
if __name__ == "__main__":
    print("\n" + "="*40)
    print("  UNIFIED SHATTERLANDS SIMULATOR: ONLINE")
    print("="*40 + "\n")

    deps = GameDeps()

    while True:
        p_input = input("Player: ")
        if p_input.lower() in ["exit", "quit"]: break

        try:
            result = director.run_sync(p_input, deps=deps)
            
            # The Ultimate Fix: Dynamically extract the text response
            # regardless of how Pydantic-AI packages it.
            if hasattr(result, 'data'):
                final_text = result.data
            elif hasattr(result, 'output'):
                final_text = result.output
            elif hasattr(result, 'content'):
                final_text = result.content
            else:
                final_text = str(result)
                
            print(f"\nDirector: {final_text}\n")
            
        except Exception as e:
            print(f"\n[SYSTEM ERROR]: {e}\n")