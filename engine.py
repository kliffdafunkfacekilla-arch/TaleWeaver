import json
import random
import os
import time
import copy
import sqlite3
import map_generator
import entities
import db_manager
import actions
import narrator

import state_manager

# Note: STATE_FILE and LOCK_FILE are now managed inside state_manager.py

def load_state():
    """Loads the state via StateManager and handles initialization/injections."""
    data = state_manager.load_state()
    if data is None: 
        return start_new_game()
    
    # INJECT FACTION DATA FOR UI (Transient view data)
    try:
        conn = sqlite3.connect(db_manager.DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT f.name, pr.value, pr.tier 
            FROM player_reputation pr 
            JOIN factions f ON pr.faction_id = f.id
        """)
        data["local_map_state"].setdefault("meta", {})["reputation"] = cursor.fetchall()
        
        cursor.execute("""
            SELECT f1.name, f2.name, fr.relationship, fr.status 
            FROM faction_relations fr 
            JOIN factions f1 ON fr.faction_a = f1.id 
            JOIN factions f2 ON fr.faction_b = f2.id
            WHERE fr.relationship != 0
        """)
        data["local_map_state"]["meta"]["faction_relations"] = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(f"⚠️ UI Injection Error: {e}")

    if "map_stack" not in data:
        data["map_stack"] = []
    
    return data

def save_state(state):
    """Strips transient data and saves via StateManager."""
    # Strip transient UI meta before saving to file
    temp_state = copy.deepcopy(state)
    meta = temp_state["local_map_state"].get("meta", {})
    if "reputation" in meta: del meta["reputation"]
    if "faction_relations" in meta: del meta["faction_relations"]
        
    state_manager.save_state(temp_state)

def start_new_game():
    db_manager.reset_world()
    local_map_data = map_generator.generate_local_map([0,0], [50,50])
    
    # Initialize basic state
    state = {
        "local_map_state": local_map_data,
        "map_stack": [], 
        "combat_log": ["Director: Welcome to Shatterlands."]
    }
    
    meta = state["local_map_state"].setdefault("meta", {})
    meta["in_combat"] = False
    meta["encounter_mode"] = "EXPLORATION"
    meta["clue_tracker"] = []
    
    # 1. ADD SECOND PLAYER (NYX)
    nyx = {
        "name": "Nyx", "type": "player", "pos": [50, 50],
        "hp": 15, "max_hp": 15, "stats": {"Logic": 8, "Awareness": 7, "Finesse": 6},
        "resources": {"stamina": 8, "max_stamina": 8, "focus": 12, "max_focus": 12},
        "inventory": ["Smoke Bomb"], "skills": ["Scan"], "tags": ["unbreakable"]
    }
    # Ensure players have unique names/IDs
    state["local_map_state"]["entities"].append(nyx)
    
    # 2. SET ACTIVE PLAYER
    meta["active_player_name"] = "Jax"
    
    for e in state["local_map_state"].get("entities", []):
        if "stats" in e:
            e["max_composure"] = entities.get_max_composure(e)
            e["composure"] = e["max_composure"]
    
    # Initialize beats for all players
    for p in [e for e in state["local_map_state"].get("entities", []) if e["type"] == "player"]:
        entities.refresh_beats(p)
        
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
    entities.refresh_beats(npc)
    visible = _npc_perceive(npc, player)
    if not visible:
        entities.regenerate_resources(npc)
        return
    if _npc_can_attack(npc, player):
        execute_attack(npc.get("id") or npc["name"], player.get("id") or player["name"])
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
    px, py = player["pos"]; nx, ny = npc["pos"]; dx, dy = px - nx, py - ny
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
            npc["pos"] = dest; nx, ny = npc["pos"]; dx, dy = px - nx, py - ny
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
    # Capture all players before switching maps
    players = [copy.deepcopy(e) for e in state["local_map_state"].get("entities", []) if e.get("type") == "player"]
    
    state["map_stack"].append(copy.deepcopy(state["local_map_state"]))
    
    # Generate map (will likely be empty of players by default)
    new_local = map_generator.generate_local_map([0,0], [12,12], building_type=building_type)
    
    # Place all players at the entrance
    grid_w, grid_h = new_local["meta"]["grid_size"]
    for i, p in enumerate(players):
        # Stagger slightly if needed, or stack (stacking is fine in Ostraka)
        p["pos"] = [grid_w // 2, grid_h - 2]
        new_local["entities"].append(p)
        
    state["local_map_state"] = new_local
    log_message(f"🚪 Entire party entered {building_type.replace('_', ' ').title()}.", state=state)
    save_state(state)

def exit_interior(state):
    if not state.get("map_stack"): return
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

def modify_player_reputation(faction_id, delta):
    conn = sqlite3.connect(db_manager.DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM player_reputation WHERE faction_id = ?", (faction_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO player_reputation (faction_id, value, tier) VALUES (?, ?, ?)", (faction_id, delta, entities.get_reputation_tier(delta)))
    else:
        new_val = max(-100, min(100, row[0] + delta))
        cursor.execute("UPDATE player_reputation SET value = ?, tier = ? WHERE faction_id = ?", (new_val, entities.get_reputation_tier(new_val), faction_id))
    conn.commit(); conn.close()

def execute_examine(actor_id, target_name):
    state = load_state()
    player = next((e for e in state["local_map_state"].get("entities", []) if e.get("type") == "player"), None)
    target = next((e for e in state["local_map_state"].get("entities", []) if e["name"].lower() == target_name.lower()), None)
    if not target: return "Target missing."
    # Mechanics: Logic Roll to uncover evidence
    roll, details = entities.roll_check(player, "Logic+Awareness")
    log_message(f"🔍 Examining {target_name}... {details}", state=state)
    
    # Mechanics: roll >= 100 - evidence_level
    # If evidence_level is 0 (Perfect Stealth), Difficulty = 100.
    # If evidence_level is 80 (Sloppy), Difficulty = 20.
    conn = sqlite3.connect(db_manager.DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT o.op_type, f_origin.name, f_target.name, o.evidence_level 
        FROM faction_operations o 
        JOIN factions f_origin ON o.origin_id = f_origin.id
        JOIN factions f_target ON o.target_id = f_target.id
        WHERE o.status = 'Exposed' OR (100 - o.evidence_level) <= ?
        LIMIT 1
    """, (roll,))
    evidence = cursor.fetchone()
    conn.close()
    if evidence:
        op_type, origin, victim, e_level = evidence
        msg = f"🧩 CLUE UNCOVERED: Evidence of a {op_type} plot by {origin} against {victim}!"
        state["local_map_state"].setdefault("meta", {}).setdefault("clue_tracker", []).append(msg)
        log_message(msg, state=state)
    else:
        log_message("Nothing unusual found.", state=state)
    save_state(state)

class GameEngine:
    def execute_action(self, intent_json, player, state):
        action = intent_json.get("action", "UNKNOWN").upper()
        target_name = intent_json.get("target", "None")
        if action == "EXAMINE":
            execute_examine(player["name"], target_name)
            return {"status": "SUCCESS", "event": "Examined object."}
        if action == "SOCIAL_ATTACK":
            best_skill = next((s for s in player.get("skills", []) if actions.ACTION_REGISTRY.get(s, {}).get("category") == "Social Combat"), None)
            return {"status": "SUCCESS", "event": execute_social_attack(player["name"], target_name, best_skill)}
        elif action == "ATTACK": return {"status": "SUCCESS", "event": execute_attack(player["name"], target_name)}
        return {"status": "FAIL", "event": "Action unknown."}

def execute_attack(actor_id, target_id):
    state = load_state()
    actor = next((e for e in state["local_map_state"].get("entities", []) if e.get("id") == actor_id or e.get("name") == actor_id), None)
    target = next((e for e in state["local_map_state"].get("entities", []) if e.get("id") == target_id or e.get("name") == target_id), None)
    if not actor or not target: return "Target missing."
    if not entities.consume_beat(actor, "stamina"): return "No Stamina!"
    w_stats = entities.get_weapon_stats(actor)
    actor["resources"]["stamina"] -= w_stats["cost"]
    att_total, _ = entities.roll_check(actor, entities.get_attack_stat(actor))
    def_total, _ = entities.roll_check(target, entities.get_defense_stat(target))
    if att_total >= def_total:
        damage = max(1, random.randint(1, w_stats["die"]) + w_stats["flat"] + entities.get_stat(actor, entities.get_attack_stat(actor)))
        is_dead, trauma = entities.apply_damage(target, damage)
        log_message(f"⚔️ {actor['name']} HITS {target['name']} for {damage}!", state=state)
        if is_dead and "sump_kin" in target.get("tags", []):
            modify_player_reputation(1, 5) # Gain Rep with Iron Caldera
    else: log_message(f"⚔️ {actor['name']} misses {target['name']}.", state=state)
    save_state(state)
    return "Attack resolved."
