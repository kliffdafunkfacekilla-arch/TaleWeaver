import json
import random
import aiohttp
import asyncio
from typing import Dict, Any, List, Optional

# CONFIGURATION
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1:8b-instruct-q3_K_L"

async def generate_story_glue(seed_event: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Narrative Weaver AI: Bridges a random map event into the campaign context.
    Uses an asynchronous POST request to the local Ollama server.
    
    Args:
        seed_event (str): The short description of the map event (e.g., 'A trail of blood').
        state (Dict[str, Any]): The full game state for context extraction.
        
    Returns:
        Dict[str, Any]: A JSON object with 'story_hook', 'involved_factions', and 'dominant_theme'.
    """
    tracker = state.get("meta", {}).get("campaign_tracker", {})
    master_arc = tracker.get("master_arc")
    past_history = tracker.get("quest_history", [])
    active_subplot = tracker.get("active_subplot", "None")
    main_plot = tracker.get("main_plot", "Hunting the bandits who burned your village.")

    arc_context = ""
    if master_arc:
        arc_context = f"""
        HIDDEN MASTER ARC (The 'Iceberg'):
        - Antagonist Faction: {master_arc.get('antagonist_faction')}
        - Secret Objective: {master_arc.get('target_objective')}
        - Key Narrative Nouns: {', '.join(master_arc.get('key_nouns', []))}
        - Current Intensity (Act): {master_arc.get('current_act', 1)}/5
        """

    prompt = f"""
    You are the Narrative Weaver for a gritty dark fantasy RPG set in Ostraka.
    CURRENT EVENT SEED: {seed_event}
    PAST HISTORY: {past_history}
    CURRENT SUB-PLOT: {active_subplot}
    MACRO CAMPAIGN: {main_plot}
    {arc_context}
    
    Write a 2-to-3 sentence story hook. 
    REQUIRMENT: Creatively connect the CURRENT EVENT SEED to the player's history or sub-plot.
    ICEBERG RULE: If the HIDDEN MASTER ARC is provided, subtly plant a "seed" or reference to its Key Nouns or Secret Objective within the description. DO NOT reveal the whole plot, just a shadow of it.

    Respond ONLY in valid JSON format with exactly three keys:
    - "story_hook": (string) The gritty narrative description.
    - "involved_factions": (array of strings) Guess 1 or 2 factions from: "sump_kin", "iron_caldera", "wild_beasts", "river_folk", "imperial_remnant".
    - "dominant_theme": (string) Choose exactly one: "combat", "stealth", or "puzzle".
    """

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(OLLAMA_URL, json=payload, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    raw_content = data.get("response", "{}")
                    weaver_data = json.loads(raw_content)
                    return weaver_data
    except Exception as e:
        print(f"[Weaver Error] AI failed: {e}")

    # FALLBACK DATA in case of AI failure or timeout
    return {
        "story_hook": f"The signs are clear: {seed_event}. It feels like an echo of your past.",
        "involved_factions": ["wild_beasts"],
        "dominant_theme": "combat"
    }

def build_mechanical_deck(weaver_data: Dict[str, Any], region_threat_level: int = 1) -> List[Dict[str, Any]]:
    """
    Mechanical Deck Builder: Translates AI narrative themes into a sequence of challenges.
    
    Args:
        weaver_data (Dict[str, Any]): The story data from generate_story_glue.
        region_threat_level (int): Difficulty modifier for the region.
        
    Returns:
        List[Dict[str, Any]]: A list of 'cards' representing tactical encounters.
    """
    deck_size = random.randint(3, 5)
    theme = weaver_data.get("dominant_theme", "combat")
    factions = weaver_data.get("involved_factions", ["wild_beasts"])
    
    deck = []
    
    for i in range(deck_size):
        if theme == "combat":
            weights = {"combat": 70, "hazard": 15, "social": 15}
        elif theme == "stealth":
            weights = {"combat": 20, "hazard": 40, "social": 40}
        elif theme == "puzzle":
            weights = {"combat": 15, "hazard": 70, "social": 15}
        else:
            weights = {"combat": 33, "hazard": 33, "social": 34}
            
        choices = list(weights.keys())
        probs = [weights[c] / 100 for c in choices]
        
        chosen_type = random.choices(choices, weights=probs)[0]
        
        card = {
            "type": chosen_type,
            "faction": random.choice(factions),
            "threat": region_threat_level,
            "resolved": False
        }
        deck.append(card)
        
    # Ensure a climactic finish
    deck[-1]["type"] = "climax"
    deck[-1]["threat"] += 1 
    
    return deck

def build_macro_deck(weaver_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Macro Deck Builder: Generates a sequence of Overworld Macro Steps.
    
    Args:
        weaver_data (Dict[str, Any]): The story data from generate_story_glue.
        
    Returns:
        List[Dict[str, Any]]: High-level objectives for the player's quest journal.
    """
    theme = weaver_data.get("dominant_theme", "combat")
    factions = weaver_data.get("involved_factions", ["wild_beasts"])
    
    regions = ["The Sump-Mire", "Iron Caldera", "Heartland Alliance", "River Folk Outpost"]
    target_region = random.choice(regions)
    building_type = "bandit_camp" if "sump_kin" in factions else "ruined_laboratory"
    
    deck = [
        {
            "type": "travel", 
            "target_region": target_region, 
            "objective": f"Travel to {target_region} to follow the lead: {weaver_data['story_hook'][:50]}..."
        },
        {
            "type": "explore_interior", 
            "building_type": building_type, 
            "objective": f"Infiltrate the {building_type.replace('_', ' ')} and complete the mission."
        }
    ]
    
    if theme == "puzzle" or random.random() > 0.7:
        deck.insert(1, {
            "type": "scout", 
            "target_region": target_region, 
            "objective": "Gather intelligence or scout the perimeter before entering."
        })
        
    return deck

def build_interior_deck(building_type: str, is_quest: bool = False, quest_data: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Builds a sequence of rooms for an interior location (Dungeon).
    
    Args:
        building_type (str): The theme of the building (e.g., 'bandit_camp').
        is_quest (bool): If True, complexity increases to match a quest arc.
        
    Returns:
        List[Dict[str, Any]]: A sequence of room definitions.
    """
    if not is_quest:
        return [{"room_type": f"{building_type}_main", "event": "social", "threat": 0}]
    
    deck_size = random.randint(3, 5) 
    deck = []
    
    deck.append({
        "room_type": "entrance", 
        "event": "trap_or_guard", 
        "threat": 1
    })
    
    for _ in range(deck_size - 2):
        deck.append({
            "room_type": "corridor", 
            "event": "combat", 
            "threat": 2
        })
        
    deck.append({
        "room_type": "boss_chamber", 
        "event": "boss_combat", 
        "threat": 3
    })
    
    return deck
