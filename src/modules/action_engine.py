from core.schemas import BiologicalChassis

def execute_beat(actor: BiologicalChassis, action_type: str, cost: int) -> BiologicalChassis:
    """
    Executes a tactical beat for a BiologicalChassis, deducting resource costs.
    Strictly validates resource availability before deduction.
    
    Args:
        actor: The character chassis performing the action.
        action_type: The pool to deduct from ("stamina", "focus", or "move").
        cost: The amount to deduct.
        
    Returns:
        The updated BiologicalChassis state.
        
    Raises:
        ValueError: If resource pools are insufficient for the request.
    """
    if action_type == "stamina":
        if actor.pools.stamina.current >= cost:
            actor.pools.stamina.current -= cost
        else:
            raise ValueError("Insufficient Stamina for this beat.")
            
    elif action_type == "focus":
        if actor.pools.focus.current >= cost:
            actor.pools.focus.current -= cost
        else:
            raise ValueError("Insufficient Focus for this beat.")
            
    elif action_type == "move":
        # Move beats are typically free (cost=0), but if penalized by terrain/trauma,
        # they deduct from Stamina.
        if cost > 0:
            if actor.pools.stamina.current >= cost:
                actor.pools.stamina.current -= cost
            else:
                raise ValueError("Insufficient Stamina for this move beat.")
        # Free move beat does nothing to stamina
    
    else:
        # Non-pool action types could be added here later (e.g., social)
        pass
            
    return actor
