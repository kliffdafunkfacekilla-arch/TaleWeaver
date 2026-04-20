from typing import Tuple, List, Dict, Any
from core.schemas_naval import AetherSkiff, ShipComponentType
from core.schemas import BiologicalChassis

def execute_regional_travel(
    ship: AetherSkiff, 
    hex_distance: int, 
    weather_modifier: float,
    baseline_fuel: int = 10
) -> Tuple[AetherSkiff, int]:
    """
    Simulates regional travel on the continental map.
    1 Hex = 1 Day (Time Dilation).
    Each day burns fuel based on power draw and weather.
    """
    days_passed = 0
    
    for day in range(hex_distance):
        # 1. Identify active power draw
        power_draw = ship.total_power_draw
        
        # 2. Check for component-based debuffs
        fuel_multiplier = 1.0
        engine = ship.get_component(ShipComponentType.ENGINE)
        
        if engine:
            if engine.current_integrity <= (engine.max_integrity * 0.5):
                # Damaged engine doubles fuel consumption
                fuel_multiplier = 2.0
            if engine.current_integrity <= 0:
                # Hull/Engine failure halts movement
                ship.tags.append("Stranded")
                if "Propulsion Failure" not in ship.tags:
                    ship.tags.append("Propulsion Failure")
                break

        # 3. Calculate burn for the day
        # burn = (baseline * power_draw) * weather_mod * engine_debuff
        daily_burn = int((baseline_fuel * power_draw) * weather_modifier * fuel_multiplier)
        
        # 4. Check fuel reserves
        if ship.current_fuel < daily_burn:
            # Mid-transit failure: Out of Fuel
            ship.current_fuel = 0
            if "Stranded" not in ship.tags:
                ship.tags.append("Stranded")
            if "Dead Calm" not in ship.tags:
                ship.tags.append("Dead Calm")
            break
            
        # 5. Burn fuel and increment time
        ship.current_fuel -= daily_burn
        days_passed += 1
        
    return ship, days_passed

def trigger_full_rest(ship: AetherSkiff, crew: List[BiologicalChassis]) -> List[BiologicalChassis]:
    """
    If the ship has operational Quarters, crew can fully regenerate HP and Composure.
    Requires one day to be spent stationary or can be used during transit if Quarters exist.
    """
    if not ship.has_quarters:
        # Cannot rest without quarters
        return crew

    for member in crew:
        member.pools.hp.current = member.pools.hp.max
        member.pools.composure.current = member.pools.composure.max
        # Clear minor traumas if applicable (optional logic)
        
    return crew
