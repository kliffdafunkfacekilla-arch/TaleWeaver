import random
import math

# Reputation Tiers
REPUTATION_TIERS = {
    "OUTCAST": {"min": -100, "max": -81, "reaction": "Hostile", "price_mod": 2.0},
    "HOSTILE": {"min": -80, "max": -41, "reaction": "Wary", "price_mod": 1.5},
    "NEUTRAL": {"min": -40, "max": 10, "reaction": "Neutral", "price_mod": 1.0},
    "LIKED": {"min": 11, "max": 40, "reaction": "Friendly", "price_mod": 0.9},
    "ALLIED": {"min": 41, "max": 80, "reaction": "Helpful", "price_mod": 0.7},
    "CHAMPION": {"min": 81, "max": 100, "reaction": "Exalted", "price_mod": 0.5}
}

def get_reputation_tier(value):
    """Returns the tier name based on a numeric value."""
    for tier, bounds in REPUTATION_TIERS.items():
        if bounds["min"] <= value <= bounds["max"]:
            return tier
    return "NEUTRAL"

def get_stat(entity, stat_name):
    """Retrieves a base stat or a derived/buffed value."""
    base = entity.get("stats", {}).get(stat_name, 5)
    bonus = get_gear_bonus(entity, stat_name)
    return base + bonus

def get_gear_bonus(entity, stat_name):
    """Scans tags for stat modifiers (e.g., 'bonus_Might_2')."""
    bonus = 0
    for tag in entity.get("tags", []):
        if tag.startswith(f"bonus_{stat_name}_"):
            try: bonus += int(tag.split("_")[-1])
            except: pass
    return bonus

def get_derived_stats(entity):
    s = entity.get("stats", {})
    return {
        "Movement": 3 + (s.get("Reflexes", 5) // 3),
        "Perception": 10 + s.get("Awareness", 5),
        "Defense": 10 + s.get("Reflexes", 5),
        "Willpower": 10 + s.get("Willpower", 5)
    }

def get_max_stamina(entity):
    return 10 + (entity.get("stats", {}).get("Endurance", 5) * 2)

def get_max_focus(entity):
    return 10 + (entity.get("stats", {}).get("Knowledge", 5) * 2)

def get_max_composure(entity):
    s = entity.get("stats", {})
    return 20 + s.get("Willpower", 5) + s.get("Intuition", 5)

def refresh_beats(entity):
    """Resets action beats for a new turn pulse."""
    max_beats = 2 + (entity.get("stats", {}).get("Finesse", 5) // 4)
    entity["beats"] = {"move": max_beats, "stamina": 1, "focus": 1}

def consume_beat(entity, beat_type):
    if entity.get("beats", {}).get(beat_type, 0) > 0:
        entity["beats"][beat_type] -= 1
        return True
    return False

def regenerate_resources(entity):
    """Passive recovery per turn."""
    res = entity.setdefault("resources", {})
    res["stamina"] = min(res.get("max_stamina", 10), res.get("stamina", 0) + 2)
    res["focus"] = min(res.get("max_focus", 10), res.get("focus", 0) + 1)
    
    # Composure regeneration
    entity["composure"] = min(get_max_composure(entity), entity.get("composure", 20) + 1)

def roll_check(entity, stat_expression):
    """Handles multi-stat rolls (e.g. 'Charm+Logic')."""
    stats = stat_expression.split('+')
    bonus = sum(get_stat(entity, s.strip()) for s in stats)
    roll = random.randint(1, 20)
    total = roll + bonus
    return total, f"({roll} + {bonus})"

def apply_damage(entity, amount, damage_type="physical"):
    """Reduces HP or Composure and applies trauma tags."""
    if damage_type == "physical":
        entity["hp"] = max(0, entity.get("hp", 0) - amount)
        if entity["hp"] <= 0:
            entity["tags"] = list(set(entity.get("tags", []) + ["dead"]))
            return True, "DEAD"
    else: # Mental/Social damage
        entity["composure"] = max(0, entity.get("composure", 0) - amount)
        if entity["composure"] <= 0:
            new_tags = ["broken", "shaken"]
            entity["tags"] = list(set(entity.get("tags", []) + new_tags))
            return True, "SHAKEN"
    return False, None

def get_movement_speed(entity):
    return 3 + (get_stat(entity, "Reflexes") // 3)

def get_weapon_stats(entity):
    # Default weapon if none equipped
    return {"range": 1, "die": 6, "flat": 1, "cost": 3}

def get_attack_stat(entity):
    return "Might" if random.random() > 0.5 else "Reflexes"

def get_defense_stat(entity):
    return "Reflexes"
