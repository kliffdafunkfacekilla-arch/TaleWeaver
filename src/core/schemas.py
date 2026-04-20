from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from enum import Enum

class GettableModel(BaseModel):
    """Base model that provides .get() for dictionary-style compatibility."""
    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

class CoreStats(GettableModel):
    """
    Primary quantitative attributes in the B.R.U.T.A.L. TTRPG system.
    Values during character creation are typically 1-8.
    """
    Might: int = 10
    Logic: int = 10
    Endurance: int = 10
    Knowledge: int = 10
    Finesse: int = 10
    Awareness: int = 10
    Reflexes: int = 10
    Intuition: int = 10
    Vitality: int = 10
    Charm: int = 10
    Fortitude: int = 10
    Willpower: int = 10

class ResourcePool(GettableModel):
    """
    Generalized tracking for current and maximum values of a resource.
    """
    current: int
    max: int

class SurvivalPools(GettableModel):
    """
    The four primary survival pools required for the Character Matrix.
    """
    hp: ResourcePool
    composure: ResourcePool
    stamina: ResourcePool
    focus: ResourcePool

class GameTags(str, Enum):
    """
    Master Tags that modify mechanical behavior in the B.R.U.T.A.L. Engine.
    """
    BRITTLE = "BRITTLE"
    VOLATILE = "VOLATILE"
    CONDUCTIVE = "CONDUCTIVE"
    UNSTABLE = "UNSTABLE"
    MOMENTUM = "MOMENTUM"
    STATIC = "STATIC"
    PRECISE = "PRECISE"
    BRUTAL = "BRUTAL"

class CharacterBuildRequest(GettableModel):
    """
    The payload used to initialize a new character chassis.
    Strictly enforces B.R.U.T.A.L. Session Zero rules.
    """
    name: str = "Jax"
    kingdom: str 
    sub_type: str = "T1" # T1-T4
    size_shift: str = "NONE" # UP, DOWN, NONE
    life_experience: Dict[str, int] = {} # 3 Body / 3 Mind
    selected_tracks: List[str] = [] # Exactly 6

    @validator('life_experience')
    def validate_exp(cls, v):
        from modules.character_engine import BODY_STATS, MIND_STATS
        body_sum = sum(v.get(s, 0) for s in BODY_STATS)
        mind_sum = sum(v.get(s, 0) for s in MIND_STATS)
        
        if body_sum != 3 or mind_sum != 3:
            raise ValueError(f"Life Experience must be exactly 3 Body points and 3 Mind points. (Got {body_sum} Body, {mind_sum} Mind)")
        return v

    @validator('selected_tracks')
    def validate_tracks(cls, v):
        if len(v) != 6:
            raise ValueError("Exactly 6 tracks must be selected for Professional Training.")
        return v

class DerivedStats(GettableModel):
    """
    Tactical sub-stats calculated from the 2:1 ratio logic.
    """
    perception: int = 0
    stealth: int = 0
    movement: int = 0
    balance: int = 0

class CharacterSheet(GettableModel):
    """
    The final validated character record.
    """
    name: str
    kingdom: str
    origin_trait: str
    stats: CoreStats
    pools: SurvivalPools
    derived: DerivedStats
    active_batteries: Dict[str, int] = {"stamina": 10, "focus": 10}
    regen_thresholds: Dict[str, int] = {"stamina": 0, "focus": 0}
    active_tracks: List[str]

class BiologicalChassis(GettableModel):
    """
    The engine-level chassis model, hydrated from the CharacterSheet.
    """
    id: str
    name: str
    species: str
    stats: CoreStats
    pools: SurvivalPools
    active_tags: List[GameTags] = []
    body_injuries: List[str] = []
    mind_trauma: List[str] = []

class MasterArc(GettableModel):
    antagonist_faction: str
    target_objective: str
    current_act: int = 1
    key_nouns: List[str] = []

class CampaignTracker(GettableModel):
    main_plot: str = "Hunting the bandits who burned your village."
    active_subplot: Optional[str] = None
    master_arc: Optional[MasterArc] = None
    quest_history: List[str] = []
    active_quest_deck: List[Dict[str, Any]] = []
    map_history_stack: List[str] = []
    tension_level: int = 0
