import sqlite3
import json
import os

# Consolidated Database Path for robust global consistency
DB_NAME = "state/shatterlands.db"

def init_db():
    """Creates the vault for the world simulation if it doesn't exist."""
    os.makedirs(os.path.dirname(DB_NAME), exist_ok=True)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # TABLE 1: The World Map (Stores every chunk Jax visits)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS map_chunks (
            chunk_x INTEGER,
            chunk_y INTEGER,
            data_json TEXT,
            last_visited_clock INTEGER,
            PRIMARY KEY (chunk_x, chunk_y)
        )
    ''')
    
    # TABLE 2: Global Metadata (The Cosmic Clock, Faction Reputations, etc.)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS global_meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # TABLE 3: Lore Entries (Aligned with World Builder)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lore_entries (
            title TEXT PRIMARY KEY,
            category TEXT,
            content TEXT,
            parameters TEXT
        )
    ''')

    # TABLE 4: Layer 4 Macro Map (The Overworld Grid)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS layer4_macro_map (
            coord_id TEXT PRIMARY KEY,
            biome TEXT,
            faction TEXT,
            location TEXT,
            chaos_level INTEGER,
            elevation INTEGER DEFAULT 0
        )
    ''')
    # Migration: add elevation column to pre-existing databases
    cursor.execute("PRAGMA table_info(layer4_macro_map)")
    existing_cols = [col[1] for col in cursor.fetchall()]
    if 'elevation' not in existing_cols:
        cursor.execute("ALTER TABLE layer4_macro_map ADD COLUMN elevation INTEGER DEFAULT 0")
    
    conn.commit()
    conn.close()

def save_chunk(chunk_x, chunk_y, state_data):
    """Packages the current map state and saves it into the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Extract the clock time so we know exactly when Jax was last here
    clock = state_data.get("meta", {}).get("clock", 0)
    data_str = json.dumps(state_data)
    
    # UPSERT: Insert it if it's new, update it if it already exists
    cursor.execute('''
        INSERT INTO map_chunks (chunk_x, chunk_y, data_json, last_visited_clock)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(chunk_x, chunk_y) 
        DO UPDATE SET data_json=excluded.data_json, last_visited_clock=excluded.last_visited_clock
    ''', (chunk_x, chunk_y, data_str, clock))
    
    conn.commit()
    conn.close()

def load_chunk(chunk_x, chunk_y):
    """Retrieves a specific map chunk from the database. Returns None if unexplored."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('SELECT data_json FROM map_chunks WHERE chunk_x=? AND chunk_y=?', (chunk_x, chunk_y))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return json.loads(result[0])
    return None

def get_macro_cell(x, y):
    """Retrieves macro map data for a specific coordinate from Layer 4."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT biome, faction, location, chaos_level, elevation FROM layer4_macro_map WHERE coord_id=?', (f"{x},{y}",))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"biome": row[0], "faction": row[1], "location": row[2], "chaos_level": row[3], "elevation": row[4] if row[4] is not None else 0}
    return None

def reset_world():
    """Wipes the database for a New Game."""
    if os.path.exists(DB_NAME):
        # We only remove the DB file itself, but keep the directory
        os.remove(DB_NAME)
    init_db()

# Run this once when the file is imported to ensure the DB exists
init_db()