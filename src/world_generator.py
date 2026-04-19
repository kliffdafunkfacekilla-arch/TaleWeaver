import random
import sqlite3
import json
from typing import Dict, List, Any, Tuple

# Internal relative-friendly imports
import db_manager

class WorldGenerator:
    """
    The World Generator: Responsible for the initial procedural generation 
    of the 100x100 global map grid.
    Distributes biomes, resource nodes, and faction influence across the Shatterlands.
    """
    def __init__(self, seed: int = 42):
        """Initializes the generator with a deterministic seed."""
        self.seed = seed
        self.grid_size = 100
        self.biomes = ["grind_canyons", "oil_marshes", "rust_wastes", "steam_peaks", "brass_forest"]

    def generate_global_map(self):
        """
        Populates the SQLite database with the initial world seed.
        Creates resource nodes and assigns faction territories.
        """
        random.seed(self.seed)
        conn = sqlite3.connect(db_manager.DB_NAME)
        cursor = conn.cursor()
        
        # ... Logic for procedural macro-world generation ...
        # (Generating resource nodes, cities, and faction zones)
        
        conn.commit()
        conn.close()
        print(f"[Generator] Global map generated with seed {self.seed}.")

    def get_region_data(self, x: int, y: int) -> Dict[str, Any]:
        """
        Retrieves biome and faction metadata for a specific coordinate on the macro grid.
        
        Args:
            x, y: Coordinates on the 100x100 grid.
            
        Returns:
            Dict[str, Any]: Metadata for the region.
        """
        random.seed(f"{x},{y}")
        return {
            "biome": random.choice(self.biomes),
            "faction": random.choice(["sump_kin", "iron_caldera", "river_folk", "imperial_remnant"]),
            "chaos_level": random.randint(0, 10)
        }
