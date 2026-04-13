import json
import random
import os
import time
import map_generator
import entities
import db_manager
import actions

def load_state():
    """Loads the map state with a retry loop to handle Windows file-sharing collisions."""
    if not os.path.exists("local_map_state.json"): return start_new_game()
    
    for _ in range(5):
        try:
            with open("local_map_state.json", "r") as f:
                data = json.load(f)
                if "entities" not in data: return start_new_game()
                return data
        except (PermissionError, json.JSONDecodeError):
            time.sleep(0.01) # Tiny wait for the other thread/process to release the file
            continue
        except Exception:
            return start_new_game()
    return start_new_game()

def save_state(state):
    """Saves the state with a brief retry for high-frequency writes."""
    for _ in range(5):
        try:
            with open("local_map_state.json", "w") as f: 
                json.dump(state, f, indent=2)
            break
        except PermissionError:
            time.sleep(0.01)
            continue

    g_pos = state.get("meta", {}).get("global_pos", [0,0])
    db_manager.save_chunk(g_pos[0], g_pos[1], state)

def log_message(msg):
    """Redirects events to the persistent combat log in the game state."""
    state = load_state()
    log = state.setdefault("combat_log", [])
    log.append(msg)
    # Keep last 15 items
    state["combat_log"] = log[-15:]
    save_state(state)
    print(f"[Log] {msg}")

def start_new_game():
    db_manager.reset_world()
    map_generator.generate_local_map([0,0], [25,25])
    state = None
    for _ in range(5):
        try:
            with open("local_map_state.json", "r") as f: state = json.load(f); break
        except: time.sleep(0.01)
    
    if not state: state = {"entities": [], "meta": {"clock": 0, "global_pos": [0,0]}, "combat_log": []}
    meta = state.setdefault("meta", {})
    meta["clock"] = 0 
    meta["campaign_tracker"] = {
        "main_plot": "Hunting the bandits who burned your village.",
        "active_subplot": None,
        "quest_history": [],
        "active_quest_deck": []
    }
    state.setdefault("combat_log", ["Director: Welcome to Shatterlands."])
    player = next((e for e in state["entities"] if e["type"] == "player"), None)
    if player: entities.refresh_beats(player)
    save_state(state)
    return state

def check_encounter_end(state, player):
    """Checks if combat should end based on hostile distance or death."""
    if not state.get("meta", {}).get("in_combat", False): return False
    
    hostiles = [e for e in state.get("entities", []) if "hostile" in e.get("tags", []) and e.get("hp", 0) > 0]
    if not hostiles:
        state["meta"]["in_combat"] = False
        log_message("Threat eliminated. Returning to Explore Mode.")
        return True
        
    px, py = player["pos"]
    all_far = True
    for h in hostiles:
        hx, hy = h["pos"]
        if max(abs(px - hx), abs(py - hy)) <= 12:
            all_far = False; break
    if all_far:
        state["meta"]["in_combat"] = False
        log_message("Distance maintained. Leveling threat alert.")
        return True
    return False

def execute_world_turn(state):
    player = next((e for e in state.get("entities", []) if e.get("type") == "player"), None)
    if not player or "dead" in player.get("tags", []): return ""
    
    if "clock" not in state["meta"]: state["meta"]["clock"] = 0
    state["meta"]["clock"] += 1
        
    # 1. Gather all active hostiles
    active_hostiles = [npc for npc in state.get("entities", []) 
                       if (npc.get("type") == "hostile" or "hostile" in npc.get("tags", [])) 
                       and npc.get("hp", 0) > 0]
                       
    # 2. EXECUTION ADVANTAGE: Sort by Movement stat (Highest goes first)
    active_hostiles.sort(key=lambda x: entities.get_derived_stats(x).get("Movement", 5), reverse=True)

    # 3. PROCESS AI PULSE IN INITIATIVE ORDER
    for npc in active_hostiles:
        execute_npc_pulse(state, npc, player)

def execute_npc_pulse(state, npc, player):
    """
    NPC Brain 2.0: Strategic pulse management.
    """
    entities.refresh_beats(npc)
    npc_id = npc.get("id", npc["name"])
    player_id = player.get("id", player["name"])
    
    px, py = player["pos"]
    nx, ny = npc["pos"]
    dx, dy = px - nx, py - ny
    dist = max(abs(dx), abs(dy))
    
    skills_db = entities.load_skills()
    
    # --- 1. EVALUATE SKILLS ---
    for skill_name in npc.get("skills", []):
        skill_data = None; skill_type = "stamina"
        for stat, data in skills_db.get("tactics", {}).items():
            for tier, t_data in data.get("tiers", {}).items():
                if t_data.get("name") == skill_name: skill_data = t_data; skill_type = "stamina"; break
            if skill_data: break
        if not skill_data:
            for school, data in skills_db.get("anomalies", {}).items():
                for tier, a_data in data.get("tiers", {}).items():
                    if a_data.get("name") == skill_name: skill_data = a_data; skill_type = "focus"; break
                if skill_data: break
        
        if skill_data:
            s_cost = skill_data.get("cost", {}).get("primary", skill_data.get("cost", {}).get("stamina", 0))
            f_cost = skill_data.get("cost", {}).get("secondary", skill_data.get("cost", {}).get("focus", 0))
            needed_range = 1 if skill_type == "stamina" else 5
            if dist <= needed_range:
                if npc["resources"].get("stamina", 0) >= s_cost and npc["resources"].get("focus", 0) >= f_cost:
                    return execute_skill_action(npc_id, player_id, skill_name)

    # --- 2. FALLBACK MOVEMENT ---
    if dist > 1 and entities.consume_beat(npc, "move"):
        speed = entities.get_movement_speed(npc)
        for _ in range(speed):
            if dist <= 1: break
            step_x = 1 if dx > 0 else (-1 if dx < 0 else 0)
            step_y = 1 if dy > 0 else (-1 if dy < 0 else 0)
            dest = [npc["pos"][0] + step_x, npc["pos"][1] + step_y]
            collision = any(e["pos"] == dest and (e.get("hp", 0) > 0 or "solid" in e.get("tags", [])) for e in state.get("entities", []))
            if not collision:
                npc["pos"] = dest
                nx, ny = npc["pos"]
                dx, dy = px - nx, py - ny
                dist = max(abs(dx), abs(dy))
            else: break
        
        # PERCEPTION CHECK
        p_stats = entities.get_derived_stats(player)
        if dist <= p_stats.get("Perception", 8):
            log_message(f"🏃 {npc['name']} closes the gap.")

    # --- 3. FALLBACK ATTACK ---
    if dist <= entities.get_weapon_stats(npc)["range"]:
        return execute_attack(npc_id, player_id)

    entities.regenerate_resources(npc)

def apply_status_tag(entity, new_tag):
    tags = entity.setdefault("tags", [])
    cc_tags = ["staggered", "stunned", "confused", "terrified", "immobilized", "blinded", "broken_armor", "grappled"]
    is_elite = "elite" in tags or "titan" in tags

    if is_elite and new_tag in cc_tags:
        if f"immune_{new_tag}" in tags: return False
        for ex_cc in cc_tags:
            if ex_cc in tags: tags.remove(ex_cc)
        if new_tag not in tags: tags.append(new_tag)
        if f"immune_{new_tag}" not in tags: tags.append(f"immune_{new_tag}") 
        return True
    else:
        if new_tag not in tags: tags.append(new_tag)
        return True

def end_player_turn():
    """Ends round, triggers enemies, and resets pulse economy."""
    state = load_state()
    player = next((e for e in state.get("entities", []) if e.get("type") == "player"), None)
    if not player or "dead" in player.get("tags", []): return "Game Over."

    check_encounter_end(state, player)
    execute_world_turn(state) 
    
    # --- BLEEDING RESOLUTION ---
    for e in state.get("entities", []):
        if "bleeding" in e.get("tags", []) and e.get("hp", 0) > 0:
            e["hp"] -= 1
            log_message(f"🩸 {e['name']} suffers 1 damage from bleeding.")
            if e["hp"] <= 0:
                e["hp"] = 0
                if "hostile" in e.get("tags", []): e["tags"].remove("hostile")
                if "dead" not in e.get("tags", []): e["tags"].append("dead")
                log_message(f"☠️ {e['name']} has bled out.")

    # Refresh Beats AFTER clearing statuses
    for e in state.get("entities", []):
        tags = e.setdefault("tags", [])
        for t in ["has_defended", "disengaging", "staggered", "stunned", "prone"]:
            if t in tags: tags.remove(t)
        for t in list(tags):
            if t.startswith("immune_"): tags.remove(t)
            
    entities.refresh_beats(player)
    
    # LOADOUT REGENERATION
    total_weight = 0
    for slot, item in player.get("equipment", {}).items():
        if item and item != "None": total_weight += entities.get_item_weight(item)
    capacity = entities.get_stat(player, "Endurance") or 10
    loadout_percent = (total_weight / capacity) * 100
    
    if loadout_percent <= 50: regen = 3
    elif loadout_percent <= 100: regen = 2
    else: regen = 1 
    
    player["resources"]["stamina"] = min(entities.get_max_stamina(player), player["resources"].get("stamina", 0) + regen)
    player["resources"]["focus"] = min(entities.get_max_focus(player), player["resources"].get("focus", 0) + regen)
    
    save_state(state)
    return "Pulse reset."

def execute_attack(actor_id, target_id):
    state = load_state()
    actor = next((e for e in state.get("entities", []) if e.get("id") == actor_id or e.get("name") == actor_id), None)
    target = next((e for e in state.get("entities", []) if e.get("id") == target_id or e.get("name") == target_id), None)
    if not actor or not target: return "Target missing."
    
    if not entities.consume_beat(actor, "stamina"):
        return f"{actor['name']} has no Stamina Beat left!"

    w_stats = entities.get_weapon_stats(actor)
    if actor["resources"].get("stamina", 0) < w_stats["cost"]:
        return f"Exhausted! (Need {w_stats['cost']} Stamina tokens)."
    actor["resources"]["stamina"] -= w_stats["cost"]

    # --- TRACK PROFICIENCY RESOLUTION ---
    att_stat = entities.get_attack_stat(actor)
    def_stat = entities.get_defense_stat(target)
    
    attack_total, _ = entities.roll_check(actor, att_stat)
    defense_total, _ = entities.roll_check(target, def_stat)
    
    # --- RANGED VS MELEE CONTEXT ---
    attack_type = "Ranged Attack" if w_stats["range"] > 1 else "Melee Attack"
    log_message(f"⚔️ {actor['name']} performs a {attack_type.lower()} on {target['name']}...")

    if attack_total > defense_total:
        # Damage scales with the Offense Track stat
        damage = max(1, random.randint(1, w_stats["die"]) + w_stats["flat"] + entities.get_stat(actor, att_stat))
        is_dead, trauma_msg = entities.apply_damage(target, damage)
        res = f"HIT for {damage} dmg!" + (" DEAD." if is_dead else "")
        log_message(f"   ↳ {res}")
        if trauma_msg: log_message(f"   ↳ {trauma_msg}")
    else:
        res = f"Missed."
        log_message(f"   ↳ {res}")
        
    state["latest_action"] = {
        "actor": actor["name"], 
        "action": attack_type, 
        "target": target["name"], 
        "mechanical_result": res,
        "weapon_used": w_stats["name"]
    }
    state["ai_directive"] = f"NARRATOR MODE: Describe a gritty {attack_type.lower()} using a {w_stats['name']}. 2 sentences."
    
    save_state(state)
    return res

def execute_move(actor_id, dest_x, dest_y):
    state = load_state()
    actor = next((e for e in state.get("entities", []) if e.get("id") == actor_id or e.get("name") == actor_id), None)
    if not actor or "dead" in actor.get("tags", []): return "Action failed."
    
    is_combat = state.get("meta", {}).get("in_combat", False)
    dx, dy = abs(actor["pos"][0] - dest_x), abs(actor["pos"][1] - dest_y)
    dist = max(dx, dy)
    
    speed = entities.get_movement_speed(actor)
    if dist > speed: return f"Distance too far! (Speed: {speed})"
    
    if is_combat:
        if not entities.consume_beat(actor, "move"): return "No Move Beats!"
        if not entities.spend_stamina(actor, 1): return "Exhausted!"
    
    actor["pos"] = [dest_x, dest_y]
    state["latest_action"] = {"actor": actor["name"], "action": "Move", "target": f"{dest_x},{dest_y}", "mechanical_result": "Moved."}
    save_state(state)
    return "Moved."

def execute_use(actor_id, item_name):
    state = load_state()
    actor = next((e for e in state.get("entities", []) if e.get("id") == actor_id or e.get("name") == actor_id), None)
    if not actor or item_name not in actor.get("inventory", []): return "Item missing."
    
    items_db = entities.load_items()
    item_data = items_db.get("consumables", {}).get(item_name)
    if not item_data: return "Cannot use this."
    
    effect = item_data.get("effect", {})
    stat = effect.get("stat")
    val = effect.get("val", 0)
    
    msg = f"Used {item_name}."
    if stat == "hp":
        actor["hp"] = min(actor.get("max_hp", 20), actor.get("hp", 0) + val)
        msg = f"Used {item_name} (+{val} HP)."
    elif stat == "composure":
        actor["composure"] = min(actor.get("max_composure", 20), actor.get("composure", 0) + val)
        msg = f"Used {item_name} (+{val} Composure)."
        
    if item_name == "Bandage" and "bleeding" in actor.get("tags", []):
        actor["tags"].remove("bleeding")
        msg += " Bleeding stopped."
        
    actor["inventory"].remove(item_name)
    log_message(f"💊 {actor['name']} {msg.lower()}")
    save_state(state)
    return msg

def execute_equip(actor_id, item_name):
    state = load_state()
    actor = next((e for e in state.get("entities", []) if e.get("id") == actor_id or e.get("name") == actor_id), None)
    if not actor: return "Actor missing."
    if entities.equip_item(actor, item_name):
        log_message(f"🛡️ {actor['name']} equipped {item_name}.")
        save_state(state); return f"Equipped {item_name}."
    return "Equip failed."

def execute_unequip(actor_id, slot):
    state = load_state()
    actor = next((e for e in state.get("entities", []) if e.get("id") == actor_id or e.get("name") == actor_id), None)
    if not actor: return "Actor missing."
    if entities.unequip_item(actor, slot):
        log_message(f"🎒 {actor['name']} unequipped {slot}.")
        save_state(state); return f"Unequipped {slot}."
    return "Unequip failed."

def execute_drop(actor_id, item_name):
    state = load_state()
    actor = next((e for e in state.get("entities", []) if e.get("id") == actor_id or e.get("name") == actor_id), None)
    if not actor or item_name not in actor.get("inventory", []): return "Item missing."
    actor["inventory"].remove(item_name)
    log_message(f"🗑️ {actor['name']} dropped {item_name}.")
    save_state(state); return f"Dropped {item_name}."

def execute_loot(actor_id, target_id):
    state = load_state()
    actor = next((e for e in state.get("entities", []) if e.get("id") == actor_id or e.get("name") == actor_id), None)
    target = next((e for e in state.get("entities", []) if e.get("id") == target_id or e.get("name") == target_id), None)
    if not actor or not target: return "Target missing."
    if entities.loot_all(actor, target):
        log_message(f"💰 {actor['name']} looted {target['name']}.")
        save_state(state); return f"Looted {target['name']}."
    return "Nothing to loot."

def execute_examine(actor_id, target_id):
    state = load_state()
    target = next((e for e in state.get("entities", []) if e.get("id") == target_id or e.get("name") == target_id), None)
    if not target: return "Target missing."
    tags = ", ".join(target.get("tags", []))
    res = f"{target['name']}: HP {target.get('hp','?')}, Tags: [{tags}]"
    log_message(f"👁️ {res}")
    return res

def execute_examine_area(actor_id, x, y):
    state = load_state()
    ents = [e for e in state.get("entities", []) if e["pos"] == [x, y]]
    if not ents: return "Nothing but the cold void here."
    res = ", ".join([e["name"] for e in ents])
    log_message(f"👁️ Area at {x},{y}: Found {res}")
    return f"Found {res}"

def execute_stat_action(actor_id, target_id, selection):
    """
    Handles actions like '[MIGHT] Bash' chosen from context menus.
    """
    state = load_state()
    actor = next((e for e in state.get("entities", []) if e.get("id") == actor_id or e.get("name") == actor_id), None)
    target = next((e for e in state.get("entities", []) if e.get("id") == target_id or e.get("name") == target_id), None)
    if not actor or not target: return "Error"
    
    try:
        stat_part, action_name = selection.split("] ")
        stat_name = stat_part.strip("[")
    except ValueError:
        return f"Unknown action: {selection}"

    action_data = actions.ACTION_REGISTRY.get(action_name)
    if not action_data: return "Action not found."

    cost = action_data.get("cost", {})
    if not entities.consume_beat(actor, cost.get("type", "stamina")):
        return f"No {cost['type'].capitalize()} Beat!"
    if not entities.spend_stamina(actor, cost.get("val", 0)):
         return "Exhausted!"

    log_message(f"🎲 {actor['name']} attempts {action_name} on {target['name']}...")
    roll_total, _ = entities.roll_check(actor, stat_name)
    
    if roll_total >= 14:
        if action_data["category"] == "Combat":
            is_dead, trauma = entities.apply_damage(target, 5)
            res = f"SUCCESS: Dealt 5 dmg!" + (" DEAD." if is_dead else "")
            if trauma: res += f" {trauma}"
        else:
            res = "SUCCESS: Effect triggered."
        log_message(f"   ↳ {res}")
    else:
        res = "FAILED."
        log_message(f"   ↳ {res}")
        
    save_state(state)
    return res

def execute_skill_action(actor_id, target_id, skill_name):
    state = load_state()
    actor = next((e for e in state.get("entities", []) if e.get("id") == actor_id or e.get("name") == actor_id), None)
    target = next((e for e in state.get("entities", []) if e.get("id") == target_id or e.get("name") == target_id), None)
    if not actor or not target: return "Error"

    skills_db = entities.load_skills()
    skill_data = None; stat_used = ""; beat_type = "stamina"

    for stat, data in skills_db.get("tactics", {}).items():
        for tier, t_data in data.get("tiers", {}).items():
            if t_data.get("name") == skill_name: skill_data = t_data; stat_used = stat; beat_type = "stamina"; break
        if skill_data: break
    if not skill_data:
        for school, data in skills_db.get("anomalies", {}).items():
            for tier, a_data in data.get("tiers", {}).items():
                if a_data.get("name") == skill_name: skill_data = a_data; stat_used = school; beat_type = "focus"; break
            if skill_data: break

    if not skill_data: return "Skill missing."
    if not entities.consume_beat(actor, beat_type): return f"No {beat_type.capitalize()} Beat left!"

    cost = skill_data.get("cost", {})
    s_cost = cost.get("primary", cost.get("stamina", 0))
    f_cost = cost.get("secondary", cost.get("focus", 0))
    
    if actor["resources"].get("stamina", 0) < s_cost or actor["resources"].get("focus", 0) < f_cost: return "Exhausted!"

    actor["resources"]["stamina"] -= s_cost
    actor["resources"]["focus"] -= f_cost
    
    log_message(f"🌀 {actor['name']} uses {skill_name} (-{s_cost}S, -{f_cost}F)")

    roll_total, _ = entities.roll_check(actor, stat_used)
    success = roll_total >= 12

    if success:
        mech_result = resolve_skill_tags(actor, target, skill_data, state)
        log_message(f"   ↳ SUCCESS: {mech_result}")
    else:
        mech_result = f"{skill_name} FAILED."
        log_message(f"   ↳ FAILED.")

    state["latest_action"] = {"actor": actor["name"], "action": skill_name, "target": target["name"], "mechanical_result": mech_result}
    save_state(state); return mech_result

def resolve_skill_tags(actor, target, skill_data, state):
    tags = skill_data.get("tags", [])
    result_parts = []
    
    if "push" in tags:
        ax, ay = actor["pos"]; tx, ty = target["pos"]; dx, dy = tx - ax, ty - ay
        nx, ny = (1 if dx > 0 else -1 if dx < 0 else 0), (1 if dy > 0 else -1 if dy < 0 else 0)
        dest = [tx + nx, ty + ny]
        if not any(e["pos"] == dest and e.get("hp", 0) > 0 for e in state.get("entities", [])):
            target["pos"] = dest; result_parts.append(f"Pushed {target['name']}")
        else:
            is_dead, trauma = entities.apply_damage(target, 2); result_parts.append(f"Wall-impact (2 dmg)")
            if trauma: result_parts.append(trauma)

    if "control" in tags or "grapple" in tags:
        apply_status_tag(target, "grappled")
        result_parts.append("Grappled")

    if "shred" in tags or "armor_crack" in tags:
        apply_status_tag(target, "broken_armor")
        result_parts.append("Armor Shredded")

    if "cc" in tags or "stun" in tags:
        apply_status_tag(target, "stunned")
        result_parts.append("Stunned")

    if "apply_status" in tags:
        for t in tags:
            if t not in ["apply_status", "push", "control", "grapple", "cc", "shred"]:
                if apply_status_tag(target, t): result_parts.append(t.replace('_', ' ').capitalize())

    if not result_parts: result_parts.append(f"Effect triggered")
    return ", ".join(result_parts)

import quest_manager

def investigate_seed(actor_id, target_id):
    """
    Triggers the Narrative Weaver to generate a quest card deck from a Story Seed.
    """
    state = load_state()
    actor = next((e for e in state.get("entities", []) if e.get("id") == actor_id or e.get("name") == actor_id), None)
    target = next((e for e in state.get("entities", []) if e.get("id") == target_id or e.get("name") == target_id), None)
    
    if not target or "story_seed" not in target.get("tags", []):
        return "Nothing special here."

    log_message(f"🔍 {actor['name']} investigates the {target['name']}...")
    
    # CALL THE WEAVER
    weaver_data = quest_manager.generate_story_glue(target["name"], state)
    deck = quest_manager.build_mechanical_deck(weaver_data, region_threat_level=1)
    
    # UPDATE CAMPAIGN
    tracker = state["meta"].setdefault("campaign_tracker", {})
    tracker["active_quest_deck"] = deck
    if not tracker.get("active_subplot"):
        tracker["active_subplot"] = weaver_data["story_hook"]
        
    log_message(f"📜 QUEST ACCEPTED: {weaver_data['story_hook']}")
    
    # CONSUME THE SEED
    target["tags"].remove("story_seed")
    if "used_seed" not in target["tags"]: target["tags"].append("used_seed")
    
    save_state(state)
    return "Quest started."

def execute_transition(dest_x, dest_y):
    state = load_state()
    player_data = next((e for e in state.get("entities", []) if e.get("type") == "player"), None)
    grid_w, grid_h = state["meta"]["grid_size"]
    global_pos = state["meta"].get("global_pos", [0, 0])
    if player_data: state["entities"].remove(player_data)
    db_manager.save_chunk(global_pos[0], global_pos[1], state)
    new_g_x, new_g_y = global_pos[0], global_pos[1]; entry_x, entry_y = dest_x, dest_y
    if dest_x >= grid_w - 1: new_g_x += 1; entry_x = 1
    elif dest_x <= 0: new_g_x -= 1; entry_x = grid_w - 2
    if dest_y >= grid_h - 1: new_g_y += 1; entry_y = 1
    elif dest_y <= 0: new_g_y -= 1; entry_y = grid_h - 2
    new_state = db_manager.load_chunk(new_g_x, new_g_y)
    if new_state:
        if player_data: player_data["pos"] = [entry_x, entry_y]; new_state["entities"].append(player_data)
        new_state["meta"]["clock"] = state["meta"].get("clock", 0); save_state(new_state)
    else:
        map_generator.generate_local_map([new_g_x, new_g_y], [entry_x, entry_y], player_data=player_data)
        new_state = load_state(); new_state["meta"]["clock"] = state["meta"].get("clock", 0); save_state(new_state)
    log_message(f"📍 Region Transition: {global_pos} ➔ {[new_g_x, new_g_y]}")
    return "Transition complete."
