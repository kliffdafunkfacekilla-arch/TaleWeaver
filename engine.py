import json
import random
import os
import map_generator
import entities
import db_manager  # NEW: Import our database manager

def load_state():
    if not os.path.exists("local_map_state.json"): return start_new_game()
    try:
        with open("local_map_state.json", "r") as f:
            data = json.load(f)
            if "entities" not in data: return start_new_game()
            return data
    except:
        return start_new_game()

def save_state(state):
    # 1. Update the local file for the UI to read
    with open("local_map_state.json", "w") as f: json.dump(state, f, indent=2)
    
    # 2. Update the SQLite Database with the persistent memory!
    g_pos = state.get("meta", {}).get("global_pos", [0,0])
    db_manager.save_chunk(g_pos[0], g_pos[1], state)

def start_new_game():
    db_manager.reset_world() # Wipe the DB clean
    map_generator.generate_local_map([0,0], [25,25])
    with open("local_map_state.json", "r") as f: state = json.load(f)
    state.setdefault("meta", {})["clock"] = 0 
    save_state(state)
    return state

def execute_world_turn(state):
    player = next((e for e in state.get("entities", []) if e.get("type") == "player"), None)
    if not player or "dead" in player.get("tags", []): return
    
    if "clock" not in state["meta"]: state["meta"]["clock"] = 0
    state["meta"]["clock"] += 1
    
    taxed_max_s = entities.get_max_stamina(player)
    if player.get("resources", {}).get("stamina", 0) < taxed_max_s:
        player["resources"]["stamina"] += 1
        
    npc_actions = []
    for npc in state.get("entities", []):
        if npc.get("type") == "hostile":
            action = entities.process_npc_turn(npc, player, state)
            if action:
                if action["action"] == "attack":
                    npc_might = entities.get_stat(npc, "Might")
                    attack_roll = random.randint(1, 20) + npc_might
                    player_def_stat = entities.get_stat(player, "Aegis")
                    if player_def_stat == 0: player_def_stat = entities.get_stat(player, "Reflexes")
                    defense_roll = random.randint(1, 20) + player_def_stat
                    
                    if attack_roll > defense_roll:
                        damage = max(1, random.randint(1, 4) + npc_might)
                        entities.apply_damage(player, damage, "physical")
                        log_msg = f"{npc['name']} rolled {attack_roll} vs Jax's {defense_roll} block! Hit for {damage} dmg!"
                    else:
                        log_msg = f"{npc['name']} rolled {attack_roll}, but Jax deflected it!"
                        
                    print(f"[Clock: {state['meta']['clock']}] {log_msg} (Jax HP: {player['hp']}/{player['max_hp']})")
                    npc_actions.append(log_msg)
                
    if npc_actions:
        state["latest_action"]["mechanical_result"] += " " + " ".join(npc_actions)

def execute_attack(actor_id, target_id):
    state = load_state()
    actor = next((e for e in state.get("entities", []) if e.get("id") == actor_id or e.get("name") == actor_id), None)
    target = next((e for e in state.get("entities", []) if e.get("id") == target_id or e.get("name") == target_id), None)
    if not actor or not target: return "ERROR: Combatants not found."
    
    actor_name, target_name = actor["name"], target["name"]
    
    if not entities.spend_stamina(actor, 2):
        print(f"\n[Combat] {actor_name} is too exhausted to swing the weapon!")
        return "Not enough stamina."
        
    dx, dy = abs(actor["pos"][0] - target["pos"][0]), abs(actor["pos"][1] - target["pos"][1])
    if max(dx, dy) > 1:
        mech_result = f"{actor_name} swung at the air! {target_name} is out of melee range."
        print(f"\n[Combat] {mech_result}")
        state["latest_action"] = {"actor": actor_name, "action": "Melee Attack", "target": target_name, "mechanical_result": mech_result}
        execute_world_turn(state); save_state(state)
        return mech_result

    actor_might = entities.get_stat(actor, "Might")
    attack_roll = random.randint(1, 20) + actor_might
    target_def = entities.get_stat(target, "Aegis") or entities.get_stat(target, "Reflexes")
    defense_roll = random.randint(1, 20) + target_def
    
    print(f"\n[Combat] {actor_name} rolled {attack_roll} vs {defense_roll} Defense!")
    
    if attack_roll > defense_roll: 
        damage = max(1, random.randint(1, 8) + actor_might)
        is_dead = entities.apply_damage(target, damage, "physical")
        if is_dead: 
            mech_result = f"CRITICAL HIT! {damage} damage. {target_name} is DEAD."
            print(f"[Combat] SUCCESS! {target_name} died.")
        else: 
            mech_result = f"HIT. {damage} damage dealt. {target_name} has {target['hp']} HP left."
            print(f"[Combat] SUCCESS! {target_name} has {target['hp']} HP remaining.")
    else: 
        mech_result = f"BLOCKED! {target_name}'s defense held."
        print(f"[Combat] BLOCKED!")
                
    state["latest_action"] = {"actor": actor_name, "action": "Melee Attack", "target": target_name, "mechanical_result": mech_result}
    # NEW GRIMDARK FANTASY PROMPT
    state["ai_directive"] = "NARRATOR MODE: You are the Game Master of Ostraka. Describe this visceral, low-tech fantasy combat action in 2 sentences. NO sci-fi terms. NO AI meta-text."
    execute_world_turn(state); save_state(state)
    return mech_result

def execute_move(actor_id, dest_x, dest_y):
    state = load_state()
    actor = next((e for e in state.get("entities", []) if e.get("id") == actor_id or e.get("name") == actor_id), None)
    if not actor or "dead" in actor.get("tags", []): return "Action failed."
    
    if not entities.spend_stamina(actor, 1):
        print(f"\n[System] {actor['name']} is too exhausted to move!")
        return "Not enough stamina."
        
    actor["pos"] = [dest_x, dest_y]
    state["latest_action"] = {"actor": actor["name"], "action": "Movement", "target": f"[{dest_x}, {dest_y}]", "mechanical_result": "Moved."}
    execute_world_turn(state); save_state(state)
    return "Moved."

def execute_transition(dest_x, dest_y):
    state = load_state()
    player_data = next((e for e in state.get("entities", []) if e.get("type") == "player"), None)
    
    grid_w, grid_h = state["meta"]["grid_size"]
    global_pos = state["meta"].get("global_pos", [0, 0])
    old_g_x, old_g_y = global_pos[0], global_pos[1]
    
    if player_data: state["entities"].remove(player_data)
    
    # 1. Save the old chunk to the DB
    db_manager.save_chunk(old_g_x, old_g_y, state)

    new_g_x, new_g_y = old_g_x, old_g_y
    entry_x, entry_y = dest_x, dest_y
    if dest_x >= grid_w - 1: new_g_x += 1; entry_x = 1
    elif dest_x <= 0: new_g_x -= 1; entry_x = grid_w - 2
    if dest_y >= grid_h - 1: new_g_y += 1; entry_y = 1
    elif dest_y <= 0: new_g_y -= 1; entry_y = grid_h - 2

    # 2. Check the DB for the new chunk
    new_state = db_manager.load_chunk(new_g_x, new_g_y)
    
    if new_state:
        if player_data:
            player_data["pos"] = [entry_x, entry_y]
            new_state["entities"].append(player_data)
        new_state["meta"]["clock"] = state["meta"].get("clock", 0) 
        save_state(new_state)
        print(f"[System] Entering persistent memory: Chunk [{new_g_x},{new_g_y}] loaded.")
    else:
        map_generator.generate_local_map([new_g_x, new_g_y], [entry_x, entry_y], player_data=player_data)
        with open("local_map_state.json", "r") as f: new_state = json.load(f)
        new_state["meta"]["clock"] = state["meta"].get("clock", 0) 
        save_state(new_state)
        print(f"[System] Uncharted territory: Chunk [{new_g_x},{new_g_y}] generated.")
        
    return "Transition complete."

def execute_examine(actor_id, target_id):
    state = load_state()
    actor = next((e for e in state.get("entities", []) if e.get("id") == actor_id or e.get("name") == actor_id), None)
    target = next((e for e in state.get("entities", []) if e.get("id") == target_id or e.get("name") == target_id), None)
    if not actor or not target: return "Error"
    
    state["latest_action"] = {"actor": actor["name"], "action": "Examine Entity", "target": target["name"], "target_current_tags": target.get("tags", []), "mechanical_result": "Examining."}
    # NEW GRIMDARK FANTASY PROMPT
    state["ai_directive"] = f"NARRATOR MODE: You are the Game Master of the grimdark fantasy world of Ostraka. Describe this target in 2 atmospheric sentences using these tags: {target.get('tags', [])}. If 'dead' is present, describe a brutal fantasy corpse. NO sci-fi terms. NO AI meta-text."
    save_state(state); return "Examining."

def execute_examine_area(actor_id, dest_x, dest_y):
    state = load_state()
    actor = next((e for e in state.get("entities", []) if e.get("id") == actor_id or e.get("name") == actor_id), None)
    if not actor: return "Error"
    map_tags = state.get("meta", {}).get("map_tags", [])
    state["latest_action"] = {"actor": actor["name"], "action": "Examine Environment", "target": f"[{dest_x}, {dest_y}]", "map_tags": map_tags, "mechanical_result": "Scanning."}
    state["ai_directive"] = f"NARRATOR MODE: You are the Game Master of Ostraka. Describe this fantasy environment in 2 atmospheric sentences using these tags: {map_tags}. NO sci-fi terms. NO AI meta-text."
    save_state(state); return "Scanning."

def execute_loot(actor_id, target_id):
    state = load_state()
    actor = next((e for e in state.get("entities", []) if e.get("id") == actor_id), None)
    target = next((e for e in state.get("entities", []) if e.get("id") == target_id or e.get("name") == target_id), None)
    if not actor or not target: return "Error"
    
    dx, dy = abs(actor["pos"][0] - target["pos"][0]), abs(actor["pos"][1] - target["pos"][1])
    if max(dx, dy) > 1: return "Too far."
    
    if entities.loot_all(actor, target):
        print(f"[System] {actor['name']} looted all items from {target['name']}.")
        state["latest_action"] = {"actor": actor["name"], "action": "Loot", "target": target["name"], "mechanical_result": "Looted."}
        save_state(state); return "Looted."
    return "Empty."

def execute_equip(actor_id, item_name):
    state = load_state()
    # Safely find the player, no matter what their ID is
    actor = next((e for e in state.get("entities", []) if e.get("type") == "player" or e.get("id") == actor_id), None)
    
    if actor:
        if entities.equip_item(actor, item_name):
            print(f"[System] Successfully equipped {item_name}.")
            save_state(state)
        else:
            print(f"[Error] Failed to equip {item_name}. Check if it exists in data/items.json!")

def execute_unequip(actor_id, slot):
    state = load_state()
    actor = next((e for e in state.get("entities", []) if e.get("type") == "player" or e.get("id") == actor_id), None)
    
    if actor:
        if entities.unequip_item(actor, slot):
            print(f"[System] Successfully unequipped {slot}.")
            save_state(state)

def execute_drop(actor_id, item_name):
    state = load_state()
    actor = next((e for e in state.get("entities", []) if e.get("type") == "player" or e.get("id") == actor_id), None)
    
    if actor and item_name in actor.get("inventory", []):
        actor["inventory"].remove(item_name)
        # Create a physical entity on the map where Jax is standing!
        dropped_item = {
            "name": f"Dropped {item_name}",
            "type": "prop",
            "pos": list(actor["pos"]),
            "tags": ["item", "container"],
            "inventory": [item_name],
            "hp": 1
        }
        state["entities"].append(dropped_item)
        print(f"[System] You dropped {item_name} on the ground.")
        save_state(state)

def execute_use(actor_id, item_name):
    state = load_state()
    actor = next((e for e in state.get("entities", []) if e.get("type") == "player" or e.get("id") == actor_id), None)
    
    if actor and item_name in actor.get("inventory", []):
        if item_name == "Bandage":
            actor["hp"] = min(actor.get("max_hp", 20), actor.get("hp", 0) + 10)
            actor["inventory"].remove(item_name)
            print("[System] Used Bandage. Recovered 10 HP.")
        elif item_name == "Venom Gland":
            print("[System] You examine the Venom Gland... you probably shouldn't eat this.")
        else:
            print(f"[System] You examine the {item_name}.")
        save_state(state)
