import json
import os
import threading
from typing import Dict, Any, Optional
from . import db_manager
from .entities import Entity

class StateManager:
    _instance = None
    _lock = threading.Lock()
    _state_path = "state/local_map_state.json"
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(StateManager, cls).__new__(cls)
                    cls._instance.state_cache: Optional[Dict[str, Any]] = None
        return cls._instance

    def load_state(self) -> Dict[str, Any]:
        """Loads state from memory or safely from disk with Pydantic validation."""
        with self._lock:
            if self.state_cache is not None:
                return self.state_cache
                
            if not os.path.exists(self._state_path): 
                return {}
                
            try:
                with open(self._state_path, "r") as f:
                    data = json.load(f)
                    self.state_cache = self._process_pydantic_entities(data)
                    return self.state_cache
            except (json.JSONDecodeError, IOError) as e:
                print(f"⚠️ State Load Error: {e}")
                return {}

    def save_state(self, state: Dict[str, Any]):
        """Updates cache and writes to disk/DB with Pydantic serialization."""
        with self._lock:
            self.state_cache = state
            try:
                os.makedirs(os.path.dirname(self._state_path), exist_ok=True)
                # Serialize Pydantic entities back to dicts for JSON storage
                serializable_state = self._serialize_pydantic_entities(state)
                with open(self._state_path, "w") as f: 
                    json.dump(serializable_state, f, indent=2)
            except IOError as e:
                print(f"⚠️ State Save Error: {e}")
            
            # Sync to DB if it's a chunk
            meta = state.get("meta", {})
            g_pos = meta.get("global_pos", [0,0])
            db_manager.save_chunk(g_pos[0], g_pos[1], state)

    def _process_pydantic_entities(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Converts raw entity dictionaries into Pydantic Entity models."""
        if "local_map_state" in state and "entities" in state["local_map_state"]:
            raw_entities = state["local_map_state"]["entities"]
            state["local_map_state"]["entities"] = [
                Entity.model_validate(e) if isinstance(e, dict) else e 
                for e in raw_entities
            ]
        return state

    def _serialize_pydantic_entities(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Converts Pydantic Entity models back into raw dictionaries for JSON."""
        # Deep copy the state structure to avoid mutating the live cache with dicts
        # BUT we only need to convert entities for serialization
        state_copy = state.copy()
        if "local_map_state" in state_copy and "entities" in state_copy["local_map_state"]:
            ents = state_copy["local_map_state"]["entities"]
            state_copy["local_map_state"] = state_copy["local_map_state"].copy()
            state_copy["local_map_state"]["entities"] = [
                e.model_dump() if hasattr(e, "model_dump") else e 
                for e in ents
            ]
        return state_copy

def load_state() -> Dict[str, Any]:
    return StateManager().load_state()

def save_state(state: Dict[str, Any]):
    StateManager().save_state(state)
