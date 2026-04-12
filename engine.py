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

def start_new_game():
    db_manager.reset_world()
    map_generator.generate_local_map([0,0], [25,25])
    state = None
    for _ in range(5):
        try:
            with open("local_map_state.json", "r") as f: state = json.load(f); break
        except: time.sleep(0.01)
    
    if not state: state = {"entities": [], "meta": {"clock": 0, "global_pos": [0,0]}}
    state.setdefault("meta", {})["clock"] = 0 
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
        print("\n[System] Threat eliminated. Returning to Explore Mode.")
        return True
        
    px, py = player["pos"]
    all_far = True
    for h in hostiles:
        hx, hy = h["pos"]
        if max(abs(px - hx), abs(py - hy)) <= 12:
            all_far = False; break
    if all_far:
        state["meta"]["in_combat"] = False
        print("\n[System] Distance maintained. Enemies have lost interest.")
        return True
    return False

def execute_world_turn(state):
    player = next((e for e in state.get("entities", []) if e.get("type") == "player"), None)
    if not player or "dead" in player.get("tags", []): return
    
    if "clock" not in state["meta"]: state["meta"]["clock"] = 0
    state["meta"]["clock"] += 1
        
    npc_logs = []
    # PROCESS AI PULSE
    for npc in state.get("entities", []):
        if (npc.get("type") == "hostile" or "hostile" in npc.get("tags", [])) and npc.get("hp", 0) > 0:
            res = execute_npc_pulse(state, npc, player)
            if res: npc_logs.append(res)
                
    if npc_logs:
        prev = state.get("latest_action", {}).get("mechanical_result", "")
        state.setdefault("latest_action", {})["mechanical_result"] = prev + " " + " ".join(npc_logs)

def execute_npc_pulse(state, npc, player):
    """
    NPC Brain 2.0: Strategic pulse management.
    1. Refresh Beats (3 per pulse).
    2. Skill Primary Check (Range & Resources).
    3. Fallback Movement.
    4. Fallback Basic Attack.
    5. Regeneration.
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
        # Lookup categorization (Body vs Mind)
        skill_data = None
        skill_type = "stamina"
        for stat, data in skills_db.get("tactics", {}).items():
            for tier, t_data in data.get("tiers", {}).items():
                if t_data.get("name") == skill_name:
                    skill_data = t_data; skill_type = "stamina"; break
            if skill_data: break
        if not skill_data:
            for school, data in skills_db.get("anomalies", {}).items():
                for tier, a_data in data.get("tiers", {}).items():
                    if a_data.get("name") == skill_name:
                        skill_data = a_data; skill_type = "focus"; break
                if skill_data: break
        
        if not skill_data: continue
        
        # Range Check: S-Die = 1, F-Die = 5 (Inferred)
        s_cost = skill_data.get("cost", {}).get("primary", skill_data.get("cost", {}).get("stamina", 0))
        f_cost = skill_data.get("cost", {}).get("secondary", skill_data.get("cost", {}).get("focus", 0))
        
        needed_range = 1 if skill_type == "stamina" else 5
        if dist <= needed_range:
            # Resource Check
            if npc["resources"].get("stamina", 0) >= s_cost and npc["resources"].get("focus", 0) >= f_cost:
                # Beat Check
                if entities.consume_beat(npc, skill_type):
                    return execute_skill_action(npc_id, player_id, skill_name)

    # --- 2. FALLBACK MOVEMENT ---
    if dist > 1 and entities.consume_beat(npc, "move"):
        step_x = 1 if dx > 0 else (-1 if dx < 0 else 0)
        step_y = 1 if dy > 0 else (-1 if dy < 0 else 0)
        dest = [nx + step_x, ny + step_y]
        
        # Multi-stage collision check
        collision = any(e["pos"] == dest and (e.get("hp", 0) > 0 or "solid" in e.get("tags", [])) for e in state.get("entities", []))
        if not collision:
            npc["pos"] = dest
            # If distance is still closed, try a basic attack next (if beat remains)
            dist = max(abs(px - dest[0]), abs(py - dest[1]))

    # --- 3. FALLBACK ATTACK ---
    if dist <= entities.get_weapon_stats(npc)["range"]:
        if entities.consume_beat(npc, "stamina"):
            return execute_attack(npc_id, player_id)

    # --- 4. END TURN REGEN ---
    entities.regenerate_resources(npc)
    return None

def apply_status_tag(entity, new_tag):
    """
    Applies a status tag while enforcing the Elite Resilience Protocol:
    1. Anti-Stacking CC (New CC overwrites old CC).
    2. Diminishing Returns (Immunity gained after status).
    """
    tags = entity.setdefault("tags", [])
    
    # ELITE OVERRIDE PROTOCOL
    cc_tags = ["staggered", "stunned", "confused", "terrified", "immobilized", "blinded", "broken_armor"]
    is_elite = "elite" in tags or "titan" in tags

    if is_elite and new_tag in cc_tags:
        # Check Diminishing Returns (Did they just recover from this?)
        if f"immune_{new_tag}" in tags:
            print(f"🛡️ [Elite Resilience] {entity.get('name', 'Entity')} is temporarily immune to {new_tag}!")
            return False
            
        # Strip existing CC tags to prevent stacking
        for existing_cc in cc_tags:
            if existing_cc in tags:
                tags.remove(existing_cc)
                print(f"🛡️ [Elite Resilience] {new_tag.capitalize()} overwrote {existing_cc.capitalize()}!")
                
        # Apply the new tag and log the future immunity
        if new_tag not in tags: tags.append(new_tag)
        # Note: immune_{new_tag} will persist until cleared at end of round
        if f"immune_{new_tag}" not in tags: tags.append(f"immune_{new_tag}") 
        return True
    else:
        # Standard entities or non-CC tags
        if new_tag not in tags: tags.append(new_tag)
        return True

def end_player_turn():
    """Ends round, triggers enemies, and resets pulse economy."""
    state = load_state()
    player = next((e for e in state.get("entities", []) if e.get("type") == "player"), None)
    if not player or "dead" in player.get("tags", []): return

    check_encounter_end(state, player)
    execute_world_turn(state) 
    
    # Refresh Beats AFTER clearing statuses
    for e in state.get("entities", []):
        tags = e.setdefault("tags", [])
        
        # Clear temporary battle-state tags
        for t in ["has_defended", "disengaging", "staggered", "stunned", "prone"]:
            if t in tags: tags.remove(t)
            
        # Clear 'immune_' tags if they don't have the status anymore
        for t in list(tags):
            if t.startswith("immune_"):
                tags.remove(t)
            
    entities.refresh_beats(player)
    
    # LOADOUT REGENERATION MATH
    total_weight = 0
    for slot, item in player.get("equipment", {}).items():
        if item and item != "None": total_weight += entities.get_item_weight(item)
    
    capacity = player.get("stats", {}).get("Endurance", 10) 
    loadout_percent = (total_weight / capacity) * 100 if capacity > 0 else 100
    
    if loadout_percent <= 50: regen_amount = 3
    elif loadout_percent <= 75: regen_amount = 2
    elif loadout_percent <= 100: regen_amount = 2
    else: regen_amount = 1 
    
    curr_s = player["resources"].get("stamina", 0)
    curr_f = player["resources"].get("focus", 0)
    player["resources"]["stamina"] = max(0, min(10, curr_s + regen_amount))
    player["resources"]["focus"] = max(0, min(10, curr_f + regen_amount))
    
    save_state(state)

def end_encounter():
    state = load_state()
    state.setdefault("meta", {})["in_combat"] = False
    save_state(state)

def execute_clash(state, actor, target, actor_tactic, target_tactic):
    matrix = {"Press": ["Maneuver", "Trick"], "Hold": ["Press", "Feint"], "Trick": ["Hold", "Disengage"], "Maneuver": ["Hold", "Press"], "Disengage": ["Press", "Maneuver"], "Feint": ["Trick", "Disengage"]}
    actor_name = actor["name"]; target_name = target["name"]
    if target_tactic in matrix.get(actor_tactic, []):
        apply_status_tag(target, "staggered")
        res = f"CLASH WON! {actor_name} used {actor_tactic} to overwhelm {target_name}. Enemy is STAGGERED."
    elif actor_tactic in matrix.get(target_tactic, []):
        apply_status_tag(actor, "staggered")
        res = f"CLASH LOST! {target_name} countered with {target_tactic}. {actor_name} is STAGGERED."
    else:
        res = f"STANDOFF! Both {actor_name} and {target_name} parried tactics."
    return res

def execute_attack(actor_id, target_id):
    state = load_state()
    actor = next((e for e in state.get("entities", []) if e.get("id") == actor_id or e.get("name") == actor_id), None)
    target = next((e for e in state.get("entities", []) if e.get("id") == target_id or e.get("name") == target_id), None)
    if not actor or not target: return "ERROR: Combatants not found."
    
    actor_name, target_name = actor["name"], target["name"]
    if "dead" in target.get("tags", []): return f"{target_name} is already finished."
    
    w_stats = entities.get_weapon_stats(actor)
    weapon_tags = w_stats.get("tags", [])
    
    is_combat = state.setdefault("meta", {}).get("in_combat", False)
    if not is_combat:
        state["meta"]["in_combat"] = True; entities.refresh_beats(actor) 
    else:
        # Beats should have been consumed by execute_npc_pulse OR the player loop
        # We don't double-consume here if we came from NPC pulse logic
        pass

    if actor["resources"].get("stamina", 0) < w_stats["cost"]:
        return f"{actor_name} is too exhausted (Stamina tokens required: {w_stats['cost']})!"
    
    # NPCs spending tokens
    actor["resources"]["stamina"] -= w_stats["cost"]
        
    dx, dy = abs(actor["pos"][0] - target["pos"][0]), abs(actor["pos"][1] - target["pos"][1])
    if max(dx, dy) > w_stats["range"]:
        return f"Target out of range."

    target_tags = target.get("tags", [])
    if "brittle" in target_tags and "brutal" in weapon_tags:
        if target.get("type") == "prop" or "environment" in target_tags:
            entities.apply_damage(target, 999, "physical")
            mech_result = f"CRITICAL MASS! Brittle {target_name} shattered!"
            state["latest_action"] = {"actor": actor_name, "action": "Attack", "target": target_name, "mechanical_result": mech_result}
            save_state(state); return mech_result
        else: brittle_bonus = 2
    else: brittle_bonus = 0

    attack_total, att_log = entities.roll_check(actor, "Might")
    def_stat = "Aegis" if entities.get_stat(target, "Aegis") > 0 else "Reflexes"
    defense_total, def_log = entities.roll_check(target, def_stat)
        
    if attack_total == defense_total:
        mech_result = execute_clash(state, actor, target, entities.get_best_clash_tactic(actor), entities.get_best_clash_tactic(target))
    elif attack_total > defense_total: 
        actor_might = entities.get_stat(actor, "Might")
        damage = max(1, random.randint(1, w_stats["die"]) + w_stats["flat"] + actor_might + brittle_bonus)
        is_dead = entities.apply_damage(target, damage, "physical")
        mech_result = f"HIT! {damage} dmg. {target_name} has {target['hp']} HP." if not is_dead else f"KILL! {damage} dmg. {target_name} is DEAD."
    else: 
        mech_result = f"MISS! {target_name} defended."
                
    state["latest_action"] = {"actor": actor_name, "action": "Strike", "target": target_name, "mechanical_result": mech_result}
    save_state(state); return mech_result

def execute_move(actor_id, dest_x, dest_y):
    # This is primarily for PLAYERS. NPCs move via execute_npc_pulse logic now.
    state = load_state()
    actor = next((e for e in state.get("entities", []) if e.get("id") == actor_id or e.get("name") == actor_id), None)
    if not actor or "dead" in actor.get("tags", []): return "Action failed."
    
    is_combat = state.get("meta", {}).get("in_combat", False)
    
    dx, dy = abs(actor["pos"][0] - dest_x), abs(actor["pos"][1] - dest_y)
    max_dist = 1
    if max(dx, dy) > max_dist: return f"Move too far!"
    
    # PULSE RESTRICTION only applies in combat
    if is_combat:
        if not entities.consume_beat(actor, "move"): return "No Move Beats!"
        if not entities.spend_stamina(actor, 1): return "Exhausted!"
    
    actor["pos"] = [dest_x, dest_y]
    state["latest_action"] = {"actor": actor["name"], "action": "Movement", "target": f"[{dest_x}, {dest_y}]", "mechanical_result": "Moved."}
    save_state(state)
    return "Moved."

def execute_transition(dest_x, dest_y):
    state = load_state()
    player_data = next((e for e in state.get("entities", []) if e.get("type") == "player"), None)
    grid_w, grid_h = state["meta"]["grid_size"]
    global_pos = state["meta"].get("global_pos", [0, 0])
    old_g_x, old_g_y = global_pos[0], global_pos[1]
    if player_data: state["entities"].remove(player_data)
    db_manager.save_chunk(old_g_x, old_g_y, state)
    new_g_x, new_g_y = old_g_x, old_g_y; entry_x, entry_y = dest_x, dest_y
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
    return "Transition complete."

def execute_examine(actor_id, target_id):
    state = load_state()
    actor = next((e for e in state.get("entities", []) if e.get("id") == actor_id or e.get("name") == actor_id), None)
    target = next((e for e in state.get("entities", []) if e.get("id") == target_id or e.get("name") == target_id), None)
    if not actor or not target: return "Error"
    state["latest_action"] = {"actor": actor["name"], "action": "Examine", "target": target["name"], "mechanical_result": "Examining."}
    state["ai_directive"] = f"NARRATOR MODE: Describe this in 2 sentences. Tags: {target.get('tags', [])}."
    save_state(state); return "Examining."

def execute_examine_area(actor_id, dest_x, dest_y):
    state = load_state()
    actor = next((e for e in state.get("entities", []) if e.get("id") == actor_id or e.get("name") == actor_id), None)
    if not actor: return "Error"
    state["latest_action"] = {"actor": actor["name"], "action": "Scan Area", "target": f"[{dest_x}, {dest_y}]", "mechanical_result": "Scanning."}
    state["ai_directive"] = f"NARRATOR MODE: Describe this environment. Tags: {state.get('meta', {}).get('map_tags', [])}."
    save_state(state); return "Scanning."

def execute_loot(actor_id, target_id):
    state = load_state()
    actor = next((e for e in state.get("entities", []) if e.get("id") == actor_id or e.get("name") == actor_id), None)
    target = next((e for e in state.get("entities", []) if e.get("id") == target_id or e.get("name") == target_id), None)
    if not actor or not target: return "Error"
    if max(abs(actor["pos"][0] - target["pos"][0]), abs(actor["pos"][1] - target["pos"][1])) > 1: return "Too far."
    
    if entities.loot_all(actor, target): 
        state["latest_action"] = {"actor": actor["name"], "action": "Loot", "target": target["name"], "mechanical_result": "Looted supplies."}
        save_state(state); return "Looted."
    return "Empty."

def execute_equip(actor_id, item_name):
    state = load_state(); actor = next((e for e in state["entities"] if e["id"] == actor_id or e["type"] == "player"), None)
    if actor and entities.equip_item(actor, item_name): save_state(state)

def execute_unequip(actor_id, slot):
    state = load_state(); actor = next((e for e in state["entities"] if e["id"] == actor_id or e["type"] == "player"), None)
    if actor and entities.unequip_item(actor, slot): save_state(state)

def execute_drop(actor_id, item_name):
    state = load_state(); actor = next((e for e in state["entities"] if e["id"] == actor_id or e["type"] == "player"), None)
    if actor and item_name in actor.get("inventory", []):
        actor["inventory"].remove(item_name)
        state["entities"].append({"name": f"Dropped {item_name}", "type": "prop", "pos": list(actor["pos"]), "tags": ["item", "container"], "inventory": [item_name], "hp": 1})
        save_state(state)

def execute_use(actor_id, item_name):
    state = load_state()
    actor = next((e for e in state["entities"] if e["id"] == actor_id or e["type"] == "player"), None)
    if not actor or item_name not in actor.get("inventory", []): return "No item."
    items = entities.load_items()
    item_data = items.get("consumables", {}).get(item_name)
    if not item_data: return "No data."
    eff = item_data.get("effect", {})
    if eff.get("stat") == "hp": actor["hp"] = min(20, actor["hp"] + eff.get("val", 0))
    actor["inventory"].remove(item_name); save_state(state); return "Used."

def execute_skill_action(actor_id, target_id, skill_name):
    state = load_state()
    actor = next((e for e in state.get("entities", []) if e.get("id") == actor_id or e.get("name") == actor_id), None)
    target = next((e for e in state.get("entities", []) if e.get("id") == target_id or e.get("name") == target_id), None)
    if not actor or not target: return "Error"

    skills_db = entities.load_skills()
    skill_data = None
    stat_used = ""

    for stat, data in skills_db.get("tactics", {}).items():
        for tier, t_data in data.get("tiers", {}).items():
            if t_data.get("name") == skill_name:
                skill_data = t_data; stat_used = stat; break
        if skill_data: break
    if not skill_data:
        for school, data in skills_db.get("anomalies", {}).items():
            for tier, a_data in data.get("tiers", {}).items():
                if a_data.get("name") == skill_name:
                    skill_data = a_data; stat_used = school; break
            if skill_data: break

    if not skill_data: return "Skill missing."

    cost = skill_data.get("cost", {})
    s_cost = cost.get("primary", cost.get("stamina", 0))
    f_cost = cost.get("secondary", cost.get("focus", 0))
    
    # Costs are already handled in NPC pulse or Player loop, but we double check pool here
    if actor["resources"].get("stamina", 0) < s_cost or actor["resources"].get("focus", 0) < f_cost:
        return "Exhausted!"

    actor["resources"]["stamina"] -= s_cost
    actor["resources"]["focus"] -= f_cost

    roll_total, roll_log = entities.roll_check(actor, stat_used)
    success = roll_total >= 12

    if success: mech_result = resolve_skill_tags(actor, target, skill_data, state)
    else: mech_result = f"{skill_name} FAILED ({roll_total} vs 12)."

    state["latest_action"] = {"actor": actor["name"], "action": skill_name, "target": target["name"], "mechanical_result": mech_result}
    save_state(state); return mech_result

def resolve_skill_tags(actor, target, skill_data, state):
    tags = skill_data.get("tags", [])
    result_parts = []
    if "push" in tags:
        ax, ay = actor["pos"]; tx, ty = target["pos"]; dx, dy = tx - ax, ty - ay
        nx, ny = (1 if dx > 0 else -1 if dx < 0 else 0), (1 if dy > 0 else -1 if dy < 0 else 0)
        dest = [tx + nx, ty + ny]
        collision = any(e["pos"] == dest and e.get("hp", 0) > 0 for e in state.get("entities", []))
        if not collision:
            target["pos"] = dest
            result_parts.append(f"Pushed {target['name']}!")
        else:
            result_parts.append(f"{target['name']} hit cover!"); entities.apply_damage(target, 2)
    if "apply_status" in tags:
        for t in tags:
            if t not in ["apply_status", "push"]:
                if apply_status_tag(target, t): result_parts.append(f"Applied {t.replace('_', ' ').capitalize()}.")
    if not result_parts: result_parts.append(f"Skill {skill_data['name']} resolved.")
    return " ".join(result_parts)

def execute_stat_action(actor_id, target_id, action_str):
    state = load_state()
    actor = next((e for e in state.get("entities", []) if e.get("id") == actor_id or e.get("type") == "player"), None)
    target = next((e for e in state.get("entities", []) if e.get("id") == target_id or e.get("name") == target_id), None)
    if not actor or not target: return "Error"
    try: stat_part, action_name = action_str.split("] ", 1); stat_used = stat_part.strip("[")
    except: return "Format err."
    
    beat_type = "stamina" if stat_used in ["Might", "Endurance", "Finesse", "Reflexes", "Vitality", "Fortitude"] else "focus"
    if not entities.consume_beat(actor, beat_type): return "No Pulse Beats!"
    
    action_data = actions.ACTION_REGISTRY.get(action_name); cost_val = action_data["cost"]["val"] if action_data else 1
    cost_type = action_data["cost"]["type"] if action_data else "stamina"
    if actor["resources"].get(cost_type, 0) < cost_val: return "Exhausted!"
    
    actor["resources"][cost_type] -= cost_val
    roll_total, _ = entities.roll_check(actor, stat_used)
    
    success = roll_total >= 12
    mech_result = f"SUCCESS: {action_name}!" if success else f"FAILED: {action_name}."
    state["latest_action"] = {"actor": actor["name"], "action": action_str, "target": target["name"], "mechanical_result": mech_result}
    save_state(state); return mech_result
