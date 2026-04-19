import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'

import engine
import pygame
import json
import actions

def test_deductive_investigation():
    print("--- STARTING INVESTIGATION TEST ---")
    pygame.init()
    
    # 1. Start fresh game
    state = engine.start_new_game()
    
    # 2. Inject a custom Mystery Seed
    state["local_map_state"]["entities"].append({
        "name": "Strange Footprints",
        "type": "prop",
        "pos": [51, 51],
        "tags": ["story_seed", "clue_source"]
    })
    
    # Mock some NPCs
    state["local_map_state"]["entities"].append({
        "name": "Barman",
        "type": "npc",
        "pos": [52, 52],
        "tags": ["bartender"]
    })
    
    engine.save_state(state)
    
    # 3. Investigate the seed
    print("Investigating the seed...")
    engine.investigate_seed("Jax", "Strange Footprints")
    state = engine.load_state()
    
    meta = state["local_map_state"]["meta"]
    print(f"Encounter Mode: {meta.get('encounter_mode')}")
    print(f"Initial Clues: {meta.get('clue_tracker')}")
    
    # 4. Mock Truth Table if AI didn't provide one in test environment or to ensure determinism
    # (In real play quest_manager generates this)
    if not meta.get("truth_table"):
        meta["truth_table"] = {"culprit": "Jax", "motive": "Hunger"}
        meta["discoverable_clues"] = [
            {"text": "The bite marks match a canine.", "source_tag": "Strange Footprints", "skill_hint": "Awareness"},
            {"text": "The Barman saw someone hairy.", "source_tag": "Barman", "skill_hint": "Logic"}
        ]
    engine.save_state(state)

    # 5. Test Questioning
    print("Questioning NPC...")
    engine.execute_question("Jax", "Barman")
    state = engine.load_state()
    print(f"Clues after Questioning: {state['local_map_state']['meta'].get('clue_tracker')}")
    assert len(state['local_map_state']['meta'].get('clue_tracker')) > 0
    
    # 6. Test Examining
    print("Examining footprints...")
    engine.execute_examine("Jax", "Strange Footprints")
    state = engine.load_state()
    print(f"Clues after Examining: {state['local_map_state']['meta'].get('clue_tracker')}")
    
    # 7. Test Deduction (This relies on AI connectivity)
    print("Testing Deduction logic (Requires Ollama)...")
    try:
        res = engine.execute_deduce("Jax", "It was a hungry wolf-man.")
        print(f"Deduction Result: {res}")
    except Exception as e:
        print(f"AI Skip: {e}")

    print("--- INVESTIGATION TEST COMPLETE ---")
    pygame.quit()

if __name__ == "__main__":
    test_deductive_investigation()
