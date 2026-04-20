import json
import os
from typing import Dict, List, Any
from core.schemas import CharacterBuildRequest, CharacterSheet, CoreStats, SurvivalPools, ResourcePool, DerivedStats

DATA_PATH = os.path.join(os.getcwd(), 'data')
KINGDOM_MATRICES_FILE = os.path.join(DATA_PATH, 'kingdom_matrices.json')
TRACK_MAPPING_FILE = os.path.join(DATA_PATH, 'track_mapping.json')

BODY_STATS = ["Might", "Endurance", "Finesse", "Reflexes", "Vitality", "Fortitude"]
MIND_STATS = ["Knowledge", "Logic", "Awareness", "Intuition", "Charm", "Willpower"]

def load_json_data(filepath: str) -> Dict:
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

class CharacterEngine:
    """
    The B.R.U.T.A.L. Character Synthesis Engine.
    Handles the procedural construction of the biological chassis.
    """
    def __init__(self):
        self.matrices = load_json_data(KINGDOM_MATRICES_FILE)
        self.track_map = load_json_data(TRACK_MAPPING_FILE)

    def reallocate_overflow(self, stats_dict: Dict[str, int]) -> Dict[str, int]:
        """
        Enforces the 'Biological Ceiling' (Hard Cap: 8).
        Overflow points are bled into the lowest stat of the same type.
        """
        def resolve_pool(pool_names: List[str]):
            overflow = 0
            for name in pool_names:
                if stats_dict[name] > 8:
                    overflow += (stats_dict[name] - 8)
                    stats_dict[name] = 8
            
            while overflow > 0:
                # Find the lowest stat in the pool that is still < 8
                eligible = [n for n in pool_names if stats_dict[n] < 8]
                if not eligible:
                    # If everything is 8, the overflow is discarded (hard limit reached)
                    break
                
                # Pick the lowest, then second lowest if ties, etc.
                lowest = min(eligible, key=lambda n: stats_dict[n])
                stats_dict[lowest] += 1
                overflow -= 1

        resolve_pool(BODY_STATS)
        resolve_pool(MIND_STATS)
        return stats_dict

    def generate_character(self, request: CharacterBuildRequest) -> CharacterSheet:
        """
        Transforms a build request into a final CharacterSheet using the multi-stage resolution engine.
        """
        # Stage 1: Kingdom Matrix Baseline
        kingdom_matrix = self.matrices.get(request.kingdom, self.matrices["Mammals"])
        base_values = kingdom_matrix.get(request.sub_type, kingdom_matrix["T1"])
        
        current_stats = {k: v for k, v in base_values.items()}

        # Stage 2: Life Experience (3 Body / 3 Mind split enforced by schema/UI)
        for stat_name, points in request.life_experience.items():
            if stat_name in current_stats:
                current_stats[stat_name] += points

        # Stage 3: Size Shift
        if request.size_shift == "UP":
            if current_stats["Might"] < current_stats["Endurance"]: current_stats["Might"] += 1
            else: current_stats["Endurance"] += 1
        elif request.size_shift == "DOWN":
            if current_stats["Finesse"] < current_stats["Reflexes"]: current_stats["Finesse"] += 1
            else: current_stats["Reflexes"] += 1

        # Stage 4: Professional Training (+2 each for 6 tracks)
        for track in request.selected_tracks:
            gov_stat = self.track_map.get(track)
            if gov_stat and gov_stat in current_stats:
                current_stats[gov_stat] += 2

        # Stage 5: Ceiling Enforcement (Hard Cap 8)
        current_stats = self.reallocate_overflow(current_stats)

        # Stage 6: Derived Statistics (Ref: character creatiikon.md)
        hp_max = current_stats["Endurance"] + current_stats["Fortitude"] + current_stats["Vitality"]
        comp_max = current_stats["Willpower"] + current_stats["Logic"] + current_stats["Charm"]
        stam_cap = current_stats["Might"] + current_stats["Reflexes"] + current_stats["Finesse"]
        focus_cap = current_stats["Knowledge"] + current_stats["Awareness"] + current_stats["Intuition"]

        # Tactical Sub-Stats (2:1 Ratio logic)
        perc = current_stats["Awareness"] + current_stats["Logic"] + current_stats["Vitality"]
        stlth = current_stats["Knowledge"] + current_stats["Charm"] + current_stats["Finesse"]
        mvmt = current_stats["Reflexes"] + current_stats["Might"] + current_stats["Intuition"]
        bal = current_stats["Endurance"] + current_stats["Fortitude"] + current_stats["Willpower"]

        # Build Final Sheet
        return CharacterSheet(
            name=request.name,
            kingdom=request.kingdom,
            origin_trait="Fictional Origin Placeholder", 
            stats=CoreStats(**current_stats),
            pools=SurvivalPools(
                hp=ResourcePool(current=hp_max, max=hp_max),
                composure=ResourcePool(current=comp_max, max=comp_max),
                stamina=ResourcePool(current=10, max=10),
                focus=ResourcePool(current=10, max=10)
            ),
            derived=DerivedStats(
                perception=perc, stealth=stlth, movement=mvmt, balance=bal
            ),
            regen_thresholds={"stamina": stam_cap, "focus": focus_cap},
            active_tracks=request.selected_tracks
        )
