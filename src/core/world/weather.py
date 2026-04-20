import random
from typing import Dict, Any

class WeatherSystem:
    """
    Manages global and localized atmospheric conditions in Ostraka.
    Reacts to celestial mechanics (Moon states).
    """
    STATES = ["Clear", "Overcast", "Rain", "Storm", "Aetheric Surge"]

    def __init__(self):
        self.current_state = "Clear"
        self.intensity = 0.1

    def update(self, calendar_info: Dict[str, Any]):
        """
        Updates weather state based on time and moon phase.
        """
        is_surge = calendar_info.get("is_moon_surge", False)
        is_shadow = calendar_info.get("is_shadow_week", False)
        
        # Base transition weights
        weights = [0.5, 0.3, 0.1, 0.05, 0.05]
        
        if is_surge:
            # Shift towards Storm and Surge
            weights = [0.2, 0.2, 0.2, 0.2, 0.2]
        
        if is_shadow:
            # Eerie stillness or pure surge
            weights = [0.1, 0.6, 0.0, 0.0, 0.3]

        self.current_state = random.choices(self.STATES, weights=weights)[0]
        self.intensity = random.uniform(0.1, 1.0)
        
        if self.current_state == "Storm":
            self.intensity = random.uniform(0.7, 1.0)
            
    def get_state(self) -> Dict[str, Any]:
        return {
            "state": self.current_state,
            "intensity": self.intensity
        }
