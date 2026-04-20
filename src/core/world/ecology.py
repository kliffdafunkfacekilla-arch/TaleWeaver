import random
from typing import List, Dict, Any, Optional

# We expect 'src' to be in sys.path or the workspace root to be correct.
try:
    import entities
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.getcwd(), 'src'))
    import entities

class EntityFactory:
    """
    Factory to instantiate lore-consistent Entity objects from string templates.
    """
    
    @staticmethod
    def create(template: str, x: int, y: int, seed_prefix: str) -> entities.Entity:
        """
        Instantiates an Entity from a template with deterministic ID and stats.
        """
        # Deterministic ID based on coordinates
        ent_id = f"ent_{seed_prefix}_{x}_{y}_{template[:3]}"
        
        ent_type = "prop"
        base_hp = 10
        stats = entities.EntityStats()
        tags = []
        name = template.replace("_", " ").title()
        
        # Archetype Mapping
        if template.startswith("npc_"):
            ent_type = "npc"
            base_hp = 12
            stats = entities.EntityStats(Awareness=4, Logic=4, Vitality=4, Might=4, Reflexes=4, Endurance=4)
            tags = ["sentient", "social", "organic"]
        elif template.startswith("creature_"):
            ent_type = "hostile"
            base_hp = 15
            stats = entities.EntityStats(Might=6, Reflexes=6, Vitality=6, Endurance=6)
            tags = ["hostile", "organic", "beast", "predator"]
        elif template.startswith("fauna_"):
            ent_type = "npc"
            base_hp = 8
            stats = entities.EntityStats(Reflexes=5, Vitality=4)
            tags = ["organic", "fauna", "prey"]
        elif template.startswith("flora_"):
            ent_type = "terrain"
            base_hp = 5
            tags = ["organic", "flora", "fixed"]
        elif template.startswith("ambient_"):
            ent_type = "prop"
            base_hp = 1
            tags = ["ambient", "tiny", "organic"]
        elif template.startswith("prop_"):
            ent_type = "prop"
            base_hp = 20
            tags = ["prop", "fixed", "interactable"]

        # Tag-based logic from user request
        if "wire_scrub" in template: tags += ["dry", "forageable"]
        if "glass_mouse" in template: tags += ["tiny", "prey"]; base_hp = 1
        if "dune_viper" in template: tags += ["venomous"]
        if "rot_weed" in template: tags += ["aquatic", "nuisance"]
        if "glow_fly" in template: tags += ["insect", "flying"]; base_hp = 1
        if "mud_slug" in template: tags += ["prey", "edible"]
        if "ash_lichen" in template: tags += ["cold", "forageable"]
        if "crag_pika" in template: tags += ["nimble"]
        if "rust_hawk" in template: tags += ["avian", "predator"]
        if "iron_wheat" in template: tags += ["crop", "staple"]
        if "field_hare" in template: tags += ["fast"]
        if "plains_coyote" in template: tags += ["pack"]
        if "strangle_vine" in template: tags += ["hazard", "obstacle"]
        if "spore_moth" in template: tags += ["insect", "glowing"]; base_hp = 1
        if "bark_beetle" in template: tags += ["insect", "edible"]

        # Force 1 HP for Ambient or Tiny
        if "ambient" in tags or "tiny" in tags:
            base_hp = 1

        # Specific Overrides for Lore Creatures
        if "horror" in template or "wyrm" in template:
            base_hp = 30
            stats.Might += 4
            tags.append("brute")
        if "anomaly" in template:
            base_hp = 100
            tags += ["chaos", "magical", "hazard"]

        return entities.Entity(
            id=ent_id,
            name=name,
            type=ent_type,
            pos=[x, y],
            hp=base_hp,
            max_hp=base_hp,
            stats=stats,
            tags=tags
        )

class EcologyManager:
    """
    Mapping of Biomes to entity pools for Ostraka.
    """
    MATRIX = {
        "The Dust Bowl": {
            "ambient_flora": ["flora_wire_scrub", "flora_ghost_bloom"],
            "fauna": ["fauna_glass_mouse"],
            "lore_neutral": ["npc_dust_husk_rider", "prop_sand_skiff"],
            "lore_hostile": ["creature_sand_eel", "creature_glass_grub", "creature_dune_viper"]
        },
        "The Sump": {
            "ambient_flora": ["flora_rot_weed", "ambient_glow_fly"],
            "fauna": ["fauna_mud_slug"],
            "lore_neutral": ["npc_river_folk", "npc_sump_kin", "prop_turtle_train_car"],
            "lore_hostile": ["creature_swamp_horror"]
        },
        "Engineer's Range": {
            "ambient_flora": ["flora_ash_lichen"],
            "fauna": ["fauna_crag_pika"],
            "lore_neutral": ["npc_avian", "npc_tarsier", "fauna_sky_grazer", "fauna_cloud_ram"],
            "lore_hostile": ["creature_cloud_cutter_ray", "creature_fur_wyrm", "creature_rust_hawk"]
        },
        "The Verdant Tangle": {
            "ambient_flora": ["flora_strangle_vine", "ambient_spore_moth"],
            "fauna": ["fauna_bark_beetle", "fauna_titan_aphid"],
            "lore_neutral": ["npc_simian", "npc_formicidae"],
            "lore_hostile": ["creature_tangle_stalker"]
        },
        "Heartland Plains": {
            "ambient_flora": ["flora_iron_wheat"],
            "fauna": ["fauna_field_hare"],
            "lore_neutral": ["npc_heartland_wolf", "npc_deer_farmer", "prop_wind_mill"],
            "lore_hostile": ["creature_coyote_bandit", "creature_plains_coyote"]
        },
        "Howling Steppes": {
            "ambient_flora": ["flora_wire_scrub"],
            "fauna": ["fauna_giant_goat", "fauna_field_hare"],
            "lore_neutral": ["npc_steppes_nomad"],
            "lore_hostile": ["creature_steppes_stalker"]
        },
        "Chaos Zone / Grind Canyons": {
            "ambient_flora": ["prop_chaos_anomaly"],
            "fauna": [],
            "lore_neutral": [],
            "lore_hostile": ["creature_litho_horror"]
        },
        "Shifting Wastes": {
            "ambient_flora": ["prop_scrap_pile"],
            "fauna": ["fauna_waste_rat"],
            "lore_neutral": ["npc_scavenger"],
            "lore_hostile": ["creature_waste_rat"]
        }
    }

    @staticmethod
    def get_spawns(biome: str, category: str = "lore_neutral") -> list:
        return EcologyManager.MATRIX.get(biome, {}).get(category, [])
