from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
import random
import json
import os
import actions

# Global caches for JSON databases to avoid repeated disk I/O
ITEM_CACHE: Optional[Dict[str, Any]] = None
SKILL_CACHE: Optional[Dict[str, Any]] = None

class Beats(BaseModel):
    """Action tokens refreshed every turn."""
    move: int = 0
    stamina: int = 0
    focus: int = 0

class ResourcePool(BaseModel):
    """Transient pools for health, energy, and action beats."""
    stamina: int = 0
    max_stamina: int = 10
    focus: int = 0
    max_focus: int = 10
    beats: Beats = Field(default_factory=Beats)

class Equipment(BaseModel):
    """Categorized items currently wielded or worn."""
    weapon: Optional[str] = "None"
    armor: Optional[str] = "None"
    accessory: Optional[str] = "None"

class EntityStats(BaseModel):
    """Primary quantitative attributes of an entity."""
    Awareness: int = 0
    Logic: int = 0
    Vitality: int = 0
    Knowledge: int = 0
    Charm: int = 0
    Finesse: int = 0
    Reflexes: int = 0
    Might: int = 0
    Intuition: int = 0
    Endurance: int = 0
    Fortitude: int = 0
    Willpower: int = 0

class Tracks(BaseModel):
    """Primary stat tracks for combat resolution."""
    offense: str = "Might"
    defense: str = "Reflexes"

class Entity(BaseModel):
    """
    The core data model for all actors and props in Ostraka.
    Strictly enforced via Pydantic for type safety and nested validation.
    """
    id: str = Field(default_factory=lambda: str(random.randint(1000, 9999)))
    name: str
    type: str = "prop"  # player, npc, hostile, prop
    pos: List[int] = Field(default_factory=lambda: [0, 0])
    hp: int = 20
    max_hp: int = 20
    resources: ResourcePool = Field(default_factory=ResourcePool)
    inventory: List[str] = Field(default_factory=list)
    equipment: Equipment = Field(default_factory=Equipment)
    stats: EntityStats = Field(default_factory=EntityStats)
    tracks: Tracks = Field(default_factory=Tracks)
    skills: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)

def load_items() -> Dict[str, Any]:
    """Reads the items database and caches it for performance."""
    global ITEM_CACHE
    if ITEM_CACHE is not None:
        return ITEM_CACHE
        
    try:
        path = "data/items.json" if os.path.exists("data/items.json") else "../data/items.json"
        with open(path, "r", encoding="utf-8") as f: 
            ITEM_CACHE = json.load(f)
            return ITEM_CACHE
    except Exception: 
        return {"weapons":{}, "armor":{}, "accessories":{}, "consumables":{}}

def load_skills() -> Dict[str, Any]:
    """Reads the skills database and caches it for performance."""
    global SKILL_CACHE
    if SKILL_CACHE is not None:
        return SKILL_CACHE
        
    try:
        path = "data/skills.json" if os.path.exists("data/skills.json") else "../data/skills.json"
        if not os.path.exists(path):
            return {"passives": {}, "tactics": {}, "anomalies": {}}
            
        with open(path, "r", encoding="utf-8") as f: 
            SKILL_CACHE = json.load(f)
            return SKILL_CACHE
    except Exception as e:
        print(f"[Error] Failed to load skills: {e}")
        return {"passives": {}, "tactics": {}, "anomalies": {}}

def get_item_weight(item_name: str) -> int:
    """Retrieves weight of an item from the JSON database."""
    items = load_items()
    for cat in ["weapons", "armor", "accessories", "consumables"]:
        if item_name in items.get(cat, {}):
            return items[cat][item_name].get("weight", 0)
    return 0

def loot_all(looter: Entity, target: Entity) -> bool:
    """Moves all inventory from target to looter."""
    if not target.inventory: return False
    looter.inventory.extend(target.inventory)
    target.inventory = []
    return True

def equip_item(entity: Entity, item_name: str) -> bool:
    """Equips an item, returning old gear to inventory."""
    items = load_items()
    item_type = None
    if item_name in items.get("weapons", {}): item_type = "weapon"
    elif item_name in items.get("armor", {}): item_type = "armor"
    elif item_name in items.get("accessories", {}): item_type = "accessory"
    
    if not item_type or item_name not in entity.inventory: return False

    current = getattr(entity.equipment, item_type)
    if current and current != "None":
        entity.inventory.append(current)
        
    setattr(entity.equipment, item_type, item_name)
    entity.inventory.remove(item_name)
    return True

def unequip_item(entity: Entity, slot: str) -> bool:
    """Unequips an item from the specific Equipment slot."""
    current = getattr(entity.equipment, slot, "None")
    if current and current != "None":
        entity.inventory.append(current)
        setattr(entity.equipment, slot, "None")
        return True
    return False

def get_gear_bonus(entity: Entity, stat_name: str) -> int:
    """Calculates stat bonuses from equipped gear."""
    items = load_items()
    bonus = 0
    bonus_key = f"{stat_name.lower()}_bonus"
    
    # Iterate over Equipment model fields
    for slot in ["weapon", "armor", "accessory"]:
        item_name = getattr(entity.equipment, slot)
        if not item_name or item_name == "None": continue
        
        item_data = None
        for cat in ["weapons", "armor", "accessories"]:
            if item_name in items.get(cat, {}):
                item_data = items[cat][item_name]
                break
        
        if item_data and bonus_key in item_data:
            bonus += item_data[bonus_key]
            
    return bonus

def get_stat(entity: Entity, stat_name: str) -> int:
    """Retrieves total stat value (Base Attribute + Gear Bonus)."""
    base = getattr(entity.stats, stat_name, 0)
    base += get_gear_bonus(entity, stat_name)
    return base

def get_attack_stat(entity: Entity) -> str:
    """Primary offensive track."""
    return entity.tracks.offense

def get_defense_stat(entity: Entity) -> str:
    """Primary defensive track."""
    return entity.tracks.defense

def get_weapon_stats(entity: Entity) -> Dict[str, Any]:
    """Retrieves profile for whatever is in entity.equipment.weapon."""
    items = load_items()
    equipped_weapon = entity.equipment.weapon
    
    if equipped_weapon and equipped_weapon in items.get("weapons", {}):
        w = items["weapons"][equipped_weapon]
        return {
            "name": equipped_weapon,
            "die": w.get("damage_die", 4),
            "flat": w.get("flat_damage", 0),
            "range": w.get("range", 1),
            "cost": w.get("stamina_cost", 2),
            "tags": w.get("tags", [])
        }
    
    unarmed = items.get("weapons", {}).get("Unarmed", {"damage_die": 4, "flat_damage": 0, "range": 1, "stamina_cost": 1})
    return {
        "name": "Unarmed",
        "die": unarmed.get("damage_die", 4),
        "flat": unarmed.get("flat_damage", 0),
        "range": unarmed.get("range", 1),
        "cost": unarmed.get("stamina_cost", 1),
        "tags": unarmed.get("tags", [])
    }

def get_derived_stats(entity: Entity) -> Dict[str, int]:
    """Groups base attributes into macro-categories (Perception, Stealth, etc)."""
    return {
        "Perception": get_stat(entity, "Awareness") + get_stat(entity, "Logic") + get_stat(entity, "Vitality"),
        "Stealth": get_stat(entity, "Knowledge") + get_stat(entity, "Charm") + get_stat(entity, "Finesse"),
        "Movement": get_stat(entity, "Reflexes") + get_stat(entity, "Might") + get_stat(entity, "Intuition"),
        "Balance": get_stat(entity, "Endurance") + get_stat(entity, "Fortitude") + get_stat(entity, "Willpower")
    }

def get_movement_speed(entity: Entity) -> int:
    """Returns final grid movement capability."""
    stats = get_derived_stats(entity)
    return max(1, stats.get("Movement", 1))

def get_best_stat_for_action(player: Entity, action_name: str) -> Optional[str]:
    """Determines which of a list of valid stats for an action is highest."""
    data = actions.ACTION_REGISTRY.get(action_name)
    if not data or not data.get("stats"): return None
    
    best_stat = data["stats"][0]
    best_val = -1
    
    for stat in data["stats"]:
        val = get_stat(player, stat)
        if val > best_val:
            best_val = val
            best_stat = stat
            
    return best_stat

def get_max_stamina(entity: Entity) -> int:
    """Calculates max stamina minus Armor Tax."""
    base_max = entity.resources.max_stamina
    items = load_items()
    armor = items.get("armor", {}).get(entity.equipment.armor)
    tax = armor.get("stamina_tax", 0) if armor else 0
    return max(1, base_max - tax)

def get_max_focus(entity: Entity) -> int:
    """Calculates max focus minus Accessory Tax."""
    base_max = entity.resources.max_focus
    items = load_items()
    acc = items.get("accessories", {}).get(entity.equipment.accessory)
    tax = acc.get("focus_tax", 0) if acc else 0
    return max(1, base_max - tax)

def spend_stamina(entity: Entity, amount: int) -> bool:
    """Decrements stamina pool."""
    if entity.resources.stamina >= amount:
        entity.resources.stamina -= amount
        return True
    return False

def refresh_beats(entity: Entity):
    """Resets resource beats, applying status penalties."""
    tags = entity.tags
    entity.resources.beats.move = 0 if "staggered" in tags else 1
    entity.resources.beats.stamina = 0 if "stunned" in tags else 1
    entity.resources.beats.focus = 1

def grant_free_beat(entity: Entity, beat_type: str) -> bool:
    """Adds a bonus beat of a specific type (e.g. 'move'). cap of 2."""
    current = getattr(entity.resources.beats, beat_type, 2)
    if current < 2:
        setattr(entity.resources.beats, beat_type, current + 1)
        return True
    return False

def consume_beat(entity: Entity, beat_type: str) -> bool:
    """Attempts to use an action beat."""
    val = getattr(entity.resources.beats, beat_type, 0)
    if val > 0:
        setattr(entity.resources.beats, beat_type, val - 1)
        return True
    return False

def apply_damage(entity: Entity, amount: int, damage_type="physical") -> tuple[bool, str]:
    """Mechanical resolution of health reduction."""
    if damage_type == "physical":
        entity.hp = max(0, entity.hp - amount)
        
        trauma_msg = ""
        if amount >= (entity.max_hp * 0.4):
            if "maimed" not in entity.tags: 
                entity.tags.append("maimed")
                if "staggered" not in entity.tags: entity.tags.append("staggered")
                trauma_msg = f"\ud83e\ude78 [TRAUMA] {entity.name} suffers a massive blow and is MAIMED!"
                
        if entity.hp > 0 and entity.hp <= (entity.max_hp * 0.25):
            if "bleeding" not in entity.tags:
                entity.tags.append("bleeding")
                if not trauma_msg:
                    trauma_msg = f"\ud83e\ude78 [TRAUMA] {entity.name} is heavily wounded and BLEEDING!"
                else:
                    trauma_msg += " and BLEEDING!"

        if entity.hp <= 0:
            if "hostile" in entity.tags: entity.tags.remove("hostile")
            if "dead" not in entity.tags: entity.tags.append("dead")
            return True, f"\ud83d\udc80 {entity.name} has fallen."
            
        return False, trauma_msg
            
    return False, ""

def roll_check(entity: Entity, stat_name: str, situational_adv=False, situational_dis=False) -> tuple[int, str]:
    """Performance check via the B.R.U.T.A.L Engine logic."""
    tags = entity.tags
    has_adv = situational_adv
    has_dis = situational_dis
    
    if any(t in tags for t in ["staggered", "prone", "terrified"]):
        has_dis = True
    if "focused" in tags:
        has_adv = True
        
    if has_adv and has_dis:
        has_adv = has_dis = False

    roll_1 = random.randint(1, 20)
    roll_2 = random.randint(1, 20)
    
    if has_adv:
        base_roll = max(roll_1, roll_2)
        roll_log = f"[Advantage: Rolled {roll_1} & {roll_2} -> {base_roll}]"
    elif has_dis:
        base_roll = min(roll_1, roll_2)
        roll_log = f"[Disadvantage: Rolled {roll_1} & {roll_2} -> {base_roll}]"
    else:
        base_roll = roll_1
        roll_log = f"[Rolled {base_roll}]"

    total = base_roll + get_stat(entity, stat_name)
    return total, roll_log

def regenerate_resources(entity: Entity):
    """Replenishes energy pools."""
    res = entity.resources
    res.stamina = min(get_max_stamina(entity), res.stamina + 2)
    res.focus = min(get_max_focus(entity), res.focus + 2)
