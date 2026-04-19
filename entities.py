import random
import json
import actions
import os

ITEM_CACHE = None
SKILL_CACHE = None

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
    if "inventory" not in target or not target["inventory"]: return False
    if "inventory" not in looter: looter["inventory"] = []
    looter["inventory"].extend(target["inventory"])
    target["inventory"] = [] 
    return True

def equip_item(entity, item_name):
    items = load_items()
    item_type = None
    if item_name in items.get("weapons", {}): item_type = "weapon"
    elif item_name in items.get("armor", {}): item_type = "armor"
    elif item_name in items.get("accessories", {}): item_type = "accessory"
    
    if not item_type or item_name not in entity.get("inventory", []): return False

    current = entity.get("equipment", {}).get(item_type)
    if current and current != "None":
        entity["inventory"].append(current)
        
    entity["equipment"][item_type] = item_name
    entity["inventory"].remove(item_name)
    return True

def unequip_item(entity, slot):
    current = entity.get("equipment", {}).get(slot)
    if current and current != "None":
        if "inventory" not in entity: entity["inventory"] = []
        entity["inventory"].append(current)
        entity["equipment"][slot] = "None"
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
    base = entity.get("stats", {}).get(stat_name, 0)
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

def get_max_composure(entity):
    """Derived Composure: Base 10 + Willpower + Intuition."""
    return 10 + get_stat(entity, "Willpower") + get_stat(entity, "Intuition")

def spend_stamina(entity, amount):
    res = entity.get("resources", {})
    if res.get("stamina", 0) >= amount:
        res["stamina"] -= amount
        return True
    return False

def refresh_beats(entity):
    if "resources" not in entity: entity["resources"] = {}
    tags = entity.get("tags", [])
    
    mv = 0 if "staggered" in tags else 1
    st = 0 if "stunned" in tags else 1
    fo = 1 
    
    entity["resources"]["beats"] = {"move": mv, "stamina": st, "focus": fo}
    # MOVEMENT RESERVOIR: Allow movement up to speed per move beat
    entity["resources"]["move_remaining"] = get_movement_speed(entity) if mv > 0 else 0

def grant_free_beat(entity, beat_type):
    current_beats = entity.setdefault("resources", {}).setdefault("beats", {"move": 0, "stamina": 0, "focus": 0})
    
    if current_beats.get(beat_type, 0) < 2:
        current_beats[beat_type] += 1
        return True
    return False

def consume_beat(entity, beat_type):
    res = entity.get("resources", {})
    beats = res.get("beats", {})
    if beats.get(beat_type, 0) > 0:
        beats[beat_type] -= 1
        return True
    return False

def apply_damage(entity, amount, damage_type="physical"):
    """
    Physical damage reduces HP. Mental damage reduces Composure.
    Returning (is_dead, trauma_msg).
    """
    if damage_type == "physical" and "hp" in entity:
        entity["hp"] -= amount
        max_hp = entity.get("max_hp", 20)
        tags = entity.setdefault("tags", [])
        trauma_msg = ""
        
        if amount >= (max_hp * 0.4):
            if "maimed" not in tags: 
                tags.append("maimed")
                if "staggered" not in tags: tags.append("staggered")
                trauma_msg = f"\ud83e\ude78 [TRAUMA] {entity['name']} suffers a massive blow and is MAIMED!"
                
        if entity["hp"] > 0 and entity["hp"] <= (max_hp * 0.25):
            if "bleeding" not in tags:
                tags.append("bleeding")
                if not trauma_msg:
                    trauma_msg = f"\ud83e\ude78 [TRAUMA] {entity['name']} is heavily wounded and BLEEDING!"
                else:
                    trauma_msg += " and BLEEDING!"

        if entity["hp"] <= 0:
            entity["hp"] = 0
            if "hostile" in entity.get("tags", []): entity["tags"].remove("hostile")
            if "dead" not in entity.get("tags", []): entity["tags"].append("dead")
            return True, f"\ud83d\udc80 {entity['name']} has fallen." 
            
        return False, trauma_msg
            
    elif damage_type == "mental" and "composure" in entity:
        entity["composure"] -= amount
        max_comp = get_max_composure(entity)
        tags = entity.setdefault("tags", [])
        trauma_msg = ""
        
        if amount >= (max_comp * 0.4):
            if "shaken" not in tags:
                tags.append("shaken")
                trauma_msg = f"\ud83e\udde0 [MENTAL TRAUMA] {entity['name']}'s resolve is SHAKEN!"
        
        if entity["composure"] <= 0:
            entity["composure"] = 0
            if "broken" not in tags: tags.append("broken")
            # In Social Combat, 'broken' usually ends the fight with compliance
            return True, f"\ud83c\udff3\ufe0f {entity['name']}'s will scales. They are BROKEN."

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

    # Support for multi-stat skills (e.g. "Charm+Logic")
    if "+" in stat_name:
        stats = stat_name.split("+")
        bonus = sum(get_stat(entity, s.strip()) for s in stats)
    else:
        bonus = get_stat(entity, stat_name)

    total = base_roll + bonus
    return total, roll_log

def regenerate_resources(entity):
    res = entity.setdefault("resources", {})
    max_s = get_max_stamina(entity)
    max_f = get_max_focus(entity)
    
    res["stamina"] = min(max_s, res.get("stamina", 0) + 2)
    res["focus"] = min(max_f, res.get("focus", 0) + 2)
    
    if "composure" in entity:
        entity["composure"] = min(get_max_composure(entity), entity["composure"] + 1)
