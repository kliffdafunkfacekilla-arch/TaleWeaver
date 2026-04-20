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
        """
        # ... logic for global event triggers ...
        return None

    async def generate_faction_rumor(self, faction: str) -> str:
        """
        Generates a localized rumor about a specific faction using AI.
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

    def evaluate_spawns(self, global_pos: List[int], quest_deck: List[Dict[str, Any]], chaos_level: int = 5) -> List[Dict[str, Any]]:
        """
        Determines which NPCs/Objects should spawn on a local map based on narrative context.
        """
        spawns = []
        
        # 1. Quest Spawns (Highest Priority)
        if quest_deck:
            current_node = quest_deck[0]
            if current_node.get("type") in ["combat", "climax", "scout"]:
                faction = current_node.get("faction", "wild_beasts")
                threat = current_node.get("threat", 1)
                
                if current_node.get("type") == "climax":
                    spawns.append({
                        "name": f"{faction.capitalize()} Leader",
                        "type": "hostile",
                        "tags": ["hostile", "elite", faction]
                    })
                
                for i in range(random.randint(1, threat + 1)):
                    spawns.append({
                        "name": f"{faction.capitalize()} Scout",
                        "type": "hostile",
                        "tags": ["hostile", faction]
                    })

        # 2. Random Disruptions (Only if Chaos Level is high)
        if chaos_level > 15:
            if random.random() < 0.3:
                spawns.append({
                    "name": "Opportunistic Scavenger",
                    "type": "hostile",
                    "tags": ["hostile", "neutral"]
                })

        # 3. Static/Atmospheric NPCs (Non-Hostile)
        if random.random() < 0.1:
            spawns.append({
                "name": "Wandering Nomad",
                "type": "npc",
                "tags": ["friendly", "trader"]
            })
            
        return spawns

class CampaignWeaver:
    """
    The Campaign Weaver: Architect of the hidden 'Iceberg' narrative.
    Connects side-quests to a long-term cosmic or political master plot.
    """
    def __init__(self):
        self.ollama_url = OLLAMA_URL
        self.model = OLLAMA_MODEL

    async def generate_master_arc(self) -> Optional[Any]:
        """
        Generates a 5-Act hidden plot involving two major factions and a cosmic threat.
        Returns a MasterArc Pydantic model populated via AI.
        """
        prompt = """
        You are the Master Storyteller for Ostraka, a gritty steampunk-fantasy world.
        Generate a 'Master Arc' for a long-term campaign.
        Include:
        - A major antagonist faction from: sump_kin, iron_caldera, imperial_remnant.
        - A cosmic or existential threat.
        - A target objective (e.g., 'The Lith-Siphon', 'The Clockwork Moon').
        - 3 to 5 'Key Nouns' (locations, artifacts, or characters) central to the plot.
        
        Respond in JSON format:
        {
            "antagonist_faction": "string",
            "target_objective": "string",
            "key_nouns": ["string", "string"]
        }
        """
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.ollama_url, json=payload, timeout=20) as response:
                    if response.status == 200:
                        data = await response.json()
                        raw = json.loads(data.get("response", "{}"))
                        # Import here to avoid circular dependencies
                        from core.schemas import MasterArc
                        return MasterArc(**raw)
        except Exception as e:
            print(f"[Weaver Error] Failed to generate plot: {e}")
            
        return None

    def evaluate_tension(self, arc: Any) -> int:
        """
        Calculates a world 'Tension' bonus based on the current Act of the master arc.
        As the arc progresses, encounters become more frequent and lethal.
        """
        if not arc: return 0
        return arc.current_act * 5 # Adds +5 chaos/threat per Act
