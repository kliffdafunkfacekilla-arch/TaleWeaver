import random
import json

def load_items():
    try:
        with open("data/items.json", "r", encoding="utf-8") as f: return json.load(f)
    except: return {"weapons":{}, "armor":{}, "accessories":{}}

def loot_all(looter, target):
    if "inventory" not in target or not target["inventory"]: return False
    if "inventory" not in looter: looter["inventory"] = []
    looter["inventory"].extend(target["inventory"])
    target["inventory"] = [] 
    return True

def equip_item(entity, item_name):
    items = load_items()
    item_type = None
    # FIX: Hardcoded slot names so "armor" doesn't become "armo"
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
    items = load_items()
    bonus = 0
    equip = entity.get("equipment", {})
    armor = items.get("armor", {}).get(equip.get("armor"))
    acc = items.get("accessories", {}).get(equip.get("accessory"))
    
    if armor and stat_name == "Aegis": bonus += armor.get("aegis_bonus", 0)
    if acc and stat_name == "Awareness": bonus += acc.get("awareness_bonus", 0)
    return bonus

def get_stat(entity, stat_name):
    base = entity.get("stats", {}).get(stat_name, 0)
    if stat_name in ["Aegis", "Awareness"]: base += get_gear_bonus(entity, stat_name)
    return base

def get_derived_stats(entity):
    return {
        "Perception": get_stat(entity, "Awareness") + get_stat(entity, "Logic") + get_stat(entity, "Vitality"),
        "Stealth": get_stat(entity, "Knowledge") + get_stat(entity, "Charm") + get_stat(entity, "Finesse"),
        "Movement": get_stat(entity, "Reflexes") + get_stat(entity, "Might") + get_stat(entity, "Intuition"),
        "Balance": get_stat(entity, "Endurance") + get_stat(entity, "Fortitude") + get_stat(entity, "Willpower")
    }

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
    res = entity.get("resources", {})
    if res.get("stamina", 0) >= amount:
        res["stamina"] -= amount
        return True
    return False

def apply_damage(entity, amount, damage_type="physical"):
    if damage_type == "physical" and "hp" in entity:
        entity["hp"] -= amount
        if entity["hp"] <= 0:
            entity["hp"] = 0
            if "hostile" in entity.get("tags", []): entity["tags"].remove("hostile")
            if "dead" not in entity.get("tags", []): entity["tags"].append("dead")
            return True
    return False

def process_npc_turn(npc, player, map_data):
    if "dead" in npc.get("tags", []) or "player" in npc.get("tags", []): return None
    if "hostile" in npc.get("tags", []):
        dx = player["pos"][0] - npc["pos"][0]
        dy = player["pos"][1] - npc["pos"][1]
        distance = max(abs(dx), abs(dy)) 
        if distance <= 1: return {"action": "attack", "target": player["id"]}
        elif distance < 6:
            move_x = 1 if dx > 0 else (-1 if dx < 0 else 0)
            move_y = 1 if dy > 0 else (-1 if dy < 0 else 0)
            new_pos = [npc["pos"][0] + move_x, npc["pos"][1] + move_y]
            collision = any(e["pos"] == new_pos and ("solid" in e.get("tags", []) or e.get("hp", 0) > 0) for e in map_data.get("entities", []))
            if new_pos == player["pos"]: collision = True
            if not collision:
                npc["pos"] = new_pos
                return {"action": "move", "target": new_pos}
    return None
