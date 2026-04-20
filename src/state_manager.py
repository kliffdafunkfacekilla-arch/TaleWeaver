import json
import os
import time
from typing import Dict, Any, Optional

# LOCAL STATE CONFIGURATION
STATE_FILE = "state/local_map_state.json"
MAX_RETRIES = 5
RETRY_DELAY = 0.05 # Seconds

def sanitize_for_json(data: Any) -> Any:
    """
    Recursively sweeps a dictionary/list and removes or replaces surrogate 
    characters that would cause 'utf-8' encoding errors on Windows.
    """
    if isinstance(data, str):
        # Encode to bytes and back, ignoring surrogates, to ensure valid UTF-8
        return data.encode('utf-8', 'ignore').decode('utf-8')
    elif isinstance(data, list):
        return [sanitize_for_json(item) for item in data]
    elif isinstance(data, dict):
        return {key: sanitize_for_json(value) for key, value in data.items()}
    return data

def load_state() -> Dict[str, Any]:
    """
    Retrieves the current world state from the local JSON file.
    Includes a retry loop to handle concurrent access issues during AI generation.
    """
    if not os.path.exists(STATE_FILE):
        return {}
        
    for _ in range(MAX_RETRIES):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (PermissionError, json.JSONDecodeError):
            time.sleep(RETRY_DELAY)
    return {}

def save_state(state: Dict[str, Any]):
    """
    Persists the world state to the local JSON file.
    Includes a sanitization pass to prevent surrogate encoding crashes.
    """
    import db_manager 
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    
    # Sanitize state to remove surrogates that crash the UTF-8 encoder
    clean_state = sanitize_for_json(state)
    
    for _ in range(MAX_RETRIES):
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(clean_state, f, cls=db_manager.PydanticEncoder, indent=2, ensure_ascii=False)
            return
        except (PermissionError, UnicodeEncodeError) as e:
            if isinstance(e, UnicodeEncodeError):
                # Fallback: strict ASCII if UTF-8 still fails after sanitization
                with open(STATE_FILE, "w", encoding="utf-8") as f:
                    json.dump(clean_state, f, cls=db_manager.PydanticEncoder, indent=2, ensure_ascii=True)
                return
            time.sleep(RETRY_DELAY)
            
    print("[Error] Failed to save local state after multiple retries.")
