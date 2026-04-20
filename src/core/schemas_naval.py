from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum

class ShipComponentType(str, Enum):
    ENGINE = "Engine"
    HULL = "Hull"
    WEAPON = "Weapon"
    QUARTERS = "Quarters"
    UTILITY = "Utility"

class ShipComponent(BaseModel):
    """
    Modular component of an Aether-Skiff.
    """
    id: str
    name: str
    type: ShipComponentType
    max_integrity: int
    current_integrity: int
    power_draw: int
    
    @property
    def is_operational(self) -> bool:
        return self.current_integrity > 0

class AetherSkiff(BaseModel):
    """
    Representation of an airship in the Ostraka naval system.
    """
    ship_id: str
    name: str
    ship_class: str # e.g., "Light Skiff", "Heavy Galleon"
    max_fuel: int
    current_fuel: int
    components: List[ShipComponent]
    cargo: List[str] = []
    
    # Transient fields for combat/travel (not typically persisted in character sheet but part of naval state)
    evasion_tokens: int = 0
    distance_closed: bool = False # For boarding trigger
    tags: List[str] = [] # e.g., ["Stranded"]

    @property
    def total_power_draw(self) -> int:
        """Sum of power draw from all operational components."""
        return sum(c.power_draw for c in self.components if c.is_operational)

    @property
    def has_quarters(self) -> bool:
        """Check if any operational component is of type Quarters."""
        return any(c.type == ShipComponentType.QUARTERS and c.is_operational for c in self.components)

    def get_component(self, component_type: ShipComponentType) -> Optional[ShipComponent]:
        """Returns the first component of a specific type."""
        for c in self.components:
            if c.type == component_type:
                return c
        return None
