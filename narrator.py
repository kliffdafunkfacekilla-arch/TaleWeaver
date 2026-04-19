import urllib.request
import json
import time

def generate_flavor_text():
    """Reads the JSON state with a retry loop and asks Ollama to narrate it."""
    state = None
    for _ in range(5):
        try:
            with open("local_map_state.json", "r") as f:
                state = json.load(f)
                break
        except (PermissionError, json.JSONDecodeError):
            time.sleep(0.01)
            continue
        except Exception:
            break

    if not state:
        return "The Director is lost in thought (State Load Failed)."

    entities_list = state.get("local_map_state", {}).get("entities", [])
    player = next((e for e in entities_list if e.get("type") == "player"), None)
    surroundings = []
    
    if player:
        px, py = player["pos"]
        for e in entities_list:
            if e == player or e.get("hp", 0) <= 0: continue
            ex, ey = e["pos"]
            dist = max(abs(px - ex), abs(py - ey))
            if dist <= 8:
                surroundings.append(f"{e['name']} ({dist} tiles away, tags: {e.get('tags',[])})")

    action = state.get("latest_action", {})
    directive = state.get("ai_directive", "Describe the scene.")
    mode = state.get("local_map_state", {}).get("meta", {}).get("encounter_mode", "EXPLORE")
    
    prompt = f"""
    {directive}
    Current Mode: {mode}
    Nearby Signs of Life: {", ".join(surroundings) if surroundings else "None visible."}
    Current Action: {action.get('actor')} performed {action.get('action')} on {action.get('target')}.
    Mechanical Result: {action.get('mechanical_result')}
    
    Write a vivid, 2-3 sentence description of this exact moment in a dark fantasy setting. 
    """

    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "llama3.1:8b-instruct-q3_K_L",
        "prompt": prompt,
        "stream": False,
        "options": {"num_ctx": 2048, "temperature": 0.7}
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result.get("response", "The Director is silent.")
    except Exception:
        return "The AI is flickering..."

class Narrator:
    def __init__(self, model="llama3.1:8b-instruct-q3_K_L", url="http://localhost:11434/api/generate"):
        self.model = model
        self.url = url

    def narrate_turn_result(self, engine_result, world_context):
        """Translates mechanical results into immersive prose via Ollama."""
        system_prompt = (
            "You are the Dungeon Master for TaleWeaver, a gritty dark fantasy RPG. "
            "STAY STRICTLY CONSISTENT with the SUCCESS or FAIL status and the mechanical log. "
            "End your narration by asking the player: 'What do you do?'"
        )

        prompt = (
            f"System: {system_prompt}\n"
            f"World Context: {world_context}\n"
            f"Mechanical Result: {engine_result}\n"
            "Narrate the result of the action:"
        )

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_ctx": 2048, "temperature": 0.8}
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(self.url, data=data, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=15) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result.get("response", "The Director is silent.")
        except Exception:
            return f"[Narrator Offline] {engine_result.get('status', 'ERROR')}: {engine_result.get('event', '...')}"

    def validate_deduction(self, player_deduction, truth_table, discovered_clues):
        """
        AI Logical Judge: Validates a player's free-text deduction against hidden truths.
        Returns a JSON with {"success": bool, "feedback": string}
        """
        prompt = f"""
        You are the Logic Engine for a Mystery Game.
        HIDDEN TRUTH: {truth_table}
        CLUES PLAYER HAS FOUND: {discovered_clues}
        PLAYER'S DEDUCTION: "{player_deduction}"
        
        Is the player's deduction logically sound and correct based on the HIDDEN TRUTH?
        They don't need to match the truth word-for-word, but they must identify the core facts (who, where, what).
        
        Respond ONLY in JSON:
        {{
            "success": true/false,
            "feedback": "A very brief narrative reaction to their claim."
        }}
        """
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(self.url, data=data, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=15) as response:
                res = json.loads(response.read().decode("utf-8"))
                return json.loads(res.get("response", '{"success": false, "feedback": "Your thoughts remain clouded."}'))
        except Exception:
            return {"success": False, "feedback": "The deduction logic is currently unstable."}