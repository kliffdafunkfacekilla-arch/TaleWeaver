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
        
    npc_actions = []
    for npc in state.get("entities", []):
        if npc.get("type") == "hostile" and npc.get("hp", 0) > 0:
            entities.refresh_beats(npc)
            action = entities.process_npc_turn(npc, player, state)
            if action:
                if action["action"] == "attack":
                    npc_might = entities.get_stat(npc, "Might")
                    attack_roll, att_log = entities.roll_check(npc, "Might")
                    def_stat = "Aegis" if entities.get_stat(player, "Aegis") > 0 else "Reflexes"
                    defense_roll, def_log = entities.roll_check(player, def_stat)
                    
                    if attack_roll > defense_roll:
                        damage = max(1, random.randint(1, 4) + npc_might)
                        entities.apply_damage(player, damage, "physical")
                        log_msg = f"{npc['name']} rolled {attack_roll} vs Jax's {defense_roll}! Hit for {damage} dmg!"
                    else:
                        log_msg = f"{npc['name']} rolled {attack_roll}, but Jax avoided the strike!"
                    npc_actions.append(log_msg)
                
    if npc_actions:
        res = state.get("latest_action", {}).get("mechanical_result", "")
        state.setdefault("latest_action", {})["mechanical_result"] = res + " " + " ".join(npc_actions)

def apply_status_tag(entity, new_tag):
    """
    Applies a status tag while enforcing the Elite Resilience Protocol:
    1. Anti-Stacking CC (New CC overwrites old CC).
    2. Diminishing Returns (Immunity gained after status).
    """
    tags = entity.setdefault("tags", [])
    
    # ELITE OVERRIDE PROTOCOL
    cc_tags = ["staggered", "stunned", "confused", "terrified", "immobilized"]
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
        # 1. Aging Immunity: Tags ending in '_immune' signify a "cooldown" after a status.
        # We clear statuses first, but keep immunity until the NEXT turn.
        # Actually, let's simplify: status clears this turn, immunity clears next.
        
        # Clear temporary battle-state tags
        for t in ["has_defended", "disengaging", "staggered", "stunned", "prone"]:
            if t in tags: tags.remove(t)
            
        # Clear 'immune_' tags if they don't have the status anymore
        # (This implements the "Immune for 1 round" rule)
        for t in list(tags):
            if t.startswith("immune_"):
                # If the base status (e.g. 'stunned') is NOT in tags, this immunity is now active.
                # It will clear at the end of THIS turn, meaning it protected them for exactly one pulse cycle.
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
    
    # Get Dynamic Weapon Stats
    w_stats = entities.get_weapon_stats(actor)
    weapon_tags = w_stats.get("tags", [])
    
    is_combat = state.setdefault("meta", {}).get("in_combat", False)
    if not is_combat:
        state["meta"]["in_combat"] = True; entities.refresh_beats(actor) 
    else:
        if not entities.consume_beat(actor, "stamina"): return "No stamina beats remaining! Press SPACE."

    if not entities.spend_stamina(actor, w_stats["cost"]):
        return f"{actor_name} is too exhausted (Stamina tokens required: {w_stats['cost']})!"
        
    dx, dy = abs(actor["pos"][0] - target["pos"][0]), abs(actor["pos"][1] - target["pos"][1])
    if max(dx, dy) > w_stats["range"]:
        mech_result = f"Target out of range for {w_stats['name']} (Range: {w_stats['range']})."
        state["latest_action"] = {"actor": actor_name, "action": "Melee Attack", "target": target_name, "mechanical_result": mech_result}
        save_state(state); return mech_result

    target_tags = target.get("tags", [])
    
    # --- DUALITY OF TAGS (Brittle / Brutal) ---
    if "brittle" in target_tags and "brutal" in weapon_tags:
        if target.get("type") == "prop" or "environment" in target_tags:
            # OBJECT RULE: Instant shattering
            entities.apply_damage(target, 999, "physical")
            mech_result = f"CRITICAL MASS! The Brittle {target_name} is instantly shattered by the Brutal impact!"
            state["latest_action"] = {"actor": actor_name, "action": "Melee Attack", "target": target_name, "mechanical_result": mech_result}
            save_state(state); return mech_result
        else:
            # ENTITY RULE: Bonus damage
            brittle_bonus = 2
    else:
        brittle_bonus = 0

    attacker_adv = True if "prone" in target_tags or "stunned" in target_tags else False
    target_stamina = target.get("resources", {}).get("stamina", 10)
    
    attack_total, att_log = entities.roll_check(actor, "Might", situational_adv=attacker_adv)
    
    if target_stamina <= 0:
        defense_total = 0; def_log = "[Exhausted: No Defense!]"
    elif "has_defended" in target.get("tags", []):
        defense_total = 10 + entities.get_gear_bonus(target, "Aegis"); def_log = "[Overwhelmed: Static]"
    else:
        def_stat = "Aegis" if entities.get_stat(target, "Aegis") > 0 else "Reflexes"
        defense_total, def_log = entities.roll_check(target, def_stat)
        target.setdefault("tags", []).append("has_defended")
        
    if attack_total == defense_total:
        mech_result = execute_clash(state, actor, target, entities.get_best_clash_tactic(actor), entities.get_best_clash_tactic(target))
    elif attack_total > defense_total: 
        actor_might = entities.get_stat(actor, "Might")
        die_size = w_stats["die"]; flat_dmg = w_stats["flat"]
        
        if attack_total - defense_total >= 5:
            damage = die_size + flat_dmg + actor_might + brittle_bonus; crit_prefix = "CRITICAL HIT! "
        else:
            damage = max(1, random.randint(1, die_size) + flat_dmg + actor_might + brittle_bonus); crit_prefix = "HIT. "
            
        is_dead = entities.apply_damage(target, damage, "physical")
        if is_dead: 
            check_encounter_end(state, actor)
            mech_result = f"{crit_prefix}{damage} damage. {target_name} is DEAD."
        else: 
            msg_mod = f" ( exploited Brittle state!)" if brittle_bonus > 0 else ""
            mech_result = f"{crit_prefix}{damage} damage dealt{msg_mod}. {target_name} has {target['hp']} HP left."
    else: 
        mech_result = f"BLOCKED! {target_name}'s defense held."
                
    state["latest_action"] = {"actor": actor_name, "action": "Melee Attack", "target": target_name, "mechanical_result": mech_result}
    state["ai_directive"] = "NARRATOR MODE: Describe this visceral combat action in 2 sentences. NO sci-fi terms."
    save_state(state); return mech_result

def execute_move(actor_id, dest_x, dest_y):
    state = load_state()
    actor = next((e for e in state.get("entities", []) if e.get("id") == actor_id or e.get("name") == actor_id), None)
    if not actor or "dead" in actor.get("tags", []): return "Action failed."
    dx, dy = abs(actor["pos"][0] - dest_x), abs(actor["pos"][1] - dest_y)
    max_dist = actor.get("speed", 5)
    if max(dx, dy) > max_dist: return f"Move too far! ({max_dist} cell limit)"
    is_combat = state.setdefault("meta", {}).get("in_combat", False)
    if is_combat:
        if not entities.consume_beat(actor, "move"): return "No Move Beats remaining! Press SPACE."
        actor_tags = actor.get("tags", [])
        if "disengaging" not in actor_tags:
            for e in state.get("entities", []):
                if e != actor and "hostile" in e.get("tags", []) and e.get("hp", 0) > 0:
                    ex, ey = abs(actor["pos"][0] - e["pos"][0]), abs(actor["pos"][1] - e["pos"][1])
                    if max(ex, ey) <= 1:
                        atk_roll, _ = entities.roll_check(e, "Might", situational_adv=True)
                        def_val = 10 + entities.get_gear_bonus(actor, "Aegis")
                        if atk_roll > def_val:
                            damage = max(2, entities.get_stat(e, "Might"))
                            entities.apply_damage(actor, damage, "physical")
        check_encounter_end(state, actor)
    else: execute_world_turn(state)
    if state.get("meta", {}).get("in_combat", False) and not entities.spend_stamina(actor, 1):
        return f"Too exhausted to move (low Stamina)!"
    actor["pos"] = [dest_x, dest_y]; state["latest_action"] = {"actor": actor["name"], "action": "Movement", "target": f"[{dest_x}, {dest_y}]", "mechanical_result": "Moved."}; save_state(state); return "Moved."

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
    if entities.loot_all(actor, target): save_state(state); return "Looted."
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
    """Dynamically applies consumable effects from items.json."""
    state = load_state()
    actor = next((e for e in state["entities"] if e["id"] == actor_id or e["type"] == "player"), None)
    if not actor or item_name not in actor.get("inventory", []): return "No item."
    
    items = entities.load_items()
    item_data = items.get("consumables", {}).get(item_name)
    if not item_data or "effect" not in item_data: return "No effect."
    
    eff = item_data["effect"]
    stat = eff.get("stat")
    val = eff.get("val", 0)
    
    if stat == "hp":
        actor["hp"] = min(actor.get("max_hp", 20), actor.get("hp", 0) + val)
    elif stat == "composure":
        actor["composure"] = min(actor.get("max_composure", 15), actor.get("composure", 0) + val)
    
    actor["inventory"].remove(item_name)
    save_state(state)
    return f"Used {item_name} (+{val} {stat})."

def execute_stat_action(actor_id, target_id, action_str):
    state = load_state()
    actor = next((e for e in state.get("entities", []) if e.get("id") == actor_id or e.get("type") == "player"), None)
    target = next((e for e in state.get("entities", []) if e.get("id") == target_id or e.get("name") == target_id), None)
    if not actor or not target: return "Error"
    try: stat_part, action_name = action_str.split("] ", 1); stat_used = stat_part.strip("[")
    except: return "Invalid format."
    
    beat_type = "stamina" if stat_used in ["Might", "Endurance", "Finesse", "Reflexes", "Vitality", "Fortitude"] else "focus"
    if not entities.consume_beat(actor, beat_type): return f"No {beat_type} beats! Press SPACE."
    
    action_data = actions.ACTION_REGISTRY.get(action_name); cost_type = "stamina"; cost_val = 1
    if action_data: cost_type = action_data["cost"]["type"]; cost_val = action_data["cost"]["val"]
    if actor["resources"].get(cost_type, 0) < cost_val: return f"Not enough {cost_type}!"
    
    actor["resources"][cost_type] -= cost_val
    roll_total, roll_log = entities.roll_check(actor, stat_used)
    
    target_resist = 10; success = roll_total >= target_resist
    mech_result = f"Action {action_name} ({stat_used}) SUCCESS!" if success else f"Action {action_name} FAILED."
    
    # ACTION MUTATORS
    if success:
        if action_name == "Disengage":
            apply_status_tag(actor, "disengaging")
        elif action_name == "Break":
            if "solid" in target.get("tags", []): target["tags"].remove("solid")
            mech_result = f"Shattered {target['name']}! Barrier destroyed."
        elif action_name == "Pickpocket":
            if entities.loot_all(actor, target): mech_result = f"Cleanly lifted items from {target['name']}."
            else: mech_result = f"Searched {target['name']} but found nothing."

    state["latest_action"] = {"actor": actor["name"], "action": action_str, "target": target["name"], "mechanical_result": mech_result}
    save_state(state); return mech_result
