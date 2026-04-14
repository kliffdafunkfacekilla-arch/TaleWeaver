import urllib.request
import json
import time
import os

def generate_flavor_text():
    """Reads the JSON state with a retry loop and asks Ollama to narrate it."""
    
    # 1. Read the current game state with Windows-safe retries
    state = None
    state_path = "state/local_map_state.json"
    for _ in range(5):
        try:
            with open(state_path, "r") as f:
                state = json.load(f)
                break
        except (PermissionError, json.JSONDecodeError):
            time.sleep(0.01)
            continue
        except Exception:
            break

    if not state:
        return "The Director is lost in thought (State Load Failed)."

    # 2. Build the Prompt for the AI
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

    # 3. The API Call to Ollama (WITH MEMORY CLAMPS)
    url = "http://localhost:11434/api/generate"
    
    payload = {
        "model": "llama3.1:8b-instruct-q3_K_L", # Exactly the model you have installed!
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_ctx": 2048,       # <--- THE FIX: Restricts context memory to save RAM!
            "temperature": 0.7     # Keeps the AI creative but focused
        }
    }

    headers = {"Content-Type": "application/json"}
    data = json.dumps(payload).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result.get("response", "The Director is silent.")
    except Exception as e:
        return f"AI Connection Failed (Ollama). ({e})"

if __name__ == "__main__":
    # Test it directly!
    print("Testing clamped memory generation...")
    print(generate_flavor_text())