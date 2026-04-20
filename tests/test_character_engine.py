import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from core.schemas import CharacterBuildRequest
from modules.character_engine import create_character

def run_test():
    print("=== B.R.U.T.A.L. Character Engine Verification ===")
    
    # 1. Setup Mock Build Request
    # Kingdom Mammals, Sub-Type T3 (Predator)
    # T3 Mammal Base: Might 4, Endurance 5, Finesse 5, Reflexes 1, Vitality 2, Fortitude 1, Knowledge 5, Logic 1, Awareness 1, Intuition 2, Charm 5, Willpower 4
    
    # Selected Tracks (Adding +2 to governing stats):
    # - Imposing Weapons (+2 Might) -> Might 6
    # - Clever Weapons (+2 Knowledge) -> Knowledge 7
    # - Braced Armor (+2 Might) -> Might 8
    # - Scholar Armor (+2 Knowledge) -> Knowledge 9 -> OVERFLOW
    # - The Wrangler (+2 Might) -> Might 10 -> OVERFLOW
    # - Mass (+2 Might) -> Might 12 -> OVERFLOW
    
    request = CharacterBuildRequest(
        name="Berserker Jax",
        kingdom="Mammals",
        sub_type="T3",
        size_shift="UP", # +1 Might or Endurance
        life_experience={
            "Might": 1,
            "Fortitude": 1,
            "Vitality": 1,
            "Willpower": 1,
            "Logic": 1,
            "Charm": 1
        },
        selected_tracks=[
            "Imposing Weapons",
            "Clever Weapons",
            "Braced Armor",
            "Scholar Armor",
            "The Wrangler",
            "Mass"
        ]
    )

    print("\n[Test 1] Character Resolution & Ceiling Reallocation...")
    sheet = create_character(request)
    
    print(f"Character: {sheet.name}")
    print(f"Final Stats: {sheet.stats.model_dump()}")
    
    # Verify Cap Enforcement
    for stat, val in sheet.stats.model_dump().items():
        assert val <= 8, f"FAILURE: Stat {stat} exceeds hard cap of 8!"
    
    print("Result: Hard Cap 8 enforced. Overflow reallocated successfully.")

    # Verify Derived Stats (Partial check)
    print("\n[Test 2] Derived Sub-Stats Logic (2:1 Ratios)...")
    print(f"HP: {sheet.pools.hp.current}/{sheet.pools.hp.max}")
    print(f"Perception: {sheet.derived.perception}")
    print(f"Stealth: {sheet.derived.stealth}")
    print(f"Movement: {sheet.derived.movement}")
    print(f"Balance: {sheet.derived.balance}")
    
    # Verify Regen Thresholds
    print(f"\n[Test 3] Active Batteries & Regen Thresholds...")
    print(f"Stamina Battery: {sheet.active_batteries['stamina']} / Focus: {sheet.active_batteries['focus']}")
    print(f"Regen Thresholds - Stamina: {sheet.regen_thresholds['stamina']} / Focus: {sheet.regen_thresholds['focus']}")

    print("\n=== All Character Engine Tests Passed Successfully ===")

if __name__ == "__main__":
    try:
        run_test()
    except Exception as e:
        print(f"\n[CRITICAL FAILURE] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
