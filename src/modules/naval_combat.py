import random
from typing import Dict, Any, Tuple
from core.schemas_naval import AetherSkiff, ShipComponentType, ShipComponent
from core.schemas import BiologicalChassis

def man_station(
    actor: BiologicalChassis, 
    ship: AetherSkiff, 
    station: str, 
    action: str,
    target_ship: AetherSkiff = None
) -> Dict[str, Any]:
    """
    Handles station-based actions during naval combat.
    Costs 1 of the actor's beats (Stamina or Focus).
    """
    station = station.lower()
    action = action.lower()
    result = {"success": False, "msg": "", "tokens": 0, "damage": 0}

    # Helper: Roll d20 + best of two stats
    def roll_naval(stats: BiologicalChassis, stat_a: str, stat_b: str) -> int:
        val_a = getattr(stats.stats, stat_a, 10)
        val_b = getattr(stats.stats, stat_b, 10)
        return random.randint(1, 20) + max(val_a, val_b)

    if station == "helm":
        # Helm (Pilot): Finesse/Reflex check.
        # Costs 1 Focus/Stamina beat (logic for beats handled at engine level)
        roll = roll_naval(actor, "Finesse", "Reflexes")
        if roll >= 15:
            result["success"] = True
            if action == "evade":
                ship.evasion_tokens += 1
                result["msg"] = f"{actor.name} skillfully maneuvers, gaining 1 Evasion Token."
                result["tokens"] = 1
            elif action == "pursue":
                ship.distance_closed = True
                result["msg"] = f"{actor.name} closes the gap! Boarding is now possible."
        else:
            result["msg"] = f"{actor.name} fails to find the right air currents."

    elif station == "cannons":
        # Cannons (Gunner): Might/Logic check to deal damage to integrity.
        if not target_ship:
            result["msg"] = "No target selected."
            return result
            
        roll = roll_naval(actor, "Might", "Logic")
        if roll >= 12:
            # Hit! Target a random component or the Hull if none specified
            target_comp = target_ship.get_component(ShipComponentType.HULL)
            if not target_comp:
                target_comp = random.choice(target_ship.components)
            
            damage = random.randint(5, 15)
            target_comp.current_integrity = max(0, target_comp.current_integrity - damage)
            
            result["success"] = True
            result["damage"] = damage
            result["msg"] = f"{actor.name} scores a direct hit on the {target_comp.name} for {damage} damage!"
        else:
            result["msg"] = f"The cannon shot sails harmlessly into the Aether."

    elif station == "forge":
        # Forge (Engineer): Focus beat to patch or Overclock.
        if action == "patch":
            # Patch a damaged component
            damaged = [c for c in ship.components if c.current_integrity < c.max_integrity]
            if damaged:
                comp = random.choice(damaged)
                repair = random.randint(3, 8)
                comp.current_integrity = min(comp.max_integrity, comp.current_integrity + repair)
                result["success"] = True
                result["msg"] = f"{actor.name} patches the {comp.name}, restoring {repair} integrity."
            else:
                result["msg"] = "All components are at maximum integrity."
        elif action == "overclock":
            # Extra speed at the cost of fuel
            ship.current_fuel = max(0, ship.current_fuel - 20)
            ship.distance_closed = True
            result["success"] = True
            result["msg"] = f"{actor.name} overclocks the aether-coils! Distance closed at high fuel cost."

    return result

def initiate_boarding(ship_a: AetherSkiff, ship_b: AetherSkiff) -> Dict[str, Any]:
    """
    Transitions the game into a tactical boarding action Battlemap.
    """
    if not ship_a.distance_closed and not ship_b.distance_closed:
        return {"success": False, "msg": "Ships are too far apart to board."}
        
    return {
        "success": True,
        "msg": "Ships are locked! Transitioning to tactical boarding combat.",
        "map_type": "boarding_action",
        "ship_a_id": ship_a.ship_id,
        "ship_b_id": ship_b.ship_id,
        "global_pos": [0,0] # Placeholder for map generator
    }
