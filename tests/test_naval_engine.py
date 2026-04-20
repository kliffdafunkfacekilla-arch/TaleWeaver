import sys
import os
import json

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from core.schemas_naval import AetherSkiff, ShipComponent, ShipComponentType
from core.schemas import BiologicalChassis, CoreStats, ResourcePool, SurvivalPools
from modules.naval_engine import execute_regional_travel, trigger_full_rest
from modules.naval_combat import man_station, initiate_boarding
from map_generator import MapGenerator

def run_test():
    print("=== Ostraka Naval Module Verification ===")
    
    # 1. Setup Mock Data
    hull = ShipComponent(id="h1", name="Iron Hull", type=ShipComponentType.HULL, max_integrity=100, current_integrity=100, power_draw=2)
    eng = ShipComponent(id="e1", name="Aether-Coils", type=ShipComponentType.ENGINE, max_integrity=50, current_integrity=50, power_draw=5)
    qtrs = ShipComponent(id="q1", name="Officer Quarters", type=ShipComponentType.QUARTERS, max_integrity=20, current_integrity=20, power_draw=1)

    ship_a = AetherSkiff(
        ship_id="SS_Vanguard",
        name="Vanguard",
        ship_class="Light Skiff",
        max_fuel=1000,
        current_fuel=500,
        components=[hull, eng, qtrs],
        cargo=[]
    )

    stats = CoreStats(Might=15, Finesse=12, Logic=10)
    pools = SurvivalPools(
        hp=ResourcePool(current=10, max=20),
        composure=ResourcePool(current=5, max=15),
        stamina=ResourcePool(current=10, max=10),
        focus=ResourcePool(current=10, max=10)
    )
    actor = BiologicalChassis(id="p1", name="Captain Jax", species="Human", stats=stats, pools=pools)

    # 2. Test Travel Logic
    print("\n[Test 1] Regional Travel Logic...")
    original_fuel = ship_a.current_fuel
    ship_a, days = execute_regional_travel(ship_a, hex_distance=5, weather_modifier=1.0)
    print(f"Result: {days} hexes traveled. Fuel consumed: {original_fuel - ship_a.current_fuel} units.")
    assert days == 5
    assert ship_a.current_fuel < original_fuel

    # 3. Test Full Rest
    print("\n[Test 2] Full Rest (Quarters Requirement)...")
    trigger_full_rest(ship_a, [actor])
    print(f"Result: Actor HP restored to {actor.pools.hp.current}/{actor.pools.hp.max}")
    assert actor.pools.hp.current == 20

    # 4. Test Station Manning
    print("\n[Test 3] Station Manning (Helm - Pursue)...")
    combat_res = man_station(actor, ship_a, "helm", "pursue")
    print(f"Result: {combat_res['msg']}")
    
    # 5. Test Boarding Trigger
    print("\n[Test 4] Boarding Trigger Logic...")
    boarding_res = initiate_boarding(ship_a, ship_a) # Test self-boarding
    print(f"Result: {boarding_res['msg']}")
    assert boarding_res['success'] is True

    # 6. Test Map Generator Integration
    print("\n[Test 5] Tactical Map Generation (Boarding Action)...")
    mg = MapGenerator()
    map_data = mg.generate_boarding_map(ship_a.model_dump(), ship_a.model_dump())
    assert "boarding" in map_data["meta"]["current_map_id"]
    print(f"Result: Generated {map_data['meta']['grid_size']} grid with hull and deck biomes.")

    print("\n=== All Naval Tests Passed Successfully ===")

if __name__ == "__main__":
    try:
        run_test()
    except Exception as e:
        print(f"\n[CRITICAL FAILURE] Test failed: {e}")
        sys.exit(1)
