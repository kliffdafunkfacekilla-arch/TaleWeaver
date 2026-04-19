import aiohttp
import json
import asyncio
import os
import re

async def generate_flavor_text():
    """Reads the JSON state with non-blocking logic and asks Ollama to narrate it (Async)."""
    
    state_path = "state/local_map_state.json"
    state = None
    
    # Simple non-blocking retry attempt for Windows file locks
    for _ in range(5):
        try:
            if os.path.exists(state_path):
                with open(state_path, "r") as f:
                    state = json.load(f)
                    break
        except (PermissionError, json.JSONDecodeError):
            await asyncio.sleep(0.01)
            continue
    
    if not state:
        return "The Director is lost in thought (State Load Failed)."

    action = state.get("latest_action", {})
    directive = state.get("ai_directive", "Describe the scene.")
    
    prompt = f"""
    {directive}
    
    Current Action: {action.get('actor')} performed {action.get('action')} on {action.get('target')}.
    Mechanical Result: {action.get('mechanical_result')}
    Target Current Tags: {action.get('target_current_tags', [])}
    Map Environment Tags: {action.get('map_tags', [])}
    
    Write a vivid, 2-3 sentence description of this exact moment. Do not invent new actions.
    """

    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "llama3.1:8b-instruct-q3_K_L",
        "prompt": prompt,
        "stream": False,
        "options": {"num_ctx": 2048, "temperature": 0.7}
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=10) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("response", "The Director is silent.")
                return f"AI Service Error: HTTP {response.status}"
    except Exception as e:
        return f"AI Connection Failed: {e}"

class Narrator:
    def __init__(self, model="llama3.1:8b-instruct-q3_K_L", url="http://localhost:11434/api/generate"):
        self.model = model
        self.url = url

    async def narrate_turn_result(self, result, context):
        """Generates immersive narration for a specific game engine result."""
        prompt = f"""
        You are the Narrator for the grim-steampunk RPG Ostraka.
        Context: {context}
        Mechanical Result: {result}
        
        Narrate the outcome in a gritty, atmospheric style. Keep it to 2 sentences.
        """
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_ctx": 2048, "temperature": 0.8}
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.url, json=payload, timeout=10) as response:
                    res = await response.json()
                    return res.get("response", "Darkness swallows the details...")
        except Exception as e:
            return f"The gears of the world grind to a halt. ({e})"

    async def validate_deduction(self, deduction_text, evidence_list):
        """Asks the AI to judge if a player's deduction is supported by the gathered evidence."""
        prompt = f"""
        Role: Arbiter of Truth
        Player Deduction: "{deduction_text}"
        Evidence Gathered: {evidence_list}
        
        Is this deduction logically sound based STRICTLY on the evidence? 
        Respond with a JSON object: {{"is_valid": true/false, "explanation": "..."}}
        """
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_ctx": 2048, "temperature": 0.2}
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.url, json=payload, timeout=10) as response:
                    res = await response.json()
                    raw = res.get("response", "{}")
                    json_match = re.search(r'\{.*\}', raw, re.DOTALL)
                    if json_match: raw = json_match.group(0)
                    return json.loads(raw)
        except Exception as e:
            return {"is_valid": False, "explanation": f"Connection lost: {e}"}