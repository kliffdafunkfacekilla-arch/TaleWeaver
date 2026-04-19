import json
import os
import sqlite3
import requests
import re

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.1:8b-instruct-q3_K_L"

class StoryArchitect:
    def __init__(self):
        self.save_path = "data/Saves/campaign_active.json"

    def _extract_json(self, text):
        """Robustly extracts JSON from an AI response regardless of markdown formatting."""
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                return None
        return None

    def generate_arc_blueprint(self, region_x, region_y, faction, biome, chaos_level):
        """Generates a strict JSON narrative blueprint based on world state."""
        prompt = f"""
        You are the master Campaign Director for the grim-steampunk RPG Ostraka.
        Generate a 3-node quest arc for the player based strictly on this world state:
        - Location: {biome} at [{region_x}, {region_y}]
        - Ruling Faction: {faction}
        - Chaos Level: {chaos_level}/20

        RULES:
        1. Return ONLY valid JSON. Do not include markdown formatting or conversational text.
        2. The 'locked_goal' must be a physical, achievable objective.
        3. Node 1 must be 'social' or 'investigation'. Node 2 must be 'exploration' or 'hazard'. Node 3 must be 'climax' or 'combat'.

        JSON SCHEMA:
        {{
          "arc_name": "Title of the Arc",
          "locked_goal": "The ultimate unchangeable objective",
          "nodes": [
            {{"id": "1", "type": "...", "task": "...", "status": "pending"}},
            {{"id": "2", "type": "...", "task": "...", "status": "locked"}},
            {{"id": "3", "type": "...", "task": "...", "status": "locked"}}
          ],
          "current_node_index": 0
        }}
        """

        payload = {
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.7, "num_ctx": 2048}
        }

        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=45)
            response.raise_for_status()
            blueprint = self._extract_json(response.json().get("response", ""))
            return blueprint
        except Exception as e:
            print(f"[Error] Failed to generate arc blueprint: {e}")
            return None

    def inject_consequence_node(self, player_action, world_impact_summary):
        """Mutates the active campaign JSON by injecting a consequence node based on disruption."""
        if not os.path.exists(self.save_path):
            print("[Error] No active campaign found to mutate.")
            return False

        try:
            with open(self.save_path, "r") as f:
                campaign = json.load(f)

            locked_goal = campaign.get("locked_goal", "Unknown objective")
            idx = campaign.get("current_node_index", 0)
            
            if idx >= len(campaign["nodes"]):
                return False

            current_node = campaign["nodes"][idx]
            current_id = str(current_node.get("id", "1"))

            prompt = f"""
            You are the Campaign Director for Ostraka. The player has severely disrupted the current quest.
            - Locked Goal: {locked_goal}
            - Current Task: {current_node.get('task')}
            - Player Action: {player_action}
            - World Consequence: {world_impact_summary}

            Generate ONE new dynamic quest node that forces the player to deal with the immediate fallout. 
            Respond ONLY in valid JSON.
            SCHEMA: {{ "type": "consequence", "task": "..." }}
            """

            payload = {
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.8, "num_ctx": 2048}
            }

            response = requests.post(OLLAMA_URL, json=payload, timeout=45)
            response.raise_for_status()
            consequence_data = self._extract_json(response.json().get("response", ""))
            if not consequence_data: return False

            # SAFE ID ASSIGNMENT: String suffix prevents ID math collisions
            # Using current_id + a unique sub-index
            sub_count = sum(1 for n in campaign["nodes"] if str(n.get("id", "")).startswith(f"{current_id}-"))
            new_id = f"{current_id}-FALLOUT-{sub_count + 1}"

            consequence_node = {
                "id": new_id,
                "type": consequence_data.get("type", "consequence"),
                "task": consequence_data.get("task", "Deal with the consequences."),
                "status": "pending"
            }

            # Insert at current_node_index, pushing original node down
            campaign["nodes"].insert(idx, consequence_node)
            
            with open(self.save_path, "w") as f:
                json.dump(campaign, f, indent=4)

            print(f"\n⚠️ CONSEQUENCE INJECTED: Node {new_id}")
            return True

        except Exception as e:
            print(f"[Error] Failed to inject consequence: {e}")
            return False

    def save_blueprint(self, blueprint_json):
        if not blueprint_json: return False
        try:
            os.makedirs(os.path.dirname(self.save_path), exist_ok=True)
            with open(self.save_path, "w") as f:
                json.dump(blueprint_json, f, indent=4)
            return True
        except Exception as e:
            print(f"[Error] Failed to save blueprint: {e}")
            return False

if __name__ == "__main__":
    architect = StoryArchitect()
    # Test would go here
