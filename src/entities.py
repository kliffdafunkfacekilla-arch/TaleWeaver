from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
import random
import json
import os
import actions

ITEM_CACHE = None
SKILL_CACHE = None

class ResourcePool(BaseModel):
    stamina: int = 10
    max_stamina: int = 10
    focus: int = 10
    max_focus: int = 10
    move_remaining: int = 0
    beats: Dict[str, int] = Field(default_factory=lambda: {"move": 1, "stamina": 1, "focus": 1})
    composure: int = 20
    max_composure: int = 20

class Entity(BaseModel):
    id: str = Field(default_factory=lambda: str(random.randint(1000, 9999)))
    name: str
    type: str  # player, npc, prop, hostile
    pos: List[int] = Field(default_factory=lambda: [0, 0])
    hp: int = 20
    max_hp: int = 20
    stats: Dict[str, int] = Field(default_factory=dict)
    resources: ResourcePool = Field(default_factory=ResourcePool)
    inventory: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    equipment: Dict[str, str] = Field(default_factory=lambda: {"weapon": "None", "armor": "None", "accessory": "None"})
    tracks: Dict[str, str] = Field(default_factory=lambda: {"offense": "Might", "defense": "Reflexes"})

    def get(self, key, default=None):
        # Compatibility helper for transition
        return getattr(self, key, default)

    def setdefault(self, key, default=None):
        # Compatibility helper
        if not hasattr(self, key):
            setattr(self, key, default)
        return getattr(self, key)

def load_items():
    global ITEM_CACHE
    if ITEM_CACHE is not None:
        return ITEM_CACHE
        
    try:
        with open("data/items.json", "r", encoding="utf-8") as f: 
            ITEM_CACHE = json.load(f)
            return ITEM_CACHE
    except Exception: 
        return {"weapons":{}, "armor":{}, "accessories":{}, "consumables":{}}

def load_skills():
    """Reads the skills database and caches it for performance."""
    global SKILL_CACHE
    if SKILL_CACHE is not None:
        return SKILL_CACHE
        
    try:
        if not os.path.exists("data/skills.json"):
            return {"passives": {}, "tactics": {}, "anomalies": {}}
            
        with open("data/skills.json", "r", encoding="utf-8") as f: 
            SKILL_CACHE = json.load(f)
            return SKILL_CACHE
    except Exception as e:
        print(f"[Error] Failed to load skills: {e}")
        return {"passives": {}, "tactics": {}, "anomalies": {}}

def get_item_weight(item_name):
    items = load_items()
    for cat in ["weapons", "armor", "accessories", "consumables"]:
        if item_name in items.get(cat, {}):
            return items[cat][item_name].get("weight", 0)
    return 0

def loot_all(looter, target):
    t_inv = target.inventory if hasattr(target, "inventory") else target.get("inventory", [])
    if not t_inv: return False
    l_inv = looter.inventory if hasattr(looter, "inventory") else looter.setdefault("inventory", [])
    l_inv.extend(t_inv)
    if hasattr(target, "inventory"): target.inventory = []
    else: target["inventory"] = []
    return True

def equip_item(entity, item_name):
    items = load_items()
    item_type = None
    if item_name in items.get("weapons", {}): item_type = "weapon"
    elif item_name in items.get("armor", {}): item_type = "armor"
    elif item_name in items.get("accessories", {}): item_type = "accessory"
    
    inv = entity.inventory if hasattr(entity, "inventory") else entity.get("inventory", [])
    if not item_type or item_name not in inv: return False

    equip = entity.equipment if hasattr(entity, "equipment") else entity.setdefault("equipment", {})
    current = equip.get(item_type)
    if current and current != "None":
        inv.append(current)
        
    equip[item_type] = item_name
    inv.remove(item_name)
    return True

def unequip_item(entity, slot):
    equip = entity.equipment if hasattr(entity, "equipment") else entity.get("equipment", {})
    current = equip.get(slot)
    if current and current != "None":
        inv = entity.inventory if hasattr(entity, "inventory") else entity.setdefault("inventory", [])
        inv.append(current)
        equip[slot] = "None"
        return True
    return False

def get_gear_bonus(entity, stat_name):
    """Dynamically looks for {stat_name}_bonus in equipped items."""
    items = load_items()
    bonus = 0
    equip = entity.get("equipment", {})
    bonus_key = f"{stat_name.lower()}_bonus"
    
    for slot, item_name in equip.items():
        if not item_name or item_name == "None": continue
        
        item_data = None
        for cat in ["weapons", "armor", "accessories"]:
            if item_name in items.get(cat, {}):
                item_data = items[cat][item_name]
                break
        
        if item_data and bonus_key in item_data:
            bonus += item_data[bonus_key]
            
    return bonus

def get_stat(entity, stat_name):
    # Support both dict and Pydantic object
    stats = entity.stats if hasattr(entity, "stats") else entity.get("stats", {})
    base = stats.get(stat_name, 0)
    base += get_gear_bonus(entity, stat_name)
    return base

def get_attack_stat(entity):
    """B.R.U.T.A.L. Engine: Returns the stat used for the Offense Track."""
    return entity.get("tracks", {}).get("offense", "Might")

def get_defense_stat(entity):
    """B.R.U.T.A.L. Engine: Returns the stat used for the Defense Track."""
    return entity.get("tracks", {}).get("defense", "Reflexes")

def get_weapon_stats(entity):
    """Retrieves damage and range based on equipped weapon."""
    items = load_items()
    equipped_weapon = entity.get("equipment", {}).get("weapon")
    
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

def get_derived_stats(entity):
    return {
        "Perception": get_stat(entity, "Awareness") + get_stat(entity, "Logic") + get_stat(entity, "Vitality"),
        "Stealth": get_stat(entity, "Knowledge") + get_stat(entity, "Charm") + get_stat(entity, "Finesse"),
        "Movement": get_stat(entity, "Reflexes") + get_stat(entity, "Might") + get_stat(entity, "Intuition"),
        "Balance": get_stat(entity, "Endurance") + get_stat(entity, "Fortitude") + get_stat(entity, "Willpower")
    }

def get_movement_speed(entity):
    stats = get_derived_stats(entity)
    return max(1, stats.get("Movement", 1))

def get_best_stat_for_action(player, action_name):
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

def get_max_stamina(entity):
    base_max = entity.get("resources", {}).get("max_stamina", 10)
    items = load_items()
    equip = entity.get("equipment", {})
    armor = items.get("armor", {}).get(equip.get("armor"))
    tax = armor.get("stamina_tax", 0) if armor else 0
    return max(1, base_max - tax)

def get_max_focus(entity):
    base_max = entity.get("resources", {}).get("max_focus", 10)
    items = load_items()
    equip = entity.get("equipment", {})
    acc = items.get("accessories", {}).get(equip.get("accessory"))
    tax = acc.get("focus_tax", 0) if acc else 0
    return max(1, base_max - tax)

def spend_stamina(entity, amount):
    res = entity.resources if hasattr(entity, "resources") else entity.get("resources", {})
    curr = res.stamina if hasattr(res, "stamina") else res.get("stamina", 0)
    if curr >= amount:
        if hasattr(res, "stamina"): res.stamina -= amount
        else: res["stamina"] -= amount
        return True
    return False

def refresh_beats(entity):
    res = entity.resources if hasattr(entity, "resources") else entity.setdefault("resources", {})
    tags = entity.tags if hasattr(entity, "tags") else entity.get("tags", [])
    
    mv = 0 if "staggered" in tags else 1
    st = 0 if "stunned" in tags else 1
    fo = 1 
    
    if hasattr(res, "beats"):
        res.beats = {"move": mv, "stamina": st, "focus": fo}
    else:
        res["beats"] = {"move": mv, "stamina": st, "focus": fo}

def grant_free_beat(entity, beat_type):
    current_beats = entity.setdefault("resources", {}).setdefault("beats", {"move": 0, "stamina": 0, "focus": 0})
    
    if current_beats.get(beat_type, 0) < 2:
        current_beats[beat_type] += 1
        return True
    return False

def consume_beat(entity, beat_type):
    res = entity.resources if hasattr(entity, "resources") else entity.get("resources", {})
    beats = res.beats if hasattr(res, "beats") else res.get("beats", {})
    if beats.get(beat_type, 0) > 0:
        beats[beat_type] -= 1
        return True
    return False

def apply_damage(entity, amount, damage_type="physical"):
    if damage_type == "physical":
        hp = entity.hp if hasattr(entity, "hp") else entity.get("hp", 0)
        max_hp = entity.max_hp if hasattr(entity, "max_hp") else entity.get("max_hp", 20)
        
        new_hp = max(0, hp - amount)
        if hasattr(entity, "hp"): entity.hp = new_hp
        else: entity["hp"] = new_hp
        
        tags = entity.tags if hasattr(entity, "tags") else entity.setdefault("tags", [])
        trauma_msg = ""
        
        if amount >= (max_hp * 0.4):
            if "maimed" not in tags: 
                tags.append("maimed")
                if "staggered" not in tags: tags.append("staggered")
                trauma_msg = f"🩸 [TRAUMA] {getattr(entity, 'name', 'Enemy')} suffers a massive blow and is MAIMED!"
                
        if new_hp > 0 and new_hp <= (max_hp * 0.25):
            if "bleeding" not in tags:
                tags.append("bleeding")
                if not trauma_msg:
                    trauma_msg = f"🩸 [TRAUMA] {getattr(entity, 'name', 'Enemy')} is heavily wounded and BLEEDING!"
                else:
                    trauma_msg += " and BLEEDING!"

        if new_hp <= 0:
            if "hostile" in tags: tags.remove("hostile")
            if "dead" not in tags: tags.append("dead")
            return True, f"💀 {getattr(entity, 'name', 'Enemy')} has fallen."
            
        return False, trauma_msg
            
    return False, ""

def roll_check(entity, stat_name, situational_adv=False, situational_dis=False):
    tags = entity.get("tags", [])
    has_adv = situational_adv
    has_dis = situational_dis
    
    if "staggered" in tags or "prone" in tags or "terrified" in tags:
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

def regenerate_resources(entity):
    res = entity.resources if hasattr(entity, "resources") else entity.setdefault("resources", {})
    max_s = res.max_stamina if hasattr(res, "max_stamina") else res.get("max_stamina", 10)
    max_f = res.max_focus if hasattr(res, "max_focus") else res.get("max_focus", 10)
    
    if hasattr(res, "stamina"):
        res.stamina = min(max_s, res.stamina + 2)
        res.focus = min(max_f, res.focus + 2)
    else:
        res["stamina"] = min(max_s, res.get("stamina", 0) + 2)
        res["focus"] = min(max_f, res.get("focus", 0) + 2)
