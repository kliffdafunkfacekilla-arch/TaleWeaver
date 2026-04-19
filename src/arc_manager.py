import json
import os
import sqlite3
import aiohttp
import re
import asyncio
from typing import Dict, Any, Optional

# AI CONFIGURATION
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.1:8b-instruct-q3_K_L"

class StoryArchitect:
    """
    The Story Architect: Responsible for generating high-level narrative blueprints
    and reactive quest consequences based on world disruptions.
    """
    def __init__(self):
        """Initializes the architect with the default save path for active campaigns."""
        self.save_path = "data/Saves/campaign_active.json"

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Robustly extracts and parses JSON from an AI natural language response."""
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                return None
        return None

    async def generate_arc_blueprint(self, region_x: int, region_y: int, faction: str, biome: str, chaos_level: int) -> Optional[Dict[str, Any]]:
        """
        Generates a 3-node quest arc blueprint based strictly on world state.
        
        Args:
            region_x, region_y: Global coordinates of the quest origin.
            faction: The ruling faction of the region.
            biome: The environmental type of the region.
            chaos_level: The local instability level (0-20).
            
        Returns:
            Optional[Dict[str, Any]]: The quest arc JSON blueprint.
        """
        prompt = f"""
        You are the master Campaign Director for the grim-steampunk RPG Ostraka.
        Generate a 3-node quest arc for the player based strictly on this world state:
        - Location: {biome} at [{region_x}, {region_y}]
        - Ruling Faction: {faction}
        - Chaos Level: {chaos_level}/20

        RULES:
        1. Return ONLY valid JSON.
        2. The 'locked_goal' must be a physical object or person that exists in the world.
        3. Each node must have: 'title', 'task', 'target_entity_type', and 'physics_requirement'.
        """
        
        payload = {
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(OLLAMA_URL, json=payload, timeout=20) as response:
                    if response.status == 200:
                        data = await response.json()
                        raw_content = data.get("response", "")
                        blueprint = self._extract_json(raw_content)
                        return blueprint
        except Exception as e:
            print(f"[Architect Error] AI failed: {e}")
        return None

    async def inject_consequence_node(self, player_action: str, world_impact_summary: str) -> bool:
        """
        Mutates the active campaign JSON to inject a 'friction' node when the player 
        causes a major world disruption.
        
        Args:
            player_action: What the player did (e.g. 'Murdered the quest giver').
            world_impact_summary: The mechanical result (e.g. 'Faction hostility increased').
            
        Returns:
            bool: True if the consequence was successfully injected.
        """
        if not os.path.exists(self.save_path): return False

        try:
            with open(self.save_path, "r") as f:
                arc_data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return False

        current_idx = arc_data.get("current_node_index", 0)
        nodes = arc_data.get("nodes", [])
        if current_idx >= len(nodes): return False
        
        current_node = nodes[current_idx]
        locked_goal = arc_data.get("locked_goal", "Unknown Objective")

        prompt = f"""
        You are the Campaign Director for Ostraka. The player has severely disrupted the current quest.
        - Locked Goal: {locked_goal}
        - Supposed Task: {current_node.get('task')}
        - Player Action: {player_action}
        - Impact: {world_impact_summary}

        Generate ONE new dynamic quest node (JSON) that forces the player to deal with the fallout.
        """

        payload = {"model": MODEL, "prompt": prompt, "stream": False, "format": "json"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(OLLAMA_URL, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        new_node = self._extract_json(data.get("response", ""))
                        if new_node:
                            # Inject immediately after current node
                            nodes.insert(current_idx + 1, new_node)
                            arc_data["nodes"] = nodes
                            with open(self.save_path, "w") as f:
                                json.dump(arc_data, f, indent=2)
                            return True
        except Exception as e:
            print(f"[Architect Error] Injected consequence failed: {e}")
            
        return False
