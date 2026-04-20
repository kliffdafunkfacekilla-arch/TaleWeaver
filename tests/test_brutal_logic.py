import sys
import os

# Add src to path so we can import cores and modules
sys.path.append(os.path.join(os.getcwd(), "src"))

from core.schemas import BiologicalChassis, CoreStats, SurvivalPools, ResourcePool, GameTags
from modules.trauma_engine import resolve_impact
from modules.action_engine import execute_beat

def test_character_creation():
    print("Testing BiologicalChassis creation...")
    stats = CoreStats(Might=15, Vitality=12)
    pools = SurvivalPools(
        hp=ResourcePool(current=20, max=20),
        composure=ResourcePool(current=15, max=15),
        stamina=ResourcePool(current=10, max=10),
        focus=ResourcePool(current=10, max=10)
    )
    chassis = BiologicalChassis(
        id="PLAYER_01",
        name="Jax",
        species="Human",
        stats=stats,
        pools=pools,
        active_tags=[GameTags.BRUTAL]
    )
    assert chassis.name == "Jax"
    assert chassis.stats.Might == 15
    assert chassis.stats.Logic == 10 # Default
    assert GameTags.BRUTAL in chassis.active_tags
    print("[SUCCESS] Chassis creation successful.")
    return chassis

def test_trauma_resolution(chassis):
    print("Testing Trauma Engine (resolve_impact)...")
    # Test Physical Damage with Armor
    chassis = resolve_impact(chassis, raw_damage=10, damage_type="physical", armor_mod=2)
    # 10 - 2 = 8. 20 - 8 = 12.
    assert chassis.pools.hp.current == 12
    
    # Test Massive Mental Damage triggering Zero-State
    chassis = resolve_impact(chassis, raw_damage=30, damage_type="mental", armor_mod=0)
    assert chassis.pools.composure.current == 0
    assert "Mental Static" in chassis.mind_trauma
    
    # Test Physical Zero-State
    chassis = resolve_impact(chassis, raw_damage=20, damage_type="physical", armor_mod=0)
    assert chassis.pools.hp.current == 0
    assert "Exhaustion" in chassis.body_injuries
    print("[SUCCESS] Trauma resolution successful.")

def test_action_economy(chassis):
    print("Testing Action Engine (execute_beat)...")
    # Reset pools for test
    chassis.pools.stamina.current = 10
    chassis.pools.focus.current = 10
    
    # Successful stamina beat
    chassis = execute_beat(chassis, "stamina", 5)
    assert chassis.pools.stamina.current == 5
    
    # Failed stamina beat (insufficient)
    try:
        execute_beat(chassis, "stamina", 10)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert str(e) == "Insufficient Stamina for this beat."
        
    # Free move beat
    chassis = execute_beat(chassis, "move", 0)
    assert chassis.pools.stamina.current == 5
    
    # Costly move beat (penalized)
    chassis = execute_beat(chassis, "move", 2)
    assert chassis.pools.stamina.current == 3
    
    print("[SUCCESS] Action economy successful.")

if __name__ == "__main__":
    print("--- B.R.U.T.A.L. ENGINE BACKEND VERIFICATION ---")
    c = test_character_creation()
    test_trauma_resolution(c)
    test_action_economy(c)
    print("--- ALL TESTS PASSED ---")
