import json
import os
import threading
import db_manager

class StateManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StateManager, cls).__new__(cls)
            cls._instance.state_cache = None
        return cls._instance

    def load_state(self):
        """Loads state from memory if available, otherwise safely reads from disk."""
        with self._lock:
            if self.state_cache is not None:
                return self.state_cache
                
            if not os.path.exists("local_map_state.json"): 
                return None
                
            try:
                with open("local_map_state.json", "r") as f:
                    self.state_cache = json.load(f)
                    return self.state_cache
            except (json.JSONDecodeError, IOError) as e:
                print(f"⚠️ State Load Error: {e}")
                return None

    def save_state(self, state):
        """Updates memory cache and safely writes to disk/DB."""
        with self._lock:
            self.state_cache = state
            try:
                with open("local_map_state.json", "w") as f: 
                    json.dump(state, f, indent=2)
            except IOError as e:
                print(f"⚠️ State Save Error: {e}")
            
            # Auto-sync to DB
            if "local_map_state" in state and "meta" in state["local_map_state"]:
                g_pos = state["local_map_state"]["meta"].get("global_pos", [0,0])
                db_manager.save_chunk(g_pos[0], g_pos[1], state)

def load_state():
    state = StateManager().load_state()
    # Note: start_new_game() is usually in engine.py to avoid circularity.
    # We will import it locally or assume it's handled by the caller if it returns None.
    return state

def save_state(state):
    StateManager().save_state(state)
