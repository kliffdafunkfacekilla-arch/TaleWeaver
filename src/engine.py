import json
import random
import os
import asyncio
from typing import Dict, Any, List, Optional, Tuple

# Internal relative-friendly imports
import map_generator
import entities
import db_manager
import actions
import quest_manager
import state_manager
from campaign_director import CampaignWeaver

def hydrate_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensures all raw dictionaries in the map state are converted to 
    high-fidelity Pydantic Entity objects for UI and logic compatibility.
    """
    if "local_map_state" in state and "entities" in state["local_map_state"]:
        state["local_map_state"]["entities"] = [
            entities.Entity.model_validate(e) if isinstance(e, dict) else e 
            for e in state["local_map_state"]["entities"]
        ]
    return state

async def load_state() -> Dict[str, Any]:
    """
    Retrieves the current world state from StateManager.
    If no state exists, initializes a new game world.
    """
    state_data = state_manager.load_state()
    if not state_data or "local_map_state" not in state_data:
        return await start_new_game()
    return hydrate_state(state_data)

def save_state(state: Dict[str, Any]):
    """
    Persists the provided state dictionary to disk and database via StateManager.
    """
    state_manager.save_state(state)

async def log_message(msg: str):
    """
    Appends a message to the persistent combat log in the game state.
    """
    state = await load_state()
    log = state.setdefault("combat_log", [])
    log.append(msg)
    state["combat_log"] = log[-15:]
    save_state(state)
    print(f"[Log] {msg}")

async def start_new_game() -> Dict[str, Any]:
    """
    Performs directory initialization, database reset, and world generation.
    Sets up the initial campaign tracker and the hidden Master Arc.
    """
    db_manager.reset_world()
    # Initialize at the center of a 100x100 grid
    map_generator.MapGenerator(width=100, height=100).generate_local_map([0,0], [50,50])
    
    state = {}
    state_path = "state/local_map_state.json"
    if os.path.exists(state_path):
        with open(state_path, "r") as f: 
            state = json.load(f)
    
    if "combat_log" not in state: 
        state["combat_log"] = ["Director: Welcome to Shatterlands."]
    
    meta = state.setdefault("meta", {})
    meta["current_map_id"] = "overworld_default"
    meta["active_interior_deck"] = []
    
    # --- ICEBERG WEAVER INITIALIZATION ---
    weaver = CampaignWeaver()
    master_arc = await weaver.generate_master_arc()
    
    if not master_arc:
        from core.schemas import MasterArc
        master_arc = MasterArc(
            antagonist_faction="sump_kin",
            target_objective="The Lith-Siphon Activation",
            key_nouns=["Opal-Wallow", "Sump-Mother", "Emerald-Pipe"],
            current_act=1
        )
        print("[Weaver Warning] AI generation failed. Using deterministic 'Lith-Siphon' fallback arc.")

    from core.schemas import CampaignTracker
    tracker = CampaignTracker(
        main_plot="Hunting the bandits who burned your village.",
        master_arc=master_arc
    )
    
    # Store as dictionary for JSON compatibility in the state object
    meta["campaign_tracker"] = tracker.model_dump()
    
    # Process entities into Pydantic models for type safety
    hydrate_state(state)
        
    player = next((e for e in state["local_map_state"].get("entities", []) if e.type == "player"), None)
    if player: 
        entities.refresh_beats(player)
        
    save_state(state)
    return state

async def check_encounter_end(state: Dict[str, Any], player: entities.Entity) -> bool:
    """Evaluates if tactical combat should end based on hostile status or distance."""
    if not state.get("meta", {}).get("in_combat", False): return False
    
    hostiles = [e for e in state["local_map_state"].get("entities", []) if "hostile" in e.tags and e.hp > 0]
    if not hostiles:
        state["meta"]["in_combat"] = False
        await log_message("Threat eliminated. Returning to Explore Mode.")
        return True
        
    px, py = player.pos
    all_far = True
    for h in hostiles:
        hx, hy = h.pos
        if max(abs(px - hx), abs(py - hy)) <= 12:
            all_far = False
            break
    if all_far:
        state["meta"]["in_combat"] = False
        await log_message("Distance maintained. Leveling threat alert.")
        return True
    return False

async def execute_world_turn(state: Dict[str, Any]):
    """Advanced the game clock and executes non-player pulses (NPC AI)."""
    player = next((e for e in state["local_map_state"].get("entities", []) if e.type == "player"), None)
    if not player or "dead" in player.tags: return
    
    meta = state.setdefault("meta", {})
    if "clock" not in meta: meta["clock"] = 0
    meta["clock"] += 1
        
    active_hostiles = [npc for npc in state["local_map_state"].get("entities", []) 
                       if (npc.type == "hostile" or "hostile" in npc.tags) 
                       and npc.hp > 0]
                       
    active_hostiles.sort(key=lambda x: entities.get_derived_stats(x).get("Movement", 5), reverse=True)

    for npc in active_hostiles:
        await execute_npc_pulse(state, npc, player)

async def execute_npc_pulse(state: Dict[str, Any], npc: entities.Entity, player: entities.Entity):
    """The B.R.U.T.A.L Engine NPC logic pulse."""
    entities.refresh_beats(npc)
    npc_id = npc.id
    player_id = player.id
    
    px, py = player.pos
    nx, ny = npc.pos
    dx, dy = px - nx, py - ny
    dist = max(abs(dx), abs(dy))
    
    skills_db = entities.load_skills()
    
    for skill_name in npc.skills:
        skill_data = None
        skill_type = "stamina"
        for stat, data in skills_db.get("tactics", {}).items():
            for tier, t_data in data.get("tiers", {}).items():
                if t_data.get("name") == skill_name: 
                    skill_data = t_data
                    skill_type = "stamina"
                    break
            if skill_data: break
        if not skill_data:
            for school, data in skills_db.get("anomalies", {}).items():
                for tier, a_data in data.get("tiers", {}).items():
                    if a_data.get("name") == skill_name: 
                        skill_data = a_data
                        skill_type = "focus"
                        break
                if skill_data: break
        
        if skill_data:
            s_cost = skill_data.get("cost", {}).get("primary", skill_data.get("cost", {}).get("stamina", 0))
            f_cost = skill_data.get("cost", {}).get("secondary", skill_data.get("cost", {}).get("focus", 0))
            needed_range = 1 if skill_type == "stamina" else 5
            if dist <= needed_range:
                if npc.resources.stamina >= s_cost and npc.resources.focus >= f_cost:
                    return await execute_skill_action(npc_id, player_id, skill_name)

    if dist > 1 and entities.consume_beat(npc, "move"):
        speed = entities.get_movement_speed(npc)
        for _ in range(speed):
            if dist <= 1: break
            step_x = 1 if dx > 0 else (-1 if dx < 0 else 0)
            step_y = 1 if dy > 0 else (-1 if dy < 0 else 0)
            dest = [npc.pos[0] + step_x, npc.pos[1] + step_y]
            collision = any(e.pos == dest and ("solid" in e.tags or e.type == "hostile") for e in state["local_map_state"].get("entities", []))
            if not collision:
                npc.pos = dest
                nx, ny = npc.pos
                dx, dy = px - nx, py - ny
                dist = max(abs(dx), abs(dy))
            else: break
        
        p_stats = entities.get_derived_stats(player)
        if dist <= p_stats.get("Perception", 8):
            await log_message(f"🏃 {npc.name} closes the gap.")

    if dist <= entities.get_weapon_stats(npc)["range"]:
        return await execute_attack(npc_id, player_id)

    entities.regenerate_resources(npc)

def apply_status_tag(entity: entities.Entity, new_tag: str) -> bool:
    """Applies a status to an entity, handling 'Elite' mitigation logic."""
    tags = entity.tags
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

async def end_player_turn() -> str:
    """Handles turn-end triggers."""
    state = await load_state()
    player = next((e for e in state["local_map_state"].get("entities", []) if e.type == "player"), None)
    if not player or "dead" in player.tags: return "Game Over."

    await check_encounter_end(state, player)
    await execute_world_turn(state) 
    
    for e in state["local_map_state"].get("entities", []):
        if "bleeding" in e.tags and e.hp > 0:
            e.hp -= 1
            await log_message(f"🩸 {e.name} suffers 1 damage from bleeding.")
            if e.hp <= 0:
                e.hp = 0
                if "hostile" in e.tags: e.tags.remove("hostile")
                if "dead" not in e.tags: e.tags.append("dead")
                await log_message(f"☠️ {e.name} has bled out.")

    for e in state["local_map_state"].get("entities", []):
        for t in ["has_defended", "disengaging", "staggered", "stunned", "prone"]:
            if t in e.tags: e.tags.remove(t)
        for t in list(e.tags):
            if t.startswith("immune_"): e.tags.remove(t)
            
    entities.refresh_beats(player)
    
    total_weight = sum(entities.get_item_weight(item) for slot, item in player.equipment.model_dump().items() if item and item != "None")
    capacity = entities.get_stat(player, "Endurance") or 10
    loadout_percent = (total_weight / capacity) * 100
    regen = 3 if loadout_percent <= 50 else (2 if loadout_percent <= 100 else 1)
    
    player.resources.stamina = min(entities.get_max_stamina(player), player.resources.stamina + regen)
    player.resources.focus = min(entities.get_max_focus(player), player.resources.focus + regen)
    
    save_state(state)
    return "Pulse reset."

async def execute_attack(actor_id: str, target_id: str) -> str:
    """Calculates a weapon-based attack."""
    state = await load_state()
    actor = next((e for e in state["local_map_state"].get("entities", []) if e.id == actor_id or e.name == actor_id), None)
    target = next((e for e in state["local_map_state"].get("entities", []) if e.id == target_id or e.name == target_id), None)
    if not actor or not target: return "Target missing."
    
    if not entities.consume_beat(actor, "stamina"):
        return f"{actor.name} has no Stamina Beat left!"

    w_stats = entities.get_weapon_stats(actor)
    if actor.resources.stamina < w_stats["cost"]:
        return f"Exhausted! (Need {w_stats['cost']} Stamina tokens)."
    actor.resources.stamina -= w_stats["cost"]

    attack_total, _ = entities.roll_check(actor, entities.get_attack_stat(actor))
    defense_total, _ = entities.roll_check(target, entities.get_defense_stat(target))
    
    attack_type = "Ranged Attack" if w_stats["range"] > 1 else "Melee Attack"
    await log_message(f"⚔️ {actor.name} performs a {attack_type.lower()} on {target.name}...")

    if attack_total > defense_total:
        damage = max(1, random.randint(1, w_stats["die"]) + w_stats["flat"] + entities.get_stat(actor, entities.get_attack_stat(actor)))
        is_dead, trauma_msg = entities.apply_damage(target, damage)
        res = f"HIT for {damage} dmg!" + (" DEAD." if is_dead else "")
        await log_message(f"   ↳ {res}")
        if trauma_msg: await log_message(f"   ↳ {trauma_msg}")
    else:
        res = f"Missed."
        await log_message(f"   ↳ {res}")
        
    state["latest_action"] = {
        "actor": actor.name, "action": attack_type, "target": target.name, 
        "mechanical_result": res, "weapon_used": w_stats["name"]
    }
    save_state(state)
    return res

async def execute_move(actor_id: str, dest_x: int, dest_y: int) -> str:
    """Attempts to move an entity."""
    state = await load_state()
    actor = next((e for e in state["local_map_state"].get("entities", []) if e.id == actor_id or e.name == actor_id), None)
    if not actor or "dead" in actor.tags: return "Action failed."
    
    is_combat = state.get("meta", {}).get("in_combat", False)
    dist = max(abs(actor.pos[0] - dest_x), abs(actor.pos[1] - dest_y))
    
    speed = entities.get_movement_speed(actor)
    if dist > speed: return f"Distance too far! (Speed: {speed})"
    
    if is_combat:
        if not entities.consume_beat(actor, "move"): return "No Move Beats!"
        if not entities.spend_stamina(actor, 1): return "Exhausted!"
    
    actor.pos = [dest_x, dest_y]
    state["latest_action"] = {"actor": actor.name, "action": "Move", "target": f"{dest_x},{dest_y}", "mechanical_result": "Moved."}
    
    await check_quest_progress(state)
    save_state(state)
    return "Moved."

async def investigate_seed(actor_id: str, target_id: str) -> str:
    """Triggers the Narrative Weaver AI."""
    state_data = await load_state()
    actor = next((e for e in state_data["local_map_state"].get("entities", []) if e.id == actor_id or e.name == actor_id), None)
    target = next((e for e in state_data["local_map_state"].get("entities", []) if e.id == target_id or e.name == target_id), None)
    
    if not target or "story_seed" not in target.tags:
        return "Nothing special here."

    await log_message(f"🔍 {actor.name} investigates the {target.name}...")
    
    weaver_data = await quest_manager.generate_story_glue(target.name, state_data)
    macro_deck = quest_manager.build_macro_deck(weaver_data) 
    
    tracker = state_data.setdefault("meta", {}).setdefault("campaign_tracker", {})
    tracker["active_quest_deck"] = macro_deck
    tracker["active_subplot"] = macro_deck[0]["objective"]
        
    await log_message(f"📜 QUEST ACCEPTED: {weaver_data['story_hook']}")
    
    target.tags.remove("story_seed")
    if "used_seed" not in target.tags: target.tags.append("used_seed")
    
    save_state(state_data)
    return "Quest started."

async def execute_loot(actor_id: str, target_id: str) -> str:
    state = await load_state()
    actor = next((e for e in state["local_map_state"].get("entities", []) if e.id == actor_id or e.name == actor_id), None)
    target = next((e for e in state["local_map_state"].get("entities", []) if e.id == target_id or e.name == target_id), None)
    if not actor or not target: return "Target missing."
    if entities.loot_all(actor, target):
        await log_message(f"💰 {actor.name} looted {target.name}.")
        save_state(state)
        return f"Looted {target.name}."
    return "Nothing to loot."

async def execute_examine(actor_id: str, target_id: str) -> str:
    state = await load_state()
    target = next((e for e in state["local_map_state"].get("entities", []) if e.id == target_id or e.name == target_id), None)
    if not target: return "Target missing."
    tags = ", ".join(target.tags)
    res = f"{target.name}: HP {target.hp}, Tags: [{tags}]"
    await log_message(f"👁️ {res}")
    return res

async def check_quest_progress(state: Dict[str, Any]) -> bool:
    """Checks if current coordinates or context satisfy a quest goal."""
    tracker = state.get("meta", {}).get("campaign_tracker", {})
    deck = tracker.get("active_quest_deck", [])
    if not deck: return False
    
    current_step = deck[0]
    region_id = state.get("meta", {}).get("region_id")
    
    if current_step["type"] == "travel" and current_step.get("target_region") == region_id:
        await log_message(f"✅ OBJECTIVE COMPLETE: Arrived in {region_id}.")
        deck.pop(0)
        tracker["active_quest_deck"] = deck
        tracker["active_subplot"] = deck[0].get("objective") if deck else "None (Quest Complete)"
        return True
    return False

async def execute_transition(dest_x: int, dest_y: int) -> str:
    """Handles chunk loading and saving."""
    state_data = await load_state()
    player_data = next((e for e in state_data["local_map_state"].get("entities", []) if e.type == "player"), None)
    grid_w, grid_h = state_data["meta"]["grid_size"]
    global_pos = state_data["meta"].get("global_pos", [0, 0])
    
    if player_data: 
        state_data["local_map_state"]["entities"].remove(player_data)
    db_manager.save_chunk(f"{global_pos[0]}_{global_pos[1]}", state_data)
    
    new_g_x, new_g_y = global_pos[0], global_pos[1]
    entry_x, entry_y = dest_x, dest_y
    if dest_x >= grid_w - 1: new_g_x += 1; entry_x = 1
    elif dest_x <= 0: new_g_x -= 1; entry_x = grid_w - 2
    if dest_y >= grid_h - 1: new_g_y += 1; entry_y = 1
    elif dest_y <= 0: new_g_y -= 1; entry_y = grid_h - 2
    
    new_state = db_manager.load_chunk(f"{new_g_x}_{new_g_y}")
    if new_state:
        new_state = hydrate_state(new_state)
        if player_data: 
            new_state["local_map_state"]["entities"] = [e for e in new_state["local_map_state"]["entities"] if e.type != "player"]
            player_data.pos = [entry_x, entry_y]
            new_state["local_map_state"]["entities"].append(player_data)
        new_state["meta"]["clock"] = state_data["meta"].get("clock", 0)
        await check_quest_progress(new_state) 
        save_state(new_state)
    else:
        deck = state_data.get("meta", {}).get("campaign_tracker", {}).get("active_quest_deck", [])
        map_generator.generate_local_map([new_g_x, new_g_y], [entry_x, entry_y], player_data=player_data, quest_deck=deck)
        new_state = await load_state()
        new_state["meta"]["clock"] = state_data["meta"].get("clock", 0)
        await check_quest_progress(new_state) 
        save_state(new_state)
    
    await log_message(f"📍 Region Transition: {global_pos} ➔ {[new_g_x, new_g_y]}")
    return "Transition complete."

async def execute_use(actor_id, item_name):
    state = await load_state(); actor = next((e for e in state["local_map_state"].get("entities", []) if e.id == actor_id or e.name == actor_id), None)
    if not actor or item_name not in actor.inventory: return "Item missing."
    items_db = entities.load_items(); item_data = items_db.get("consumables", {}).get(item_name)
    if not item_data: return "Cannot use this."
    effect = item_data.get("effect", {}); stat = effect.get("stat"); val = effect.get("val", 0)
    msg = f"Used {item_name}."
    if stat == "hp": actor.hp = min(actor.max_hp, actor.hp + val); msg = f"Used {item_name} (+{val} HP)."
    elif stat == "composure": actor.composure = min(actor.max_composure, actor.composure + val); msg = f"Used {item_name} (+{val} Composure)."
    if item_name == "Bandage" and "bleeding" in actor.tags: actor.tags.remove("bleeding"); msg += " Bleeding stopped."
    actor.inventory.remove(item_name)
    await log_message(f"💊 {actor.name} {msg.lower()}"); save_state(state); return msg

async def execute_equip(actor_id, item_name):
    state = await load_state(); actor = next((e for e in state["local_map_state"].get("entities", []) if e.id == actor_id or e.name == actor_id), None)
    if not actor: return "Actor missing."
    if entities.equip_item(actor, item_name):
        await log_message(f"🛡️ {actor.name} equipped {item_name}."); save_state(state); return f"Equipped {item_name}."
    return "Equip failed."

async def execute_unequip(actor_id, slot):
    state = await load_state(); actor = next((e for e in state["local_map_state"].get("entities", []) if e.id == actor_id or e.name == actor_id), None)
    if not actor: return "Actor missing."
    if entities.unequip_item(actor, slot):
        await log_message(f"🎒 {actor.name} unequipped {slot}."); save_state(state); return f"Unequipped {slot}."
    return "Unequip failed."

async def execute_drop(actor_id, item_name):
    state = await load_state(); actor = next((e for e in state["local_map_state"].get("entities", []) if e.id == actor_id or e.name == actor_id), None)
    if not actor or item_name not in actor.inventory: return "Item missing."
    actor.inventory.remove(item_name); await log_message(f"🗑️ {actor.name} dropped {item_name}."); save_state(state); return f"Dropped {item_name}."

async def execute_examine_area(actor_id, x, y):
    state = await load_state(); ents = [e for e in state["local_map_state"].get("entities", []) if e.pos == [x, y]]
    if not ents: return "Nothing but the cold void here."
    res = ", ".join([e.name for e in ents]); await log_message(f"👁️ Area at {x},{y}: Found {res}"); return f"Found {res}"

async def execute_stat_action(actor_id, target_id, selection):
    state = await load_state(); actor = next((e for e in state["local_map_state"].get("entities", []) if e.id == actor_id or e.name == actor_id), None)
    target = next((e for e in state["local_map_state"].get("entities", []) if e.id == target_id or e.name == target_id), None)
    if not actor or not target: return "Error"
    try: stat_part, action_name = selection.split("] "); stat_name = stat_part.strip("[")
    except ValueError: return f"Unknown action: {selection}"
    action_data = actions.ACTION_REGISTRY.get(action_name)
    if not action_data: return "Action not found."
    cost = action_data.get("cost", {})
    if not entities.consume_beat(actor, cost.get("type", "stamina")): return f"No {cost['type'].capitalize()} Beat!"
    if not entities.spend_stamina(actor, cost.get("val", 0)): return "Exhausted!"
    await log_message(f"🎲 {actor.name} attempts {action_name} on {target.name}...")
    roll_total, _ = entities.roll_check(actor, stat_name)
    if roll_total >= 14:
        if action_data["category"] == "Combat":
            is_dead, trauma = entities.apply_damage(target, 5)
            res = f"SUCCESS: Dealt 5 dmg!" + (" DEAD." if is_dead else "")
            if trauma: res += f" {trauma}"
        else: res = "SUCCESS: Effect triggered."
        await log_message(f"   ↳ {res}")
    else: res = "FAILED."; await log_message(f"   ↳ {res}")
    save_state(state); return res

async def execute_skill_action(actor_id, target_id, skill_name):
    state = await load_state(); actor = next((e for e in state["local_map_state"].get("entities", []) if e.id == actor_id or e.name == actor_id), None)
    target = next((e for e in state["local_map_state"].get("entities", []) if e.id == target_id or e.name == target_id), None)
    if not actor or not target: return "Error"
    skills_db = entities.load_skills(); skill_data = None; stat_used = ""; beat_type = "stamina"
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
    cost = skill_data.get("cost", {}); s_cost = cost.get("primary", cost.get("stamina", 0)); f_cost = cost.get("secondary", cost.get("focus", 0))
    if actor.resources.stamina < s_cost or actor.resources.focus < f_cost: return "Exhausted!"
    actor.resources.stamina -= s_cost; actor.resources.focus -= f_cost
    await log_message(f"🌀 {actor.name} uses {skill_name} (-{s_cost}S, -{f_cost}F)")
    roll_total, _ = entities.roll_check(actor, stat_used)
    success = roll_total >= 12
    if success: mech_result = resolve_skill_tags(actor, target, skill_data, state); await log_message(f"   ↳ SUCCESS: {mech_result}")
    else: mech_result = f"{skill_name} FAILED."; await log_message(f"   ↳ FAILED.")
    state["latest_action"] = {"actor": actor.name, "action": skill_name, "target": target.name, "mechanical_result": mech_result}
    save_state(state); return mech_result

def resolve_skill_tags(actor, target, skill_data, state):
    tags = skill_data.get("tags", []); result_parts = []
    if "push" in tags:
        ax, ay = actor.pos; tx, ty = target.pos; dx, dy = tx - ax, ty - ay
        nx, ny = (1 if dx > 0 else -1 if dx < 0 else 0), (1 if dy > 0 else -1 if dy < 0 else 0); dest = [tx + nx, ty + ny]
        if not any(e.pos == dest and e.hp > 0 for e in state["local_map_state"].get("entities", [])): target.pos = dest; result_parts.append(f"Pushed {target.name}")
        else:
            is_dead, trauma = entities.apply_damage(target, 2); result_parts.append(f"Wall-impact (2 dmg)")
            if trauma: result_parts.append(trauma)
    if "control" in tags or "grapple" in tags: apply_status_tag(target, "grappled"); result_parts.append("Grappled")
    if "shred" in tags or "armor_crack" in tags: apply_status_tag(target, "broken_armor"); result_parts.append("Armor Shredded")
    if "cc" in tags or "stun" in tags: apply_status_tag(target, "stunned"); result_parts.append("Stunned")
    if "apply_status" in tags:
        for t in tags:
            if t not in ["apply_status", "push", "control", "grapple", "cc", "shred"]:
                if apply_status_tag(target, t): result_parts.append(t.replace('_', ' ').capitalize())
    if not result_parts: result_parts.append(f"Effect triggered")
    return ", ".join(result_parts)

async def enter_interior(state, building_type, is_quest=False):
    tracker = state.setdefault("meta", {}).setdefault("campaign_tracker", {}); stack = tracker.setdefault("map_history_stack", [])
    current_id = state.get("meta", {}).get("current_map_id", "overworld_default"); db_manager.save_map_state(current_id, state.get("local_map_state", {}))
    stack.append(current_id)
    deck = tracker.get("active_quest_deck", [])
    if deck and deck[0].get("type") == "explore_interior":
        await log_message(f"📍 VOID-BREACH: Entering {building_type} to complete quest objective.")
        deck.pop(0); tracker["active_quest_deck"] = deck
        if deck: tracker["active_subplot"] = deck[0].get("objective")
        else: tracker["active_subplot"] = "Dungeon Phase Active"
    rooms_deck = quest_manager.build_interior_deck(building_type, is_quest); state["meta"]["active_interior_deck"] = rooms_deck
    state["meta"]["current_map_id"] = f"{building_type}_{len(stack)}"; await advance_interior_room(state); return f"Entered {building_type}."

async def exit_interior(state):
    tracker = state.get("meta", {}).get("campaign_tracker", {}); stack = tracker.get("map_history_stack", [])
    if not stack: return "Error: No overworld to return to."
    parent_id = stack.pop(); restored_map = db_manager.load_map_state(parent_id)
    if restored_map: state["local_map_state"] = restored_map; state["meta"]["current_map_id"] = parent_id; state["meta"]["active_interior_deck"] = []; save_state(state); return f"Exited back back to safely."
    return "Error: Failed to restore parent map from database."

async def advance_interior_room(state):
    deck = state.get("meta", {}).get("active_interior_deck", [])
    if not deck: return await exit_interior(state)
    current_room = deck.pop(0); state["meta"]["active_interior_deck"] = deck 
    new_data = map_generator.generate_interior_room(current_room); state["local_map_state"] = new_data["local_map_state"]; state["meta"].update(new_data["meta"])
    save_state(state); return f"Advanced to next area: {current_room.get('room_type', 'Unknown')}"
