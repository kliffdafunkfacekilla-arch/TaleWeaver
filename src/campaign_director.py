import json
import os
import random
import aiohttp
import asyncio
from typing import Dict, Any, Optional, List

# AI CONFIGURATION
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1:8b-instruct-q3_K_L"

class CampaignDirector:
    """
    The Campaign Director: Manages macro-level story progression, 
    faction relationships, and global world events.
    """
    def __init__(self):
        """Initializes the director with default campaign paths."""
        self.campaign_path = "data/Saves/campaign_active.json"
        self.faction_state_path = "data/factions.json"

    async def check_world_event_trigger(self, player_stats: Dict[str, int]) -> Optional[str]:
        """
        Determines if a global narrative event (e.g. Faction War, Plague) 
        should trigger based on player actions and world state.
        
        Args:
            player_stats: Summary of player accomplishments/notoriety.
            
        Returns:
            Optional[str]: Description of the triggered event or None.
        """
        # ... logic for global event triggers ...
        return None

    async def generate_faction_rumor(self, faction: str) -> str:
        """
        Generates a localized rumor about a specific faction using AI.
        
        Args:
            faction: Name of the faction (e.g. 'sump_kin').
            
        Returns:
            str: A short narrative rumor string.
        """
        prompt = f"""
        You are a shifty informant in the back-alleys of Ostraka.
        Tell a 1-sentence rumor about the '{faction}' faction. 
        Focus on their latest shadowy movements or internal strife.
        """
        
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(OLLAMA_URL, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("response", "They say something is stirring in the depths.")
        except Exception:
            pass
        return "The shadows have ears, but they aren't talking today."

    def get_faction_reputation(self, faction: str) -> int:
        """Retrieves player reputation score for a specific faction."""
        if not os.path.exists(self.faction_state_path): return 0
        try:
            with open(self.faction_state_path, "r") as f:
                data = json.load(f)
                return data.get(faction, {}).get("reputation", 0)
        except Exception:
            return 0
            
    def update_faction_reputation(self, faction: str, delta: int):
        """Modifies player reputation for a specific faction and persists to disk."""
        if not os.path.exists(self.faction_state_path): return
        try:
            with open(self.faction_state_path, "r") as f:
                data = json.load(f)
            
            if faction not in data: data[faction] = {"reputation": 0}
            data[faction]["reputation"] += delta
            
            with open(self.faction_state_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[Director Error] Failed to update faction rep: {e}")
