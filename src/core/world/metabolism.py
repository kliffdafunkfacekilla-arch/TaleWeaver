import random
from typing import Dict, Any, List

class MetabolismManager:
    """
    Handles bio-social stability for Ostraka entities.
    Calculates thrive/die/migrate triggers based on environmental pressure.
    """
    
    @staticmethod
    def calculate_happiness(population: int, food: int, water: int, safety: int) -> int:
        """
        Derives happiness for a group (animal herd or city pop).
        Target: 50 (Stable), >75 (Thriving), <25 (Unstable).
        """
        if population <= 0: return 50
        
        # Per-capita needs (Abstracted)
        food_score = min(40, (food / population) * 40)
        water_score = min(30, (water / population) * 30)
        safety_score = min(30, safety * 3) # Safety is building-driven
        
        return int(food_score + water_score + safety_score)

    @staticmethod
    def process_biological_cycle(entity_data: Dict[str, Any], atmos: Dict[str, Any]) -> Dict[str, Any]:
        """
        Updates an organic entity's metabolism.
        Returns modifiers for state or survival triggers.
        """
        tags = entity_data.get("tags", [])
        if "organic" not in tags: return entity_data
        
        # Metabolism state stored in tags or a dedicated field (if model updated)
        # For now, we simulate effects via HP and Tags
        
        biome = atmos.get("biome", "Unknown")
        weather = atmos.get("weather", {}).get("state", "Clear")
        chaos = atmos.get("chaos_modifier", 0.0)
        
        # Survival Logic
        is_thriving = False
        is_suffering = False
        
        if "flora" in tags:
            if biome in ["The Dust Bowl"] and "dry" not in tags: is_suffering = True
            if biome in ["The Verdant Tangle"]: is_thriving = True
        
        if "fauna" in tags:
            if weather == "Storm": is_suffering = True
            if chaos > 0.4: is_suffering = True # Aetheric interference
            
        # Apply Consequences
        if is_suffering:
            entity_data["hp"] = max(0, entity_data["hp"] - 1)
            if entity_data["hp"] <= 0: tags.append("dead")
        elif is_thriving:
            # Chance to reproduce (spawn copy in high-level loop)
            if random.random() < 0.05:
                entity_data["repro_ready"] = True
                
        return entity_data

    @staticmethod
    def handle_social_chaos(settlement: Dict[str, Any]) -> List[str]:
        """
        Triggers consequences for low settlement happiness.
        Returns a list of 'Events' (e.g. ['spawn_bandits', 'destroy_building']).
        """
        happy = settlement.get("happiness", 50)
        events = []
        
        if happy < 25:
            events.append("spawn_bandits")
            if random.random() < 0.1:
                events.append("riot_damage")
        
        if happy < 10:
            events.append("famine_migration")
            
        return events
