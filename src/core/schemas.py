from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class CoreStats(BaseModel):
    """
    Primary quantitative attributes in the B.R.U.T.A.L. TTRPG system.
    Default value for all stats is 10 as per ruleset version 2.3.
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

class ResourcePool(BaseModel):
    """
    Generalized tracking for current and maximum values of a resource.
    """
    current: int
    max: int

class SurvivalPools(BaseModel):
    """
    The four primary survival pools required for the Character Matrix.
    - HP: Physical structural integrity.
    - Composure: Mental and psychic stability.
    - Stamina: Body-driven action energy.
    - Focus: Mind-driven action energy.
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

class BiologicalChassis(BaseModel):
    """
    The absolute source of truth for an entity's physical and mental state.
    Serves as the foundational 'Character Sheet' for the engine.
    """
    id: str
    name: str
    species: str
    stats: CoreStats
    pools: SurvivalPools
    active_tags: List[GameTags] = []
    body_injuries: List[str] = []
    mind_trauma: List[str] = []
