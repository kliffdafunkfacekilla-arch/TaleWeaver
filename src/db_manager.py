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
    Initializes the SQLite database and creates the necessary tables.
    Includes a lightweight migration layer to sync existing schemas.
    """
    os.makedirs(os.path.dirname(DB_NAME), exist_ok=True)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # map_chunks: Stores local area state for the recursive fractal grid.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS map_chunks (
            map_key TEXT PRIMARY KEY,
            data_json TEXT,
            last_visited_clock INTEGER
        )
    ''')
    
    # saved_maps: Stores arbitrary map data (interiors, special locations) keyed by ID.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS saved_maps (
            map_id TEXT PRIMARY KEY, 
            map_data TEXT
        )
    ''')
    
    # map_states: Stores tactical map data.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS map_states (
            map_id TEXT PRIMARY KEY,
            data TEXT
        )
    ''')

    # buildings: Stores settlement infrastructure and production.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS buildings (
            id TEXT PRIMARY KEY,
            settlement_id TEXT,
            type TEXT,
            resource_generated TEXT,
            yield_per_pulse INTEGER
        )
    ''')

    # trade_routes: Stores caravan logic and economic flows.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trade_routes (
            id TEXT PRIMARY KEY,
            source_settlement_id TEXT,
            target_settlement_id TEXT,
            goods_type TEXT,
            caravan_status TEXT
        )
    ''')

    # resource_nodes: Stores harvestable map features.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resource_nodes (
            id TEXT PRIMARY KEY,
            node_type TEXT,
            remaining_supply INTEGER,
            gx INTEGER,
            gy INTEGER,
            is_renewable INTEGER DEFAULT 0,
            regrow_rate REAL DEFAULT 0.0
        )
    ''')

    # factions: High-level tactical agents.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS factions (
            id TEXT PRIMARY KEY,
            name TEXT,
            alignment TEXT,
            tech_level INTEGER DEFAULT 1,
            resources_json TEXT
        )
    ''')

    # settlements: Geographical hubs for factions.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settlements (
            id TEXT PRIMARY KEY,
            faction_id TEXT,
            name TEXT,
            level INTEGER DEFAULT 1,
            gx INTEGER,
            gy INTEGER,
            cx INTEGER,
            cy INTEGER,
            population INTEGER,
            happiness INTEGER DEFAULT 50,
            buildings_json TEXT,
            FOREIGN KEY(faction_id) REFERENCES factions(id)
        )
    ''')

    # --- MIGRATION LAYER ---
    # Ensure factions table has 'resources_json' if it already existed
    try:
        cursor.execute("ALTER TABLE factions ADD COLUMN resources_json TEXT")
    except sqlite3.OperationalError:
        pass # Column already exists
    
    conn.commit()
    conn.close()

def save_map_state(map_id: str, local_state: Dict[str, Any]):
    """Persists a tactical map chunk to the SQL database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    data_json = json.dumps(local_state, cls=PydanticEncoder)
    cursor.execute("INSERT OR REPLACE INTO map_states (map_id, data) VALUES (?, ?)", (map_id, data_json))
    conn.commit()
    conn.close()

def load_map_state(map_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a tactical map chunk from the SQL database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT data FROM map_states WHERE map_id = ?", (map_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return None

def save_chunk(map_key: str, state_data: Dict[str, Any]):
    """Stores a local map chunk's state indexed by its unique fractal key."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    clock = state_data.get("meta", {}).get("clock", 0)
    data_str = json.dumps(state_data, cls=PydanticEncoder)
    
    cursor.execute('''
        INSERT INTO map_chunks (map_key, data_json, last_visited_clock)
        VALUES (?, ?, ?)
        ON CONFLICT(map_key) 
        DO UPDATE SET data_json=excluded.data_json, last_visited_clock=excluded.last_visited_clock
    ''', (map_key, data_str, clock))
    
    conn.commit()
    conn.close()

def load_chunk(map_key: str) -> Optional[Dict[str, Any]]:
    """Loads a previously visited map chunk from the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT data_json FROM map_chunks WHERE map_key=?', (map_key,))
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