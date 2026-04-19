import sqlite3
import json
import requests
import os

# --- PATH CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'state', 'shatterlands.db')
CAMPAIGN_SAVE_PATH = os.path.join(BASE_DIR, 'data', 'Saves', 'campaign_active.json')

# --- OLLAMA CONFIGURATION ---
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "llama3.1:8b-instruct-q3_K_L"

class CampaignDirector:
    def __init__(self):
        self.db_path = DB_PATH
        os.makedirs(os.path.dirname(CAMPAIGN_SAVE_PATH), exist_ok=True)
        
    def _get_db_connection(self):
        return sqlite3.connect(self.db_path)

    def get_regional_context(self, l4_x, l4_y, l3_x, l3_y):
        context = {
            "macro_cell": f"L4[{l4_x},{l4_y}]",
            "micro_cell": f"L3[{l3_x},{l3_y}]",
            "ruling_faction": "Unknown Faction",
            "local_biome": "Uncharted Wilderness",
            "world_threat_level": "Moderate"
        }
        
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT n_biome, faction FROM map_layer4 WHERE x=? AND y=?", (l4_x, l4_y))
                row = cursor.fetchone()
                
                if row:
                    context['local_biome'] = row[0] if row[0] else "Uncharted Wilderness"
                    context['ruling_faction'] = row[1] if row[1] else "Unknown Faction"
                    
        except sqlite3.OperationalError as e:
            print(f"DB Warning: Could not fetch map data ({e}). Using default context.")

        return context

    def generate_macro_arc(self, l4_x, l4_y, l3_x, l3_y):
        print(f"DM Lens focused on L4[{l4_x},{l4_y}] -> L3[{l3_x},{l3_y}]...")
        world_data = self.get_regional_context(l4_x, l4_y, l3_x, l3_y)
        
        prompt = f"""You are the Dungeon Master for the RPG 'Ostraka'. 
        The player is currently in {world_data['macro_cell']}, sub-region {world_data['micro_cell']}.
        
        CURRENT WORLD STATE:
        - Ruling Faction: {world_data['ruling_faction']}
        - Biome: {world_data['local_biome']}
        
        Write a 2 to 3 sentence 'Macro Arc' describing a major background conflict or event currently happening in this exact region. 
        This is NOT a direct quest for the player yet; it is a living world event.
        
        Rules:
        - Use the specific faction and biome provided.
        - Return ONLY the text of the arc. No conversational filler, no markdown formatting.
        """

        payload = {
            "model": MODEL,
            "prompt": prompt,
            "stream": False
        }
        
        print(f"Thinking: LLM is architecting the regional conflict...")
        try:
            response = requests.post(OLLAMA_URL, json=payload)
            response.raise_for_status()
            arc_text = response.json().get('response', '').strip()
            self._save_arc(world_data, arc_text)
            return arc_text
            
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to Ollama Brain: {e}")
            return None

    def _save_arc(self, world_data, arc_text):
        save_data = {
            "current_location": world_data,
            "active_macro_arc": arc_text,
            "quests_completed": 0
        }
        with open(CAMPAIGN_SAVE_PATH, 'w') as f:
            json.dump(save_data, f, indent=4)
        print(f"Macro Arc saved to data/Saves/campaign_active.json")

if __name__ == "__main__":
    dm = CampaignDirector()
    print("Initializing Campaign Engine...")
    arc = dm.generate_macro_arc(l4_x=5, l4_y=5, l3_x=42, l3_y=12)
    
    if arc:
        print("\n=== CURRENT MACRO ARC ===")
        print(arc)
        print("=========================\n")
