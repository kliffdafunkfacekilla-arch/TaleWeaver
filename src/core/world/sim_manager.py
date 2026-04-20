from typing import Dict, Any, List
try:
    from core.world.time_manager import OstrakaCalendar
    from core.world.weather import WeatherSystem
except ImportError:
    # Fallback for root execution
    import sys
    import os
    sys.path.append(os.path.join(os.getcwd(), 'src'))
    from core.world.time_manager import OstrakaCalendar
    from core.world.weather import WeatherSystem

class SimulationManager:
    """
    Master controller for the Ostraka Clockwork Foundation.
    Unifies Time, Weather, and Aetheric Tension.
    """
    # Sacred Groves (Dragon Prisons) - Global Coordinates
    SACRED_GROVES = [(1,1), (1,8), (8,1), (8,8)]
    CONVERGENCE = (5, 5)

    def __init__(self, master_seed: int = 42):
        self.calendar = OstrakaCalendar()
        self.weather = WeatherSystem()
        self.seed = master_seed

    def pulse(self, hours_passed: int = 1):
        """Advances the simulation state."""
        self.calendar.advance_hours(hours_passed)
        info = self.calendar.get_current_info()
        self.weather.update(info)
        
    def get_aetheric_tension(self, gx: int, gy: int) -> float:
        """
        Calculates Tensegrity Tension based on distance to Convergence and Sacred Groves.
        """
        info = self.calendar.get_current_info()
        if info.get("is_shadow_week"):
            return 0.0  # SNAP-BACK
            
        # Distance to Convergence (Ground Zero)
        dx_c = gx - self.CONVERGENCE[0]
        dy_c = gy - self.CONVERGENCE[1]
        dist_c = (dx_c**2 + dy_c**2)**0.5
        
        # Distance to nearest Sacred Grove
        min_dist_g = min(((gx - px)**2 + (gy - py)**2)**0.5 for px, py in self.SACRED_GROVES)
        
        # Tension logic: Flows from Prisons to Convergence
        # Higher tension near groves, decreasing towards center
        tension = min(1.0, (min_dist_g / 5.0) + 0.1)
        return tension

    def get_atmospheric_state(self, gx: int, gy: int) -> Dict[str, Any]:
        """Provides full context for the Map Generator."""
        info = self.calendar.get_current_info()
        weather = self.weather.get_state()
        tension = self.get_aetheric_tension(gx, gy)
        
        # Chaos Modifier
        chaos_mod = 0.0
        if info.get("is_moon_surge"): chaos_mod += 0.2
        if weather["state"] == "Aetheric Surge": chaos_mod += 0.3
        
        return {
            "calendar": info,
            "weather": weather,
            "aetheric_tension": tension,
            "chaos_modifier": chaos_mod
        }
