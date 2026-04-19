import sqlite3
import json
import os

# Consolidated Database Path for robust global consistency
DB_NAME = os.path.abspath(os.path.join(os.path.dirname(__file__), "state/shatterlands.db"))

def init_db():
    os.makedirs(os.path.dirname(DB_NAME), exist_ok=True)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # GLOBAL_META: Tracks world-state flags and the celestial clock
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS global_meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

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

    # FACTIONS & DIPLOMACY
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS factions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            wealth INTEGER DEFAULT 1000,
            influence INTEGER DEFAULT 50,
            ideology TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS faction_relations (
            faction_a INTEGER,
            faction_b INTEGER,
            relationship INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Neutral',
            PRIMARY KEY (faction_a, faction_b)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS faction_operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            origin_id INTEGER,
            target_id INTEGER,
            op_type TEXT,
            status TEXT DEFAULT 'Active',
            evidence_level INTEGER DEFAULT 0,
            FOREIGN KEY(origin_id) REFERENCES factions(id),
            FOREIGN KEY(target_id) REFERENCES factions(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS player_reputation (
            faction_id INTEGER PRIMARY KEY,
            value INTEGER DEFAULT 0,
            tier TEXT DEFAULT 'Neutral',
            FOREIGN KEY(faction_id) REFERENCES factions(id)
        )
    ''')

    # Add migration checks
    cursor.execute("PRAGMA table_info(layer4_macro_map)")
    existing_cols = [col[1] for col in cursor.fetchall()]
    if 'resource_wealth' not in existing_cols:
        cursor.execute("ALTER TABLE layer4_macro_map ADD COLUMN resource_wealth INTEGER DEFAULT 50")
    if 'chaos_level' not in existing_cols:
        cursor.execute("ALTER TABLE layer4_macro_map ADD COLUMN chaos_level INTEGER DEFAULT 0")

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cursor.fetchall()]
    if 'settlements' not in tables:
        cursor.execute('CREATE TABLE settlements (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, x INTEGER, y INTEGER, happiness INTEGER DEFAULT 70, population INTEGER DEFAULT 100, faction_id INTEGER, FOREIGN KEY(faction_id) REFERENCES factions(id))')
    
    # Check for faction_id in settlements (Migration)
    cursor.execute("PRAGMA table_info(settlements)")
    settlement_cols = [col[1] for col in cursor.fetchall()]
    if 'faction_id' not in settlement_cols:
        cursor.execute("ALTER TABLE settlements ADD COLUMN faction_id INTEGER")

    if 'buildings' not in tables:
        cursor.execute('CREATE TABLE buildings (id INTEGER PRIMARY KEY AUTOINCREMENT, settlement_id INTEGER, building_type TEXT, defense_bonus INTEGER DEFAULT 0, resource_generated TEXT, yield_per_pulse INTEGER, durability INTEGER DEFAULT 100, FOREIGN KEY(settlement_id) REFERENCES settlements(id))')
    
    if 'resource_nodes' not in tables:
        cursor.execute('CREATE TABLE resource_nodes (id INTEGER PRIMARY KEY AUTOINCREMENT, x INTEGER, y INTEGER, resource_type TEXT, remaining_supply INTEGER)')
    if 'trade_routes' not in tables:
        cursor.execute('CREATE TABLE trade_routes (id INTEGER PRIMARY KEY AUTOINCREMENT, source_settlement_id INTEGER, target_settlement_id INTEGER, transport_tech TEXT, goods_type TEXT, caravan_status TEXT DEFAULT \'In Transit\', FOREIGN KEY(source_settlement_id) REFERENCES settlements(id), FOREIGN KEY(target_settlement_id) REFERENCES settlements(id))')
    if 'weather_fronts' not in tables:
        cursor.execute('CREATE TABLE weather_fronts (id INTEGER PRIMARY KEY AUTOINCREMENT, x FLOAT, y FLOAT, storm_type TEXT, intensity INTEGER, lifespan INTEGER DEFAULT 5)')
    
    conn.commit()
    conn.close()

def reset_world():
    if os.path.exists(DB_NAME):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = cursor.fetchall()
        for table in tables: cursor.execute(f"DROP TABLE {table[0]}")
        conn.commit(); conn.close()
    if os.path.exists("local_map_state.json"): os.remove("local_map_state.json")
    if os.path.exists("local_map_state.lock"): os.remove("local_map_state.lock")
    init_db()

def save_chunk(x, y, state):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    data = json.dumps(state)
    clock = state.get("local_map_state", {}).get("meta", {}).get("clock", 0)
    cursor.execute('INSERT OR REPLACE INTO map_chunks (chunk_x, chunk_y, data_json, last_visited_clock) VALUES (?, ?, ?, ?)', (x, y, data, clock))
    conn.commit(); conn.close()

def load_chunk(x, y):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT data_json FROM map_chunks WHERE chunk_x = ? AND chunk_y = ?", (x, y))
    row = cursor.fetchone()
    conn.close()
    return json.loads(row[0]) if row else None

def get_macro_cell(x, y):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT biome, chaos_level, fractal_dna FROM layer4_macro_map WHERE coord_id = ?", (f"{x},{y}",))
    row = cursor.fetchone()
    conn.close()
    return {"biome": row[0], "chaos": row[1], "dna": row[2]} if row else None

if __name__ == "__main__":
    init_db()