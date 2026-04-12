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
            # Only reset the game on catastrophic failures, not temporary locks
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
    
    # Robust read for the fresh map
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
        
    # Distance Exit: If all hostiles are > 12 tiles away, drop combat (Buffed from 10)
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
            # Refresh NPC beats for their turn (simple pass)
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
                        
                    print(f"[Clock: {state['meta']['clock']}] {log_msg}")
                    npc_actions.append(log_msg)
                
    if npc_actions:
        res = state.get("latest_action", {}).get("mechanical_result", "")
        state.setdefault("latest_action", {})["mechanical_result"] = res + " " + " ".join(npc_actions)

def end_player_turn():
    """Ends the player's round, triggers enemy actions, and resets the Pulse economy."""
    state = load_state()
    player = next((e for e in state.get("entities", []) if e.get("type") == "player"), None)
    if not player or "dead" in player.get("tags", []): return

    check_encounter_end(state, player)

    print("\n--- [ ENEMY PHASE ] ---")
    execute_world_turn(state) 
    print("\n--- [ NEW ROUND ] ---")
    
    entities.refresh_beats(player)
    
    # --- LOADOUT REGENERATION MATH ---
    total_weight = 0
    for slot, item in player.get("equipment", {}).items():
        if item and item != "None":
            total_weight += entities.get_item_weight(item)
            
    capacity = player.get("stats", {}).get("Endurance", 10) 
    loadout_percent = (total_weight / capacity) * 100 if capacity > 0 else 100
    
    # Determine Regen Rate (BUFFED v2)
    if loadout_percent <= 50: regen_amount = 3
    elif loadout_percent <= 75: regen_amount = 2
    elif loadout_percent <= 100: regen_amount = 2
    else: regen_amount = 1 
    
    # Wipe temporary combat tags
    for e in state.get("entities", []):
        tags = e.setdefault("tags", [])
        if "has_defended" in tags: tags.remove("has_defended")
        if "disengaging" in tags: tags.remove("disengaging")
        
    # Apply Regen (Capped at 10)
    curr_s = player["resources"].get("stamina", 0)
    curr_f = player["resources"].get("focus", 0)
    player["resources"]["stamina"] = max(0, min(10, curr_s + regen_amount))
    player["resources"]["focus"] = max(0, min(10, curr_f + regen_amount))
    
    print(f"[System] Loadout at {int(loadout_percent)}%. Regenerated {regen_amount} Stamina/Focus.")
    save_state(state)

def end_encounter():
    """Drops the game back into Explore Mode."""
    state = load_state()
    state.setdefault("meta", {})["in_combat"] = False
    print("\n[SCENE] THREAT ELIMINATED. Returning to Explore Mode.")
    save_state(state)

def execute_clash(state, actor, target, actor_tactic, target_tactic):
    matrix = {
        "Press": ["Maneuver", "Trick"],
        "Hold": ["Press", "Feint"],
        "Trick": ["Hold", "Disengage"],
        "Maneuver": ["Hold", "Press"],
        "Disengage": ["Press", "Maneuver"],
        "Feint": ["Trick", "Disengage"]
    }
    
    actor_name = actor["name"]; target_name = target["name"]
    print(f"[Clash] {actor_name} uses {actor_tactic} vs {target_name}'s {target_tactic}!")
    
    if target_tactic in matrix.get(actor_tactic, []):
        target.setdefault("tags", [])
        if "staggered" not in target["tags"]: target["tags"].append("staggered")
        res = f"CLASH WON! {actor_name} used {actor_tactic} to overwhelm {target_name}. Enemy is STAGGERED."
    elif actor_tactic in matrix.get(target_tactic, []):
        actor.setdefault("tags", [])
        if "staggered" not in actor["tags"]: actor["tags"].append("staggered")
        res = f"CLASH LOST! {target_name} countered with {target_tactic}. {actor_name} is STAGGERED."
    else:
        res = f"STANDOFF! Both {actor_name} and {target_name} parried each other's tactics."
        
    print(f"[Clash] {res}")
    return res

def execute_attack(actor_id, target_id):
    state = load_state()
    actor = next((e for e in state.get("entities", []) if e.get("id") == actor_id or e.get("name") == actor_id), None)
    target = next((e for e in state.get("entities", []) if e.get("id") == target_id or e.get("name") == target_id), None)
    if not actor or not target: return "ERROR: Combatants not found."
    
    actor_name, target_name = actor["name"], target["name"]
    if "dead" in target.get("tags", []): return f"{target_name} is already finished."
    
    # --- ENCOUNTER TRIGGER ---
    is_combat = state.setdefault("meta", {}).get("in_combat", False)
    if not is_combat:
        print(f"\n[!] ENCOUNTER INITIATED BY {actor_name}! [!]")
        state["meta"]["in_combat"] = True
        entities.refresh_beats(actor) 
    else:
        if not entities.consume_beat(actor, "stamina"):
            return "No stamina beats remaining this round! Press SPACE."

    # THEN check for the actual Stamina token cost
    if not entities.spend_stamina(actor, 2):
        return f"{actor_name} is too exhausted (low Stamina tokens)!"
        
    dx, dy = abs(actor["pos"][0] - target["pos"][0]), abs(actor["pos"][1] - target["pos"][1])
    if max(dx, dy) > 1:
        mech_result = f"Target out of range."
        state["latest_action"] = {"actor": actor_name, "action": "Melee Attack", "target": target_name, "mechanical_result": mech_result}
        save_state(state); return mech_result

    target_tags = target.get("tags", [])
    attacker_adv = True if "prone" in target_tags or "stunned" in target_tags else False
    
    # 0. Exhaustion Check
    target_stamina = target.get("resources", {}).get("stamina", 10)
    
    # 1. Attacker Rolls Might
    attack_total, att_log = entities.roll_check(actor, "Might", situational_adv=attacker_adv)
    
    # 2. Defender Check (The Overwhelm & Exhaustion Mechanic)
    if target_stamina <= 0:
        defense_total = 0
        def_log = "[Exhausted: No Defense Possible!]"
    elif "has_defended" in target.get("tags", []):
        # Target has already defended this round! Use Static Defense.
        defense_total = 10 + entities.get_gear_bonus(target, "Aegis")
        def_log = "[Overwhelmed: Static Defense]"
    else:
        # First attack of the round: Roll active defense!
        def_stat = "Aegis" if entities.get_stat(target, "Aegis") > 0 else "Reflexes"
        defense_total, def_log = entities.roll_check(target, def_stat)
        target.setdefault("tags", []).append("has_defended") # Mark them!
        
    print(f"\n[Combat] {actor_name} attacks {target_name}!")
    print(f"  -> Attacker: {att_log} + Stat = {attack_total}")
    print(f"  -> Defender: {def_log} + Stat = {defense_total}")
    
    if attack_total == defense_total:
        actor_tactic = entities.get_best_clash_tactic(actor)
        target_tactic = entities.get_best_clash_tactic(target)
        mech_result = execute_clash(state, actor, target, actor_tactic, target_tactic)
    elif attack_total > defense_total: 
        actor_might = entities.get_stat(actor, "Might")
        
        # --- CRITICAL HIT LOGIC ---
        if attack_total - defense_total >= 5:
            # Critical Hit: Maximize the 1d8 damage!
            damage = 8 + actor_might
            crit_prefix = "CRITICAL HIT! "
        else:
            # Standard Hit: Roll 1d8 normally
            damage = max(1, random.randint(1, 8) + actor_might)
            crit_prefix = "HIT. "
            
        is_dead = entities.apply_damage(target, damage, "physical")
        if is_dead: 
            check_encounter_end(state, actor)
            mech_result = f"{crit_prefix}{damage} damage. {target_name} is DEAD."
        else: 
            mech_result = f"{crit_prefix}{damage} damage dealt. {target_name} has {target['hp']} HP left."
    else: 
        mech_result = f"BLOCKED! {target_name}'s defense held."
        print(f"[Combat] BLOCKED!")
                
    state["latest_action"] = {"actor": actor_name, "action": "Melee Attack", "target": target_name, "mechanical_result": mech_result}
    state["ai_directive"] = "NARRATOR MODE: Describe this visceral combat action in 2 sentences. NO sci-fi terms."
    save_state(state); return mech_result

def execute_move(actor_id, dest_x, dest_y):
    state = load_state()
    actor = next((e for e in state.get("entities", []) if e.get("id") == actor_id or e.get("name") == actor_id), None)
    if not actor or "dead" in actor.get("tags", []): return "Action failed."
    
    # Distance check
    dx, dy = abs(actor["pos"][0] - dest_x), abs(actor["pos"][1] - dest_y)
    max_dist = actor.get("speed", 5)
    if max(dx, dy) > max_dist:
        return f"Move too far! ({max_dist} cell limit)"

    # --- EXPLORE VS ENCOUNTER MOVEMENT ---
    is_combat = state.setdefault("meta", {}).get("in_combat", False)
    if is_combat:
        if not entities.consume_beat(actor, "move"):
            return "No Move Beats remaining this round! Press SPACE."
            
        # Threat Zone Check
        actor_tags = actor.get("tags", [])
        if "disengaging" not in actor_tags:
            for e in state.get("entities", []):
                if e != actor and "hostile" in e.get("tags", []) and e.get("hp", 0) > 0:
                    ex, ey = abs(actor["pos"][0] - e["pos"][0]), abs(actor["pos"][1] - e["pos"][1])
                    if max(ex, ey) <= 1:
                        print(f"\n[!] THREAT ZONE: {e['name']} takes a free strike! [!]")
                        atk_roll, _ = entities.roll_check(e, "Might", situational_adv=True)
                        def_val = 10 + entities.get_gear_bonus(actor, "Aegis")
                        if atk_roll > def_val:
                            damage = max(2, entities.get_stat(e, "Might"))
                            entities.apply_damage(actor, damage, "physical")
                            print(f"  -> HIT! {actor['name']} takes {damage} damage while turning their back!")
                        else:
                            print(f"  -> MISSED! {actor['name']} slipped away just in time.")
                            
        # Post-move combat check
        check_encounter_end(state, actor)
    else:
        # EXPLORE MODE: Free movement but advances world clock
        execute_world_turn(state)

    if state.get("meta", {}).get("in_combat", False) and not entities.spend_stamina(actor, 1):
        return f"Too exhausted to move (low Stamina tokens)!"
        
    actor["pos"] = [dest_x, dest_y]
    state["latest_action"] = {"actor": actor["name"], "action": "Movement", "target": f"[{dest_x}, {dest_y}]", "mechanical_result": "Moved."}
    save_state(state); return "Moved."

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
        new_state = load_state()
        new_state["meta"]["clock"] = state["meta"].get("clock", 0); save_state(new_state)
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
    map_tags = state.get("meta", {}).get("map_tags", [])
    state["latest_action"] = {"actor": actor["name"], "action": "Scan Area", "target": f"[{dest_x}, {dest_y}]", "mechanical_result": "Scanning."}
    state["ai_directive"] = f"NARRATOR MODE: Describe this environment. Tags: {map_tags}."
    save_state(state); return "Scanning."

def execute_loot(actor_id, target_id):
    state = load_state()
    actor = next((e for e in state.get("entities", []) if e.get("id") == actor_id), None)
    target = next((e for e in state.get("entities", []) if e.get("id") == target_id or e.get("name") == target_id), None)
    if not actor or not target: return "Error"
    if max(abs(actor["pos"][0] - target["pos"][0]), abs(actor["pos"][1] - target["pos"][1])) > 1: return "Too far."
    if entities.loot_all(actor, target): save_state(state); return "Looted."
    return "Empty."

def execute_equip(actor_id, item_name):
    state = load_state(); actor = next((e for e in state["entities"] if e["type"] == "player"), None)
    if actor and entities.equip_item(actor, item_name): save_state(state)

def execute_unequip(actor_id, slot):
    state = load_state(); actor = next((e for e in state["entities"] if e["type"] == "player"), None)
    if actor and entities.unequip_item(actor, slot): save_state(state)

def execute_drop(actor_id, item_name):
    state = load_state(); actor = next((e for e in state["entities"] if e["type"] == "player"), None)
    if actor and item_name in actor.get("inventory", []):
        actor["inventory"].remove(item_name)
        state["entities"].append({"name": f"Dropped {item_name}", "type": "prop", "pos": list(actor["pos"]), "tags": ["item", "container"], "inventory": [item_name], "hp": 1})
        save_state(state)

def execute_use(actor_id, item_name):
    state = load_state(); actor = next((e for e in state["entities"] if e["type"] == "player"), None)
    if actor and item_name == "Bandage":
        actor["hp"] = min(actor.get("max_hp", 20), actor.get("hp", 0) + 10)
        actor["inventory"].remove(item_name); save_state(state)

def execute_stat_action(actor_id, target_id, action_str):
    state = load_state()
    actor = next((e for e in state.get("entities", []) if e.get("type") == "player" or e.get("id") == actor_id), None)
    target = next((e for e in state.get("entities", []) if e.get("id") == target_id or e.get("name") == target_id), None)
    if not actor or not target: return "Error"
    
    try:
        stat_part, action_name = action_str.split("] ", 1); stat_used = stat_part.strip("[")
    except: return "Invalid format."

    # Enforce B.R.U.T.A.L. Beat Rule: Stat determines Beat Type
    body_stats = ["Might", "Endurance", "Finesse", "Reflexes", "Vitality", "Fortitude"]
    mind_stats = ["Knowledge", "Logic", "Awareness", "Intuition", "Charm", "Willpower"]
    
    beat_type = "stamina" if stat_used in body_stats else "focus"
    
    if not entities.consume_beat(actor, beat_type):
        return f"No {beat_type} beats remaining! Press SPACE."

    # Tokens still follow action cost, but Beats follow the Stat.
    action_data = actions.ACTION_REGISTRY.get(action_name); cost_type = "stamina"; cost_val = 1
    if action_data: cost_type = action_data["cost"]["type"]; cost_val = action_data["cost"]["val"]

    if actor["resources"].get(cost_type, 0) < cost_val:
        return f"Not enough {cost_type} tokens!"
    
    actor["resources"][cost_type] -= cost_val
    roll_total, roll_log = entities.roll_check(actor, stat_used)
    
    target_resist = 10; success = roll_total >= target_resist
    mech_result = f"Action {action_name} ({stat_used}) roll {roll_total} vs DC {target_resist}. SUCCESS!" if success else f"Action {action_name} FAILED."
    
    # Handle Tactical Effects
    if success and action_name == "Disengage":
        actor.setdefault("tags", [])
        if "disengaging" not in actor["tags"]:
            actor["tags"].append("disengaging")
        mech_result += " (Shielded from Threat Zones)"
        
    state["latest_action"] = {"actor": actor["name"], "action": action_str, "target": target["name"], "mechanical_result": mech_result}
    state["ai_directive"] = f"NARRATOR MODE: Describe this {stat_used}-based {action_name}. Outcome: {'SUCCESS' if success else 'FAILURE'}."
    save_state(state); return mech_result
