from core.schemas import BiologicalChassis

def resolve_impact(target: BiologicalChassis, raw_damage: int, damage_type: str, armor_mod: int) -> BiologicalChassis:
    """
    Resolves damage impacts against a BiologicalChassis according to B.R.U.T.A.L. rules.
    
    Args:
        target: The character chassis being impacted.
        raw_damage: The incoming damage value before mitigation.
        damage_type: Either "physical" (targets HP) or "mental" (targets Composure).
        armor_mod: The additive or subtractive armor modifier.
        
    Returns:
        The updated BiologicalChassis state.
    """
    # 1. Calculate actual damage after armor mitigation
    actual_damage = max(0, raw_damage - armor_mod)
    
    # 2. Route damage based on type
    if damage_type == "physical":
        target.pools.hp.current = max(0, target.pools.hp.current - actual_damage)
    elif damage_type == "mental":
        target.pools.composure.current = max(0, target.pools.composure.current - actual_damage)
    
    # 3. Trigger Zero-State Logic
    if target.pools.hp.current <= 0:
        if "Exhaustion" not in target.body_injuries:
            target.body_injuries.append("Exhaustion")
            
    if target.pools.composure.current <= 0:
        if "Mental Static" not in target.mind_trauma:
            target.mind_trauma.append("Mental Static")
            
    return target
