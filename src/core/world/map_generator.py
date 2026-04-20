import math
import random
import noise
from typing import Dict, List, Any, Tuple
try:
    from core.world.ecology import EcologyManager, EntityFactory
except ImportError:
    from ecology import EcologyManager, EntityFactory

class FractalMapGenerator:
    """
    Clockwork Fractal Map Generator for Ostraka.
    Deterministic terrain and entity population with multi-tier ecology.
    Now reacts to Time, Weather, and Aetheric Tension.
    Refactored to avoid unstable 'base' parameter in noise calls.
    """
    def __init__(self, master_seed: int):
        self.master_seed = master_seed

    def _calculate_biome(self, x: float, y: float, scale: float, chaos_mod: float = 0.0) -> Tuple[str, Dict[str, float]]:
        """
        Matrix logic for Ostraka biomes based on 3 noise layers + Global Chaos Modifier.
        Uses coordinate offsets for stability.
        """
        # We use large offsets derived from the master_seed for different layers
        # This is more stable on Windows than using the 'base' parameter
        seed_off = self.master_seed % 1000000 
        
        # Layer 1: Elevation
        e_raw = noise.pnoise2((x + seed_off) / scale, 
                              (y + seed_off) / scale, octaves=4)
        elevation = (e_raw + 1.0) / 2.0
        
        # Layer 2: Moisture (offset by another chunk of the seed)
        m_raw = noise.pnoise2((x + seed_off + 5000) / scale, 
                              (y + seed_off + 5000) / scale, octaves=4)
        moisture = (m_raw + 1.0) / 2.0
        
        # Layer 3: Chaos (offset by another chunk)
        c_raw = noise.pnoise2((x + seed_off + 10000) / scale, 
                              (y + seed_off + 10000) / scale, octaves=4)
        chaos = (c_raw + 1.0) / 2.0 + chaos_mod
        chaos = max(0.0, min(1.0, chaos))
        
        raw_values = {"elev": elevation, "moist": moisture, "chaos": chaos}

        # Ostraka Biome Matrix
        if chaos > 0.85:
            return "Chaos Zone / Grind Canyons", raw_values
        if elevation > 0.75:
            return "Engineer's Range", raw_values
        if elevation < 0.3 and moisture > 0.7:
            return "The Sump", raw_values
        if elevation < 0.4 and moisture < 0.3:
            return "The Dust Bowl", raw_values
        if 0.4 <= elevation <= 0.75:
            if moisture > 0.6: return "The Verdant Tangle", raw_values
            if moisture >= 0.3: return "Heartland Plains", raw_values
            return "Howling Steppes", raw_values
        return "Shifting Wastes", raw_values

    def generate_chunk(self, offset_x: int, offset_y: int, width: int = 100, height: int = 100, 
                       scale: float = 20.0, seed_prefix: str = "seed",
                       atmos_state: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generates a 2D grid of biomes AND a list of lore-accurate entities.
        """
        grid = []
        entities_list = []
        
        chaos_mod = atmos_state.get("chaos_modifier", 0.0) if atmos_state else 0.0
        is_shadow = atmos_state.get("calendar", {}).get("is_shadow_week", False) if atmos_state else False
        weather = atmos_state.get("weather", {}).get("state", "Clear") if atmos_state else "Clear"
        
        # Setting the random seed for deterministic spawning in this chunk
        random.seed(f"{self.master_seed}_{seed_prefix}")
        
        for y in range(height):
            row = []
            for x in range(width):
                global_x = offset_x + x
                global_y = offset_y + y
                
                biome_name, raw_data = self._calculate_biome(global_x, global_y, scale, chaos_mod)
                row.append({
                    "biome": biome_name,
                    "data": raw_data
                })
                
                chaos = raw_data["chaos"]
                
                # --- Multi-Tier Spawning Logic ---
                ambient_chance = 0.40 if not is_shadow else 0.10
                fauna_chance = 0.15 if not is_shadow else 0.05
                
                if random.random() < ambient_chance:
                    options = EcologyManager.get_spawns(biome_name, "ambient_flora")
                    if options:
                        entities_list.append(EntityFactory.create(random.choice(options), x, y, seed_prefix))
                
                if random.random() < fauna_chance:
                    options = EcologyManager.get_spawns(biome_name, "fauna")
                    if options:
                        entities_list.append(EntityFactory.create(random.choice(options), x, y, seed_prefix))
                
                lore_chance = 0.05
                if weather == "Aetheric Surge": lore_chance = 0.15
                
                if random.random() < lore_chance:
                    template = None
                    if chaos > 0.95:
                        template = "creature_litho_horror"
                    elif chaos > 0.85:
                        hostiles = EcologyManager.get_spawns(biome_name, "lore_hostile")
                        if hostiles: template = random.choice(hostiles)
                        else: template = "prop_chaos_anomaly"
                    else:
                        choices = EcologyManager.get_spawns(biome_name, "lore_neutral") + \
                                  EcologyManager.get_spawns(biome_name, "lore_hostile")
                        if choices: template = random.choice(choices)
                    
                    if template:
                        ent = EntityFactory.create(template, x, y, seed_prefix)
                        if "cloud_cutter" in template and weather == "Storm":
                            ent.name = "Red Ghost Cloud-Cutter"
                            ent.type = "hostile"
                            ent.tags.append("hostile")
                        entities_list.append(ent)
            grid.append(row)
        
        return {
            "grid": grid,
            "entities": [e.model_dump() for e in entities_list],
            "meta": {
                "offset": [offset_x, offset_y],
                "size": [width, height],
                "scale": scale,
                "atmospheric_state": atmos_state
            }
        }
