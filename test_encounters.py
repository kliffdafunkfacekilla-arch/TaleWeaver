import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'

import engine
import pygame
import json
import actions

def set_high_stats(state):
    player = next(e for e in state["local_map_state"]["entities"] if e["type"] == "player")
    player["stats"] = {
        "Might": 20, "Endurance": 20, "Reflexes": 20, "Finesse": 20, "Vitality": 20, "Fortitude": 20,
        "Knowledge": 20, "Logic": 20, "Awareness": 20, "Intuition": 20, "Charm": 20, "Willpower": 20
    }

def test_story_driven_encounters():
    print("--- STARTING ENCOUNTER TEST ---")
    pygame.init()
    
    # 1. Start fresh game
    state = engine.start_new_game()
    set_high_stats(state)
    meta = state["local_map_state"]["meta"]
    
    # 2. Verify: No combat on start even with hostiles
    state["local_map_state"]["entities"].append({
        "name": "Dormant Bandit",
        "type": "hostile",
        "pos": [51, 51],
        "hp": 10,
        "tags": ["hostile"]
    })
    engine.save_state(state)
    
    engine.evaluate_encounter_threat(state)
    print(f"Checking Passive Aggro (Distance 1): in_combat={state['local_map_state']['meta'].get('in_combat')}")
    assert state['local_map_state']['meta'].get('in_combat') == False, "FAIL: Hostile triggered combat without incident!"

    # 3. Test Attack-Triggered Combat
    print("Testing Player-Initiated Combat...")
    engine.execute_attack("Jax", "Dormant Bandit")
    state = engine.load_state()
    print(f"Post-Attack: in_combat={state['local_map_state']['meta'].get('in_combat')}, mode={state['local_map_state']['meta'].get('encounter_mode')}")
    assert state['local_map_state']['meta'].get('in_combat') == True
    assert state['local_map_state']['meta'].get('encounter_mode') == "COMBAT"

    # 4. Cleanup and Reset for Puzzle test
    state = engine.start_new_game()
    set_high_stats(state)
    state["local_map_state"]["entities"].append({
        "name": "Ancient Gear-Lock",
        "type": "prop",
        "pos": [51, 51],
        "hp": 10, # Integrity
        "tags": ["puzzle", "locked"]
    })
    engine.save_state(state)
    engine.trigger_incident(state, mode="PUZZLE")
    state = engine.load_state()
    print(f"Puzzle Trigger: mode={state['local_map_state']['meta'].get('encounter_mode')}")

    # 5. Test Puzzle Solving
    print("Testing Puzzle Solving (Logical Damage)...")
    engine.execute_stat_action("Jax", "Ancient Gear-Lock", "[LOGIC] Geometric Puzzle")
    state = engine.load_state()
    puzzle = next(e for e in state["local_map_state"]["entities"] if e["name"] == "Ancient Gear-Lock")
    print(f"Puzzle HP after Logic check: {puzzle['hp']}")
    assert puzzle['hp'] < 10

    # 6. Test Mystery Discovery
    state = engine.start_new_game()
    set_high_stats(state)
    state["local_map_state"]["entities"].append({
        "name": "Torn Journal",
        "type": "prop",
        "pos": [51, 51],
        "tags": ["mystery"],
        "hidden_tags": ["poisoned_lead", "traitor_name"]
    })
    engine.save_state(state)
    engine.trigger_incident(state, mode="MYSTERY")
    print("Testing Mystery Discovery (Tag Reveal)...")
    engine.execute_examine("Jax", "Torn Journal")
    state = engine.load_state()
    journal = next(e for e in state["local_map_state"]["entities"] if e["name"] == "Torn Journal")
    print(f"Journal Tags after Examine: {journal['tags']}")
    assert "poisoned_lead" in journal['tags']
    
    engine.execute_examine("Jax", "Torn Journal")
    state = engine.load_state()
    print(f"Mystery Solved Status: {state['local_map_state']['meta'].get('mystery_solved')}")
    assert state['local_map_state']['meta'].get('mystery_solved') == True

    print("--- ALL ENCOUNTER TESTS PASSED! ---")
    pygame.quit()

if __name__ == "__main__":
    test_story_driven_encounters()
