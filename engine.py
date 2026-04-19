import json
import random
import os
import time
import copy
import map_generator
import entities
import db_manager
import actions
import narrator

# LOCKING MECHANISM FOR STATE SAFETY
STATE_FILE = "local_map_state.json"
LOCK_FILE = "local_map_state.lock"

def acquire_lock():
    """Simple file-based lock to prevent race conditions on Windows."""
    for _ in range(50): # 0.5s total timeout
        try:
            if not os.path.exists(LOCK_FILE):
                with open(LOCK_FILE, "w") as f:
                    f.write(str(os.getpid()))
                return True
        except: pass
        time.sleep(0.01)
    return False

def release_lock():
    if os.path.exists(LOCK_FILE):
        try: os.remove(LOCK_FILE)
        except: pass

def load_state():
    """Loads the state with robust locking to prevent corruption."""
    if not os.path.exists(STATE_FILE): return start_new_game()
    
    if acquire_lock():
        try:
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
                release_lock()
                # Migration for map_stack if missing
                if "map_stack" not in data:
                    data["map_stack"] = []
                    if data.get("parent_map_state"):
                        data["map_stack"].append(data["parent_map_state"])
                return data
        except Exception:
            release_lock()
            return start_new_game()
    return start_new_game()

def save_state(state):
    """Saves the state with robust locking."""
    if acquire_lock():
        try:
            with open(STATE_FILE, "w") as f: 
                json.dump(state, f, indent=2)
            release_lock()
        except:
            release_lock()

    g_pos = state["local_map_state"].get("meta", {}).get("global_pos", [0,0])
    db_manager.save_chunk(g_pos[0], g_pos[1], state)

def start_new_game():
    db_manager.reset_world()
    local_map_data = map_generator.generate_local_map([0,0], [50,50])
    
    state = {
        "local_map_state": local_map_data,
        "map_stack": [], # NEW: Supports infinite interior depth
        "combat_log": ["Director: Welcome to Shatterlands."]
    }
    
    meta = state["local_map_state"].setdefault("meta", {})
    meta["in_combat"] = False
    meta["encounter_mode"] = "EXPLORATION"
    meta["clue_tracker"] = []
    
    for e in state["local_map_state"].get("entities", []):
        if "stats" in e:
            e["max_composure"] = entities.get_max_composure(e)
            e["composure"] = e["max_composure"]
    
    player = next((e for e in state["local_map_state"].get("entities", []) if e["type"] == "player"), None)
    if player: entities.refresh_beats(player)
    save_state(state)
    return state

def check_encounter_end(state, player):
    meta = state["local_map_state"].get("meta", {})
    if not meta.get("in_combat", False): return False
    
    mode = meta.get("encounter_mode", "COMBAT")
    
    if mode == "COMBAT":
        hostiles = [e for e in state["local_map_state"].get("entities", []) if ("hostile" in e.get("tags", []) or e.get("type") == "hostile") and e.get("hp", 0) > 0]
        if not hostiles:
            meta["in_combat"] = False
            log_message("Threat eliminated. Returning to Explore Mode.", state=state)
            return True
    
    elif mode == "SOCIAL_COMBAT":
        hostiles = [e for e in state["local_map_state"].get("entities", []) if ("hostile" in e.get("tags", []) or e.get("type") == "npc") and e.get("composure", 20) > 0]
        if not hostiles:
            meta["in_combat"] = False
            log_message("Social objectives achieved.", state=state)
            return True

    px, py = player["pos"]
    hostiles = [e for e in state["local_map_state"].get("entities", []) if ("hostile" in e.get("tags", []) or e.get("type") == "hostile") and e.get("hp", 0) > 0]
    all_far = True
    for h in hostiles:
        hx, hy = h["pos"]
        if max(abs(px - hx), abs(py - hy)) <= 12:
            all_far = False; break
    if all_far and hostiles:
        meta["in_combat"] = False
        log_message("Distance maintained. Encounter mode suspended.", state=state)
        return True
        
    return False

def trigger_incident(state, mode="COMBAT"):
    meta = state["local_map_state"].setdefault("meta", {})
    meta["in_combat"] = True
    meta["encounter_mode"] = mode
    log_message(f"⚠️ INCIDENT TRIGGERED: {mode} initiated.", state=state)
    save_state(state)

def execute_world_turn(state):
    player = next((e for e in state["local_map_state"].get("entities", []) if e.get("type") == "player"), None)
    if not player or "dead" in player.get("tags", []): return

    meta = state["local_map_state"].get("meta", {})
    meta["clock"] = meta.get("clock", 0) + 1
        
    if not meta.get("in_combat", False): return
        
    active_actors = [npc for npc in state["local_map_state"].get("entities", []) 
                       if (npc.get("type") == "hostile" or "hostile" in npc.get("tags", []) or "puzzle" in npc.get("tags", [])) 
                       and npc.get("hp", 0) > 0]
                       
    active_actors.sort(key=lambda x: entities.get_derived_stats(x).get("Movement", 5), reverse=True)
    mode = meta.get("encounter_mode")

    for npc in active_actors:
        if mode == "SOCIAL_COMBAT": execute_social_npc_pulse(state, npc, player)
        elif "puzzle" in npc.get("tags", []): execute_puzzle_pulse(state, npc, player)
        else: execute_npc_pulse(state, npc, player)

def execute_npc_pulse(state, npc, player):
    """Refactored Monolithic AI Pulse."""
    entities.refresh_beats(npc)
    
    # 1. PERCEIVE
    visible = _npc_perceive(npc, player)
    if not visible:
        entities.regenerate_resources(npc)
        return

    # 2. ACT (Attack if in range)
    if _npc_can_attack(npc, player):
        execute_attack(npc.get("id") or npc["name"], player.get("id") or player["name"])
    # 3. MOVE (Close the gap if not in range)
    else:
        _npc_move_towards(state, npc, player)

    entities.regenerate_resources(npc)

def _npc_perceive(npc, player):
    dist = max(abs(npc["pos"][0] - player["pos"][0]), abs(npc["pos"][1] - player["pos"][1]))
    perception = entities.get_stat(npc, "Awareness") + 5
    return dist <= perception

def _npc_can_attack(npc, player):
    w_stats = entities.get_weapon_stats(npc)
    dist = max(abs(npc["pos"][0] - player["pos"][0]), abs(npc["pos"][1] - player["pos"][1]))
    return dist <= w_stats["range"]

def _npc_move_towards(state, npc, player):
    if not entities.consume_beat(npc, "move"): return
    
    px, py = player["pos"]
    nx, ny = npc["pos"]
    dx, dy = px - nx, py - ny
    
    speed = entities.get_movement_speed(npc)
    for _ in range(speed):
        dist = max(abs(npc["pos"][0] - px), abs(npc["pos"][1] - py))
        if dist <= 1: break
        
        sx = 1 if dx > 0 else (-1 if dx < 0 else 0)
        sy = 1 if dy > 0 else (-1 if dy < 0 else 0)
        dest = [npc["pos"][0] + sx, npc["pos"][1] + sy]
        
        collision = any(e["pos"] == dest and (e.get("hp", 0) > 0 or "solid" in e.get("tags", [])) 
                        for e in state["local_map_state"].get("entities", []))
        if not collision:
            npc["pos"] = dest
            nx, ny = npc["pos"]
            dx, dy = px - nx, py - ny
        else: break

def execute_social_npc_pulse(state, npc, player):
    entities.refresh_beats(npc)
    dist = max(abs(npc["pos"][0] - player["pos"][0]), abs(npc["pos"][1] - player["pos"][1]))
    choices = [a for a, d in actions.ACTION_REGISTRY.items() if d.get("category") == "Social Combat" and d.get("offense")]
    if choices and dist <= 5:
        execute_social_attack(npc.get("id") or npc["name"], player.get("id") or player["name"], random.choice(choices))
    entities.regenerate_resources(npc)

def execute_social_attack(actor_id, target_id, action_name=None):
    state = load_state()
    actor = next((e for e in state["local_map_state"].get("entities", []) if e.get("id") == actor_id or e.get("name") == actor_id), None)
    target = next((e for e in state["local_map_state"].get("entities", []) if e.get("id") == target_id or e.get("name") == target_id), None)
    if not actor or not target: return "Target missing."

    if actor.get("type") == "player" and state["local_map_state"].get("meta", {}).get("encounter_mode") != "SOCIAL_COMBAT":
        trigger_incident(state, mode="SOCIAL_COMBAT")

    if action_name is None:
        action_name = "Persuade" if "Persuade" in actor.get("skills", []) else "Beguile"
    
    action_data = actions.ACTION_REGISTRY.get(action_name)
    if not action_data or not entities.consume_beat(actor, "focus"): return "No Focus Beat!"
    
    actor["resources"]["focus"] -= action_data.get("cost", {"val": 1})["val"]
    att_total, _ = entities.roll_check(actor, "+".join(action_data["stats"]))
    def_total, _ = entities.roll_check(target, "Willpower")

    log_message(f"🗣️ {actor['name']} uses {action_name}...", state=state)
    if att_total >= def_total:
        damage = max(1, random.randint(1, 6) + sum(entities.get_stat(actor, s) for s in action_data["stats"]))
        is_broken, trauma = entities.apply_damage(target, damage, damage_type="mental")
        log_message(f"   ↳ {damage} composure reduced!" + (" BROKEN." if is_broken else ""), state=state)
    else: log_message(f"   ↳ Resisted.", state=state)

    save_state(state)
    return "Action resolved."

def enter_interior(state, building_type):
    """Supports infinite depth via map_stack."""
    print(f"[ENGINE] Entering interior: {building_type}")
    
    # Push current state to stack
    state["map_stack"].append(copy.deepcopy(state["local_map_state"]))
    
    # Generate new interior
    new_local = map_generator.generate_local_map([0,0], [12,12], building_type=building_type)
    state["local_map_state"] = new_local
    
    log_message(f"🚪 Entered {building_type.replace('_', ' ').title()}.", state=state)
    save_state(state)

def exit_interior(state):
    """Pops the map stack to return to the previous layer."""
    if not state.get("map_stack"):
        log_message("Already at the top level.", state=state)
        return
    
    # Pop previous state
    prev_state = state["map_stack"].pop()
    state["local_map_state"] = prev_state
    
    log_message("⬆️ Returned to previous layer.", state=state)
    save_state(state)

def log_message(msg, state=None):
    if state is None: state = load_state()
    log = state.setdefault("combat_log", [])
    log.append(msg)
    state["combat_log"] = log[-15:]
    save_state(state)

class GameEngine:
    def execute_action(self, intent_json, player, state):
        import quest_manager # Local import to handle circularity if needed
        action = intent_json.get("action", "UNKNOWN").upper()
        target_name = intent_json.get("target", "None")
        params = intent_json.get("parameters", "")
        
        target = next((e for e in state["local_map_state"].get("entities", []) if e["name"].lower() == target_name.lower()), None)
        
        if action == "SOCIAL_ATTACK":
            best_skill = next((s for s in player.get("skills", []) if actions.ACTION_REGISTRY.get(s, {}).get("category") == "Social Combat"), None)
            return {"status": "SUCCESS", "event": execute_social_attack(player["name"], target_name, best_skill), "mechanics_log": "Social attack."}

        elif action == "ATTACK": return {"status": "SUCCESS", "event": execute_attack(player["name"], target_name), "mechanics_log": "Attack."}
        elif action == "MOVE":
            # (Move logic simplified for space)
            return {"status": "SUCCESS", "event": "Moved.", "mechanics_log": "Success"}
        
        return {"status": "FAIL", "event": "Action unknown.", "mechanics_log": "Error"}

def execute_attack(actor_id, target_id):
    state = load_state()
    actor = next((e for e in state["local_map_state"].get("entities", []) if e.get("id") == actor_id or e.get("name") == actor_id), None)
    target = next((e for e in state["local_map_state"].get("entities", []) if e.get("id") == target_id or e.get("name") == target_id), None)
    if not actor or not target: return "Target missing."

    if not entities.consume_beat(actor, "stamina"): return "No Stamina!"
    w_stats = entities.get_weapon_stats(actor)
    actor["resources"]["stamina"] -= w_stats["cost"]

    att_stat = entities.get_attack_stat(actor)
    def_total, _ = entities.roll_check(target, entities.get_defense_stat(target))
    att_total, _ = entities.roll_check(actor, att_stat)

    if att_total >= def_total:
        damage = max(1, random.randint(1, w_stats["die"]) + w_stats["flat"] + entities.get_stat(actor, att_stat))
        is_dead, trauma = entities.apply_damage(target, damage)
        log_message(f"⚔️ {actor['name']} HITS {target['name']} for {damage}!", state=state)
    else: log_message(f"⚔️ {actor['name']} misses {target['name']}.", state=state)
    
    save_state(state)
    return "Attack resolved."

def execute_puzzle_pulse(state, npc, player): ...
def execute_deduce(actor_id, params): ... 
def execute_question(actor_id, target): ...
def execute_examine(actor_id, target): ...
