import sqlite3
import json
import os
from pydantic import BaseModel
from typing import Dict, Any, Optional

DB_NAME = "state/shatterlands.db"

class PydanticEncoder(json.JSONEncoder):
    """
    Custom JSON encoder to handle Pydantic models during database storage.
    Automatically converts BaseModel instances via model_dump().
    """
    def default(self, obj):
        if isinstance(obj, BaseModel):
            return obj.model_dump()
        return super().default(obj)

def init_db():
    """
    Initializes the SQLite database and creates the necessary tables 
    for persistent map chunk and macro-world state storage.
    """
    os.makedirs(os.path.dirname(DB_NAME), exist_ok=True)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # map_chunks: Stores local area state for the 100x100 global grid.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS map_chunks (
            chunk_x INTEGER,
            chunk_y INTEGER,
            data_json TEXT,
            last_visited_clock INTEGER,
            PRIMARY KEY (chunk_x, chunk_y)
        )
    ''')
    
    # saved_maps: Stores arbitrary map data (interiors, special locations) keyed by ID.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS saved_maps (
            map_id TEXT PRIMARY KEY, 
            map_data TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def save_map_state(map_id: str, state_dict: dict):
    """Saves a standalone map state (e.g., a dungeon or interior) to the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    data_str = json.dumps(state_dict, cls=PydanticEncoder)
    
    cursor.execute('''
        INSERT INTO saved_maps (map_id, map_data)
        VALUES (?, ?)
        ON CONFLICT(map_id) DO UPDATE SET map_data=excluded.map_data
    ''', (map_id, data_str))
    
    conn.commit()
    conn.close()

def load_map_state(map_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a specific map state by its unique ID."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT map_data FROM saved_maps WHERE map_id=?', (map_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return json.loads(result[0])
    return None

def save_chunk(chunk_x: int, chunk_y: int, state_data: Dict[str, Any]):
    """Stores a local map chunk's state indexed by its global grid coordinates."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    clock = state_data.get("meta", {}).get("clock", 0)
    data_str = json.dumps(state_data, cls=PydanticEncoder)
    
    cursor.execute('''
        INSERT INTO map_chunks (chunk_x, chunk_y, data_json, last_visited_clock)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(chunk_x, chunk_y) 
        DO UPDATE SET data_json=excluded.data_json, last_visited_clock=excluded.last_visited_clock
    ''', (chunk_x, chunk_y, data_str, clock))
    
    conn.commit()
    conn.close()

def load_chunk(chunk_x: int, chunk_y: int) -> Optional[Dict[str, Any]]:
    """Loads a previously visited map chunk from the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT data_json FROM map_chunks WHERE chunk_x=? AND chunk_y=?', (chunk_x, chunk_y))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return json.loads(result[0])
    return None

def reset_world():
    """Wipes the database file entirely to start a fresh simulation."""
    if os.path.exists(DB_NAME):
        try:
            os.remove(DB_NAME)
        except PermissionError:
            print("[Warning] Database file is locked. Manual reset required.")
    init_db()

# Ensure DB is initialized on module load
init_db()