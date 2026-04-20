from typing import Dict, List, Any, Tuple

class OstrakaCalendar:
    """
    The Ostraka Clockwork Calendar Engine.
    Tracks a 539-day year, 7-day weeks, and the 49-day Cruorbus moon cycles.
    """
    WEEKDAYS = ["Spireday", "Ironday", "Whispday", "Heartday", "Mindday", "Bloodday", "Shadowday"]
    MONTHS = [
        "Month of the Hearth", "Month of the Ember", "Month of the Forge",
        "Month of the Sledge", "Month of the Bellows", "Month of the Anvil",
        "Month of the Quench", "Month of the Blade", "Month of the Steam",
        "Month of the Gear", "Month of the Crank", "Month of the Shadow"
    ]
    SEASONS = [
        "Season of Sparks", "Season of Bloom", "Season of Blazes", "Season of Harvest",
        "Season of Chill", "Season of Frost", "Season of Rime", "Season of Thaw"
    ]

    def __init__(self, year: int = 1, day: int = 1, hour: int = 12):
        self.year = year
        self.total_days = day
        self.hour = hour

    def advance_hours(self, hours: int) -> str:
        """
        Advances the clock and updates current calendar state.
        """
        self.hour += hours
        while self.hour >= 24:
            self.hour -= 24
            self.total_days += 1
        
        while self.total_days > 539:
            self.total_days -= 539
            self.year += 1
            
        return self.get_formatted_time()

    def get_current_info(self) -> Dict[str, Any]:
        """Calculates current date and celestial components."""
        day_idx = (self.total_days - 1)
        
        # Month: 11 months of 45 days, 1 month of 44 days (Total 539)
        month_idx = min(day_idx // 45, 11)
        day_of_month = (day_idx % 45) + 1
        weekday = self.WEEKDAYS[day_idx % 7]
        
        # Year Wobble (Upper: first 269 days, Lower: last 270 days)
        wobble = "Upper Wobble" if self.total_days <= 269 else "Lower Wobble"
        
        # Season Logic (8 seasons, roughly 67 days each)
        season_idx = min(day_idx // 67, 7)
        season = self.SEASONS[season_idx]
        
        # Shadow Week Check (Days 533-539)
        is_shadow_week = self.total_days >= 533
        
        # Moon Phase (49-day cycle for Cruorbus)
        # Resting (24.5 days), Surge (24.5 days)
        moon_day = day_idx % 49
        if moon_day < 24.5:
            phase = "Resting State (Purple)"
            is_surge = False
        else:
            phase = "Surge State (Red)"
            is_surge = True
            
        # Cruorbus context (Leering/Silent based on Wobble)
        moon_aspect = "The Leering" if wobble == "Upper Wobble" else "The Blood-Eye"

        return {
            "year": self.year,
            "total_days": self.total_days,
            "month": self.MONTHS[month_idx],
            "day": day_of_month,
            "weekday": weekday,
            "hour": self.hour,
            "wobble": wobble,
            "season": season,
            "is_shadow_week": is_shadow_week,
            "moon_phase": f"{phase} - {moon_aspect}",
            "is_moon_surge": is_surge
        }

    def get_formatted_time(self) -> str:
        info = self.get_current_info()
        shadow_str = " [SHADOW WEEK]" if info["is_shadow_week"] else ""
        return (f"Year {info['year']}{shadow_str}, {info['weekday']}, "
                f"{info['month']} ({info['season']}). "
                f"Clock: {info['hour']:02d}:00. Moon: {info['moon_phase']}")
