import json
import os
import time
from typing import Dict, Any, Optional

# LOCAL STATE CONFIGURATION
STATE_FILE = "state/local_map_state.json"
MAX_RETRIES = 5
RETRY_DELAY = 0.05 # Seconds

def load_state() -> Dict[str, Any]:
    """
    Retrieves the current world state from the local JSON file.
    Includes a retry loop to handle concurrent access issues during AI generation.
    
    Returns:
        Dict[str, Any]: The parsed game state dictionary.
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
    Uses Pydantic serialization for complex entity models via custom logic 
    (or assumes strings are pre-serialized).
    
    Args:
        state (Dict[str, Any]): The world state to save.
    """
    # Import here to avoid circular dependencies
    import db_manager 
    
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    
    for _ in range(MAX_RETRIES):
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                # Use the PydanticEncoder from db_manager
                json.dump(state, f, cls=db_manager.PydanticEncoder, indent=2)
            return
        except PermissionError:
            time.sleep(RETRY_DELAY)
            
    print("[Error] Failed to save local state after multiple retries.")
