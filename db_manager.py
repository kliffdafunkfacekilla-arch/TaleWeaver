import sqlite3
import json
import os

# Consolidated Database Path for robust global consistency
DB_NAME = "state/shatterlands.db"

def init_db():
    os.makedirs(os.path.dirname(DB_NAME), exist_ok=True)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Core World Map (Macro)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS layer4_macro_map (
            coord_id TEXT PRIMARY KEY,
            biome TEXT,
            faction TEXT,
            location TEXT,
            chaos_level INTEGER DEFAULT 0,
            elevation INTEGER DEFAULT 0,
            resource_wealth INTEGER DEFAULT 50,
            fractal_dna TEXT
        )
    ''')

    # LOCAL MAP CHUNKS (THE DIORAMA STATE)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS map_chunks (
            chunk_x INTEGER,
            chunk_y INTEGER,
            data_json TEXT,
            last_visited_clock INTEGER,
            PRIMARY KEY (chunk_x, chunk_y)
        )
    ''')

    # Add migration for resource_wealth/chaos_level if they didn't exist
    cursor.execute("PRAGMA table_info(layer4_macro_map)")
    existing_cols = [col[1] for col in cursor.fetchall()]
    if 'resource_wealth' not in existing_cols:
        cursor.execute("ALTER TABLE layer4_macro_map ADD COLUMN resource_wealth INTEGER DEFAULT 50")
    if 'chaos_level' not in existing_cols:
        cursor.execute("ALTER TABLE layer4_macro_map ADD COLUMN chaos_level INTEGER DEFAULT 0")

    # Add migration for new 4X tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cursor.fetchall()]
    if 'buildings' not in tables:
        cursor.execute('CREATE TABLE settlements (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, x INTEGER, y INTEGER, happiness INTEGER DEFAULT 70, population INTEGER DEFAULT 100)')
        cursor.execute('CREATE TABLE buildings (id INTEGER PRIMARY KEY AUTOINCREMENT, settlement_id INTEGER, building_type TEXT, defense_bonus INTEGER DEFAULT 0, resource_generated TEXT, yield_per_pulse INTEGER, FOREIGN KEY(settlement_id) REFERENCES settlements(id))')
    if 'resource_nodes' not in tables:
        cursor.execute('CREATE TABLE resource_nodes (id INTEGER PRIMARY KEY AUTOINCREMENT, x INTEGER, y INTEGER, resource_type TEXT, remaining_supply INTEGER)')
    if 'trade_routes' not in tables:
        cursor.execute('CREATE TABLE trade_routes (id INTEGER PRIMARY KEY AUTOINCREMENT, source_settlement_id INTEGER, target_settlement_id INTEGER, transport_tech TEXT, goods_type TEXT, caravan_status TEXT DEFAULT \'In Transit\', FOREIGN KEY(source_settlement_id) REFERENCES settlements(id), FOREIGN KEY(target_settlement_id) REFERENCES settlements(id))')
    if 'weather_fronts' not in tables:
        cursor.execute('CREATE TABLE weather_fronts (id INTEGER PRIMARY KEY AUTOINCREMENT, x FLOAT, y FLOAT, storm_type TEXT, intensity INTEGER, lifespan INTEGER DEFAULT 5)')
    
    conn.commit()
    conn.close()

def reset_world():
    """Wipes all persistent data and re-initializes the database."""
    print("[DATABASE] Resetting world state...")
    if os.path.exists(DB_NAME):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = cursor.fetchall()
        for table in tables:
            cursor.execute(f"DROP TABLE {table[0]}")
        conn.commit()
        conn.close()
    
    if os.path.exists("local_map_state.json"):
        os.remove("local_map_state.json")
        
    init_db()
    print("[DATABASE] World re-initialized.")

def save_chunk(x, y, state):
    """Saves a local map chunk to the persistent vault."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    data = json.dumps(state)
    clock = state.get("local_map_state", {}).get("meta", {}).get("clock", 0)
    cursor.execute('''
        INSERT OR REPLACE INTO map_chunks (chunk_x, chunk_y, data_json, last_visited_clock)
        VALUES (?, ?, ?, ?)
    ''', (x, y, data, clock))
    conn.commit()
    conn.close()

def load_chunk(x, y):
    """Loads a local map chunk from the persistent vault."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT data_json FROM map_chunks WHERE chunk_x = ? AND chunk_y = ?", (x, y))
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return None

def get_macro_cell(x, y):
    """Retrieves the macro-level world state for a specific L4 coordinate."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT biome, chaos_level, fractal_dna FROM layer4_macro_map WHERE coord_id = ?", (f"{x},{y}",))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"biome": row[0], "chaos": row[1], "dna": row[2]}
    return None

if __name__ == "__main__":
    init_db()