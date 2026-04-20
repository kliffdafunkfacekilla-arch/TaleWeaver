import json
import os
import random
from typing import Dict, List, Any, Optional

# Internal relative-friendly imports
import entities
from core.world.map_generator import FractalMapGenerator
from core.world.ecology import EntityFactory

class MapGenerator:
    """
    Bridge between the Clockwork Fractal Engine and the Ostraka Engine.
    Handles high-resolution 100x100 map generation with deterministic seeding.
    Supports local fractal terrain AND tactical ship boarding actions.
    """
    DEFAULT_SHIP_LAYOUTS = {
        "Light Skiff": [
            ["ship_hull", "ship_deck", "ship_deck", "ship_deck", "ship_hull"],
            ["ship_hull", "ship_deck", "ship_helm", "ship_deck", "ship_hull"],
            ["ship_hull", "ship_deck", "ship_deck", "ship_deck", "ship_hull"],
            ["ship_hull", "ship_deck", "ship_cannons", "ship_deck", "ship_hull"],
            ["ship_hull", "ship_deck", "ship_deck", "ship_deck", "ship_hull"],
            ["ship_hull", "ship_deck", "ship_quarters", "ship_deck", "ship_hull"],
            ["ship_hull", "ship_deck", "ship_deck", "ship_deck", "ship_hull"],
        ],
        "Heavy Galleon": [
            ["ship_hull"] * 9,
            ["ship_hull", "ship_deck", "ship_deck", "ship_deck", "ship_helm", "ship_deck", "ship_deck", "ship_deck", "ship_hull"],
            ["ship_hull"] + ["ship_deck"] * 7 + ["ship_hull"],
            ["ship_hull", "ship_deck", "ship_cannons", "ship_deck", "ship_deck", "ship_deck", "ship_cannons", "ship_deck", "ship_hull"],
            ["ship_hull"] + ["ship_deck"] * 7 + ["ship_hull"],
            ["ship_hull", "ship_deck", "ship_deck", "ship_deck", "ship_quarters", "ship_deck", "ship_deck", "ship_deck", "ship_hull"],
            ["ship_hull"] * 9,
        ]
    }

    def __init__(self, width: int = 100, height: int = 100):
        """Initializes the tactical grid dimensions (Locked at 100x100)."""
        self.width = width
        self.height = height
        # Deterministic master seed for the world
        self.f_gen = FractalMapGenerator(master_seed=42069)

    def generate_local_map(self, global_pos: List[int], player_entry_pos: List[int], player_data: Optional[entities.Entity] = None, quest_deck: List[Dict[str, Any]] = []) -> Dict[str, Any]:
        """
        Generates a 100x100 local tactical map using the Fractal Engine.
        
        Args:
            global_pos: The [x,y] coordinates on the world grid.
            player_entry_pos: Where the player should start on the tactical grid.
            player_data: The persistent player Entity object.
            
        Returns:
            Dict[str, Any]: The complete local_map_state dictionary.
        """
        # Coordinate mapping for fractal noise offsets
        gx, gy = global_pos
        offset_x = gx * self.width
        offset_y = gy * self.height
        
        # Atmospheric state for spawn modifiers
        atmos = {
            "chaos_modifier": 0.0,
            "weather": {"state": "Clear"},
            "calendar": {"is_shadow_week": False}
        }
        
        chunk = self.f_gen.generate_chunk(
            offset_x=offset_x, 
            offset_y=offset_y, 
            width=self.width, 
            height=self.height,
            atmos_state=atmos
        )
        
        # Prepare Entities
        final_entities = []
        
        # Inject Player
        if player_data:
            player_data.pos = player_entry_pos
            final_entities.append(player_data)
        else:
            # Fallback player if data is missing
            new_player = entities.Entity(
                name="Captain Jax",
                type="player",
                pos=player_entry_pos,
                hp=20,
                max_hp=20,
                tags=["player", "flesh", "river_folk"]
            )
            final_entities.append(new_player)
            
        # Map raw fractal entities into Pydantic models
        for raw_e in chunk["entities"]:
            # Avoid placing props on top of the player
            if raw_e["pos"] == player_entry_pos: continue
            
            # Pydantic validation for the generated entity
            ent = entities.Entity.model_validate(raw_e)
            final_entities.append(ent)
            
        # Final Packaging for engine consumption
        local_state = {
            "local_map_state": {
                "environment": f"You have entered a new region at {global_pos}.",
                "entities": final_entities,
                "biomes": chunk["grid"]
            },
            "meta": {
                "global_pos": global_pos,
                "grid_size": [self.width, self.height],
                "clock": 0,
                "region_id": f"reg_{gx}_{gy}",
                "current_map_id": f"local_{gx}_{gy}"
            }
        }
        
        # Persistence check
        state_path = "state/local_map_state.json"
        os.makedirs(os.path.dirname(state_path), exist_ok=True)
        # Handle the Pydantic serialization through engine's save logic eventually, 
        # but for now we write directly to satisfy immediate engine.load_state() calls.
        with open(state_path, "w", encoding="utf-8") as f:
            # We must use a dict representation that includes our Pydantic objects serialized
            json_compatible = {
                "local_map_state": {
                    "environment": local_state["local_map_state"]["environment"],
                    "entities": [e.model_dump() for e in local_state["local_map_state"]["entities"]],
                    "biomes": local_state["local_map_state"]["biomes"]
                },
                "meta": local_state["meta"]
            }
            json.dump(json_compatible, f, indent=2)
            
        return json_compatible

    def generate_boarding_map(self, ship_a: Dict[str, Any], ship_b: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates a tactical battlemap where ship A is boarding ship B.
        Ships are placed side-by-side in the center of the 100x100 grid.
        """
        # Create empty sky/aether grid
        grid = [[{"biome": "The Void / Aether Sky", "data": {"elev": 0, "moist": 0, "chaos": 0.5}} for _ in range(self.width)] for _ in range(self.height)]
        
        # Helper to inject ship layout
        def inject_ship(layout_name: str, start_x: int, start_y: int):
            layout = self.DEFAULT_SHIP_LAYOUTS.get(layout_name, self.DEFAULT_SHIP_LAYOUTS["Light Skiff"])
            for dy, row in enumerate(layout):
                for dx, cell in enumerate(row):
                    if start_y + dy < self.height and start_x + dx < self.width:
                        grid[start_y + dy][start_x + dx] = {
                            "biome": f"Ship Interior ({cell.replace('ship_', '').title()})",
                            "data": {"elev": 1.0, "moist": 0.0, "chaos": 0.1, "is_ship": True}
                        }

        # Place Ship A (Left)
        inject_ship(ship_a.get("class", "Light Skiff"), 40, 45)
        # Place Ship B (Right) - Locked together
        inject_ship(ship_b.get("class", "Light Skiff"), 46, 45)

        local_state = {
            "local_map_state": {
                "environment": f"EMERGENCY: {ship_a['name']} has docked with {ship_b['name']} for boarding!",
                "entities": [], # In practice, loop through ship crews and inject entities here
                "biomes": grid
            },
            "meta": {
                "global_pos": [0, 0],
                "grid_size": [self.width, self.height],
                "region_id": "naval_boarding_sector",
                "current_map_id": f"boarding_{ship_a['ship_id']}_{ship_b['ship_id']}"
            }
        }
        
        # Save state for loading
        state_path = "state/local_map_state.json"
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(local_state, f, indent=2)
            
        return local_state

    def generate_interior_room(self, room_definition: Dict[str, Any]) -> Dict[str, Any]:
        """Interior rooms remain 15x15 for tactical focus."""
        # Simple placeholder that maintains the 15x15 standard for dungeons
        return {
            "local_map_state": {"entities": [], "biomes": []},
            "meta": {"grid_size": [15, 15]}
        }

def generate_local_map(global_pos: List[int], player_entry_pos: List[int], player_data: Optional[entities.Entity] = None, quest_deck: List[Dict[str, Any]] = []) -> Dict[str, Any]:
    """Module-level entry point for the engine's transition logic."""
    bridge = MapGenerator()
    return bridge.generate_local_map(global_pos, player_entry_pos, player_data, quest_deck)
