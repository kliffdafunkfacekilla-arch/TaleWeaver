from typing import Dict, List, Any, Optional
import entities

# ACTION_REGISTRY: Maps raw semantic actions to B.R.U.T.A.L Engine mechanics.
# Metadata includes category, valid target types, stamina cost, and primary stats involved.
ACTION_REGISTRY: Dict[str, Dict[str, Any]] = {
    "Attack": {
        "category": "Combat", "targets": ["hostile", "npc"], 
        "stats": ["Might", "Reflexes"], "cost": {"type": "stamina", "val": 2}
    },
    "Loot": {
        "category": "Intervention", "targets": ["item", "dead"], 
        "stats": ["Finesse", "Awareness"], "cost": {"type": "move", "val": 1}
    },
    "Examine": {
        "category": "Sensory", "targets": ["player", "npc", "hostile", "prop", "item"], 
        "stats": ["Awareness", "Logic", "Knowledge"], "cost": {"type": "focus", "val": 1}
    },
    "Talk": {
        "category": "Social", "targets": ["npc"], 
        "stats": ["Charm", "Intuition", "Logic"], "cost": {"type": "focus", "val": 1}
    },
    "Use": {
        "category": "Intervention", "targets": ["item", "prop"], 
        "stats": ["Finesse", "Knowledge"], "cost": {"type": "stamina", "val": 1}
    },
    "Move": {
        "category": "Tactical", "targets": ["location"], 
        "stats": ["Reflexes", "Endurance"], "cost": {"type": "move", "val": 1}
    }
}

def get_valid_actions(actor: entities.Entity, target: Optional[entities.Entity], learned_skills: List[str] = []) -> List[str]:
    """
    Computes all valid mechanical interactions between an actor and a target.
    
    Args:
        actor: The entity initiating the action.
        target: The entity being interacted with (can be None for area actions).
        learned_skills: Optional list of specific skill-based actions the actor can perform.
        
    Returns:
        List[str]: Names of all valid actions from REGISTRY or skills.
    """
    valid = []
    
    # Check general registry actions
    for name, data in ACTION_REGISTRY.items():
        if not target:
            if "location" in data["targets"]: valid.append(name)
            continue
            
        # Target-based filtering
        if target.type in data["targets"]:
            valid.append(name)
        elif any(tag in data["targets"] for tag in target.tags):
            valid.append(name)

    # Filter out dead targets for non-sensory/loot actions
    if target and "dead" in target.tags:
        valid = [a for a in valid if a in ["Loot", "Examine"]]

    # Character-specific skill overrides could go here
    for skill in learned_skills:
        # Complex skill validation would occur here based on skill.json metadata
        valid.append(skill)
        
    return list(set(valid))
