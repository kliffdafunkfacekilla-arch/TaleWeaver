import sqlite3
import json
import os
from pydantic import BaseModel

DB_NAME = "state/shatterlands.db"

class PydanticEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle Pydantic models during DB storage."""
    def default(self, obj):
        if isinstance(obj, BaseModel):
            return obj.model_dump()
        return super().default(obj)

def init_db():
    os.makedirs(os.path.dirname(DB_NAME), exist_ok=True)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS map_chunks (
            chunk_x INTEGER,
            chunk_y INTEGER,
            data_json TEXT,
            last_visited_clock INTEGER,
            PRIMARY KEY (chunk_x, chunk_y)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS saved_maps (
            map_id TEXT PRIMARY KEY, 
            map_data TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def save_map_state(map_id: str, state_dict: dict):
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

def load_map_state(map_id: str) -> dict:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT map_data FROM saved_maps WHERE map_id=?', (map_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return json.loads(result[0])
    return None

def save_chunk(chunk_x, chunk_y, state_data):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Handle clock if it's in a nested dict
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

def load_chunk(chunk_x, chunk_y):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT data_json FROM map_chunks WHERE chunk_x=? AND chunk_y=?', (chunk_x, chunk_y))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return json.loads(result[0])
    return None

def reset_world():
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
    init_db()

init_db()