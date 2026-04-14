import sqlite3
import json
import os

DB_NAME = "state/shatterlands.db"

def init_db():
    """Creates the vault for the world simulation if it doesn't exist."""
    # Ensure directory exists
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
    
    # TABLE 3: Map Persistence (Stores dormant maps to prevent memory bloat)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS saved_maps (
            map_id TEXT PRIMARY KEY, 
            map_data TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def save_map_state(map_id: str, state_dict: dict):
    """Saves a map state to the persistent database using UPSERT logic."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    data_str = json.dumps(state_dict)
    
    # Using the requested ON CONFLICT UPSERT logic
    cursor.execute('''
        INSERT INTO saved_maps (map_id, map_data)
        VALUES (?, ?)
        ON CONFLICT(map_id) DO UPDATE SET map_data=excluded.map_data
    ''', (map_id, data_str))
    
    conn.commit()
    conn.close()

def load_map_state(map_id: str) -> dict:
    """Retrieves a saved map state from the database. Returns None if not found."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT map_data FROM saved_maps WHERE map_id=?', (map_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return json.loads(result[0])
    return None

def save_chunk(chunk_x, chunk_y, state_data):
    """Packages the current map state and saves it into the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Extract the clock time from the root meta
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

def reset_world():
    """Wipes the database for a New Game."""
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
    init_db()

# Run this once when the file is imported to ensure the DB exists
init_db()