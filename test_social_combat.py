import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'

import engine
import entities
import pygame
import json
import actions
import copy

def test_social_combat():
    print("--- STARTING SOCIAL COMBAT TEST ---")
    pygame.init()
    
    # 1. Start fresh game
    state = engine.start_new_game()
    player = next(e for e in state["local_map_state"]["entities"] if e["type"] == "player")
    
    # Mock an NPC
    npc = {
        "id": "TargetNPC",
        "name": "Senator Vaelen",
        "type": "npc",
        "pos": [51, 51],
        "stats": {"Willpower": 2, "Intuition": 1, "Knowledge": 3},
        "tags": ["social_target"]
    }
    npc["max_composure"] = 20
    npc["composure"] = 20
    
    state["local_map_state"]["entities"].append(npc)
    engine.save_state(state)
    
    # Refresh Player for actions
    entities.refresh_beats(player)
    player.setdefault("resources", {})["focus"] = 10
    player.setdefault("stats", {})["Logic"] = 10
    player.setdefault("stats", {})["Charm"] = 10
    player.setdefault("skills", []).append("Persuade")
    engine.save_state(state)
    
    # 2. Trigger Social Combat
    print("Triggering Social Combat manually...")
    engine.trigger_incident(state, mode="SOCIAL_COMBAT")
    
    # Re-fetch from file to ensure persistence
    state = engine.load_state()
    print(f"Encounter Mode: {state['local_map_state']['meta']['encounter_mode']}")
    
    # 3. Perform Social Attack
    print("Performing Persuade attack...")
    res = engine.execute_social_attack("Jax", "Senator Vaelen", "Persuade")
    print(f"Result: {res}")
    
    state = engine.load_state()
    target = next(e for e in state["local_map_state"]["entities"] if e["name"] == "Senator Vaelen")
    print(f"Target Composure: {target.get('composure')} / {target.get('max_composure')}")
    
    # 4. Check 'broken' logic
    print("Simulating mental break...")
    target["composure"] = 2 # Low enough for a high roll to break
    engine.save_state(state)
    
    # Need new beat? Yes, cycle beats or just cheat for test
    player = next(e for e in state["local_map_state"]["entities"] if e["type"] == "player")
    entities.refresh_beats(player) 
    engine.save_state(state)
    
    res = engine.execute_social_attack("Jax", "Senator Vaelen", "Beguile")
    print(f"Result: {res}")
    
    state = engine.load_state()
    target = next(e for e in state["local_map_state"]["entities"] if e["name"] == "Senator Vaelen")
    print(f"Target Tags: {target.get('tags')}")
    
    # 5. Verify Mode End
    p_copy = copy.deepcopy(player)
    p_copy["pos"] = [0,0]
    engine.check_encounter_end(state, p_copy)
    state = engine.load_state()
    print(f"In Combat: {state['local_map_state']['meta']['in_combat']}")
    
    print("--- SOCIAL COMBAT TEST COMPLETE ---")
    pygame.quit()

if __name__ == "__main__":
    test_social_combat()
