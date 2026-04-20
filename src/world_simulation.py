import sqlite3
import random
import time
import json
from typing import Dict, List, Any, Optional

# Internal relative-friendly imports
import db_manager
import entities
from core.world.sim_manager import SimulationManager
from core.world.map_generator import FractalMapGenerator
from core.world.metabolism import MetabolismManager
from core.world.faction_manager import FactionManager

class WorldSimulation:
    """
    The World Simulation Engine: Manages macro-level autonomous logic.
    Supports LOD (Level of Detail) gating based on player proximity.
    """
    def __init__(self, master_seed: int = 42, initial_time: Dict[str, Any] = None):
        """Initializes the simulation with deterministic generators and managers."""
        self.db_path = db_manager.DB_NAME
        self.generator = FractalMapGenerator(master_seed=master_seed)
        self.sim_manager = SimulationManager(master_seed=master_seed)
        self.faction_manager = FactionManager(self.db_path)
        
        # Hydrate calendar from state if provided
        if initial_time:
            self.sim_manager.calendar.year = initial_time.get("year", 42)
            self.sim_manager.calendar.total_days = initial_time.get("total_days", 1)
            self.sim_manager.calendar.hour = initial_time.get("hour", 12)

    def execute_simulation_pulse(self, player_coord: Optional[entities.WorldCoord] = None):
        """
        Calculates one 'tick' (1 hour) of global world time.
        Orchestrates foundations, factions, and proximity-gated ecology.
        """
        # 1. Advance foundations (Time, Weather, Aether) - GLOBAL
        self.sim_manager.pulse(1)
        
        # 2. Advance Geopolitical Actors - GLOBAL (Abstracted)
        self.faction_manager.pulse()
        
        # 3. Process Metabolism (Biological Ecosystem) - REGIONAL LOD
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            # Use player's region to gate high-detail entity pulses
            region_key = player_coord.to_key() if player_coord else None
            atmos = self.sim_manager.get_atmospheric_state(
                player_coord.gx if player_coord else 5, 
                player_coord.gy if player_coord else 5
            )
            
            self._process_map_chunk_metabolism(cursor, atmos, region_key)
            self._cleanup_stale_data(cursor)
            conn.commit()
        except sqlite3.Error as e:
            print(f"[Sim Error] Biological pulse failed: {e}")
        finally:
            conn.close()

    def get_atmospheric_state(self, gx: int, gy: int) -> Dict[str, Any]:
        """Provides context for chunk generation at a specific coordinate."""
        return self.sim_manager.get_atmospheric_state(gx, gy)

    def _process_map_chunk_metabolism(self, cursor: sqlite3.Cursor, atmos: Dict[str, Any], region_key: Optional[str]):
        """
        Iterates through map chunks. 
        Detailed pulse only for chunks in the player's active region.
        """
        if not region_key:
            # If no player coord (startup/wait), pulse nothing or a random sample
            return

        # Filtering: map_key starts with the regional coordinates gx_gy_cx_cy_rx_ry
        # entities.WorldCoord.to_key() returns exactly this prefix.
        query = "SELECT map_key, data_json FROM map_chunks WHERE map_key LIKE ?"
        cursor.execute(query, (f"{region_key}%",))
        chunks = cursor.fetchall()
        
        if not chunks: return

        for key, data_str in chunks:
            data = json.loads(data_str)
            entities_list = data.get("entities", [])
            
            new_entities = []
            for ent in entities_list:
                updated_ent = MetabolismManager.process_biological_cycle(ent, atmos)
                if "dead" not in updated_ent.get("tags", []):
                    new_entities.append(updated_ent)
                    
                    # Reproduction Check
                    if updated_ent.get("repro_ready"):
                        copy_ent = updated_ent.copy()
                        copy_ent["id"] = f"{updated_ent['id']}_off"
                        del copy_ent["repro_ready"]
                        new_entities.append(copy_ent)
            
            data["entities"] = new_entities
            cursor.execute("UPDATE map_chunks SET data_json = ? WHERE map_key = ?", (json.dumps(data, cls=db_manager.PydanticEncoder), key))

    def _cleanup_stale_data(self, cursor: sqlite3.Cursor):
        """Purges delivered or stalled routes and empty resource nodes."""
        cursor.execute("DELETE FROM trade_routes WHERE caravan_status IN ('Delivered', 'Stalled')")
        cursor.execute("DELETE FROM resource_nodes WHERE remaining_supply <= 0 AND is_renewable = 0")
