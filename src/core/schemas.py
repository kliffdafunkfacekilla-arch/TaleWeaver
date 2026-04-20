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
    Might: int = 0
    Logic: int = 0
    Endurance: int = 0
    Knowledge: int = 0
    Finesse: int = 0
    Awareness: int = 0
    Reflexes: int = 0
    Intuition: int = 0
    Vitality: int = 0
    Charm: int = 0
    Fortitude: int = 0
    Willpower: int = 0

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
    """
    name: str = "New Character"
    kingdom: str 
    sub_type: str 
    size_shift: str = "NONE" 
    life_experience: Dict[str, int] = {} 
    selected_tracks: List[str] = [] 

    @validator('life_experience')
    def validate_exp(cls, v):
        if sum(v.values()) != 6:
            raise ValueError("Life Experience must distribute exactly 6 points.")
        return v

    @validator('selected_tracks')
    def validate_tracks(cls, v):
        if len(v) != 6:
            raise ValueError("Exactly 6 tracks must be selected.")
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
