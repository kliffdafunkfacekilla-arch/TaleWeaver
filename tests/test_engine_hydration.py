import sys
import os
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import engine
import entities

def test_hydration():
    # 1. Setup mock data (raw dicts)
    mock_raw_state = {
        "local_map_state": {
            "entities": [
                {
                    "id": "123",
                    "name": "Test Player",
                    "type": "player",
                    "pos": [0, 0],
                    "hp": 20,
                    "max_hp": 20,
                    "stats": {"Might": 10},
                    "equipment": {"weapon": "Iron Sword"}
                },
                {
                    "id": "456",
                    "name": "Test Prop",
                    "type": "prop",
                    "pos": [5, 5]
                }
            ]
        }
    }

    # 2. Patch state_manager.load_state
    with patch("state_manager.load_state", return_value=mock_raw_state):
        # 3. Call engine.load_state()
        hydrated_state = engine.load_state()
        
        # 4. Verify entities are objects, not dicts
        ents = hydrated_state["local_map_state"]["entities"]
        assert len(ents) == 2
        for e in ents:
            assert isinstance(e, entities.Entity)
            print(f"Verified hydrated entity: {e.name} (Type: {type(e)})")
            
        # Verify nested access (proves it's a model)
        player = ents[0]
        assert player.stats.Might == 10
        assert player.equipment.weapon == "Iron Sword"
        print("Verified nested attribute access successful.")

if __name__ == "__main__":
    try:
        test_hydration()
        print("\nHYDRATION TEST PASSED")
    except Exception as e:
        print(f"\nHYDRATION TEST FAILED: {e}")
        sys.exit(1)
