import json
import random
import requests

# CONFIGURATION
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1:8b-instruct-q3_K_L"

def generate_story_glue(seed_event, state):
    """
    Narrative Weaver AI: Bridges a random map event into the campaign context.
    Now generates Truths and Clues for Deductive Puzzles and Mysteries.
    """
    tracker = state.get("local_map_state", {}).get("meta", {}).get("campaign_tracker", {})
    past_history = tracker.get("quest_history", [])
    active_subplot = tracker.get("active_subplot", "None")
    main_plot = tracker.get("main_plot", "Hunting the bandits who burned your village.")

    prompt = f"""
    You are the Narrative Weaver for a gritty dark fantasy RPG set in Ostraka.
    CURRENT EVENT SEED: {seed_event}
    PAST HISTORY: {past_history}
    CURRENT SUB-PLOT: {active_subplot}
    MACRO CAMPAIGN: {main_plot}
    
    Write a 2-to-3 sentence story hook that creatively connects the CURRENT EVENT SEED to the player's PAST HISTORY or SUB-PLOT.
    
    If the dominant_theme is "mystery" or "puzzle", you MUST provide a "truth_table" and "discoverable_clues".
    
    Respond ONLY in valid JSON format with exactly these keys:
    - "story_hook": (string) The gritty narrative description.
    - "involved_factions": (array of strings)
    - "dominant_theme": (string) "combat", "stealth", "puzzle", or "mystery".
    - "truth_table": (object) Internal facts that solve the encounter (e.g. {{"solution": "The key is in the well", "culprit": "Jax"}}).
    - "discoverable_clues": (array of objects) Fragments of information. 
        Each clue: {{"text": "...", "source_tag": "tag_name", "skill_hint": "stat_name"}}
    """

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=20)
        if response.status_code == 200:
            data = response.json()
            raw_content = data.get("response", "{}")
            weaver_data = json.loads(raw_content)
            return weaver_data
    except Exception as e:
        print(f"[Weaver Error] AI failed: {e}")

    # FALLBACK DATA
    return {
        "story_hook": f"The signs are clear: {seed_event}. It feels like an echo of your past.",
        "involved_factions": ["wild_beasts"],
        "dominant_theme": "mystery",
        "truth_table": {"solution": "The guard dropped it at the tavern"},
        "discoverable_clues": [
            {"text": "The guard was seen drinking heavily at the Crow's Nest.", "source_tag": "bartender", "skill_hint": "Awareness"},
            {"text": "A metallic glint was noticed near the hearth.", "source_tag": "tavern_floor", "skill_hint": "Logic"}
        ]
    }

def build_mechanical_deck(weaver_data, region_threat_level=1):
    """
    Mechanical Deck Builder: Translates AI narrative themes into a sequence of challenges.
    """
    deck_size = random.randint(3, 5)
    theme = weaver_data.get("dominant_theme", "combat")
    factions = weaver_data.get("involved_factions", ["wild_beasts"])
    
    deck = []
    
    for i in range(deck_size):
        if theme == "combat":
            weights = {"combat": 70, "hazard": 15, "social": 15}
        elif theme == "stealth":
            weights = {"combat": 20, "hazard": 40, "mystery": 40}
        elif theme == "puzzle":
            weights = {"puzzle": 70, "hazard": 15, "social": 15}
        elif theme == "mystery":
            weights = {"mystery": 70, "hazard": 15, "social": 15}
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
        
    deck[-1]["type"] = "climax"
    deck[-1]["threat"] += 1
    
    return deck

def build_macro_deck(weaver_data):
    """
    Macro Deck Builder: Generates a sequence of Overworld Macro Steps.
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
    
    if theme in ["puzzle", "mystery"] or random.random() > 0.7:
        deck.insert(1, {
            "type": "scout", 
            "target_region": target_region, 
            "objective": "Gather intelligence or scout the perimeter before entering."
        })
        
    return deck

def build_interior_deck(building_type, is_quest=False, quest_data=None):
    """Builds a sequence of rooms for an interior location."""
    
    if not is_quest:
        return [{"room_type": f"{building_type}_main", "event": "social", "threat": 0}]
    
    deck_size = random.randint(3, 5)
    deck = []
    
    # Card 1: The Entrance
    deck.append({
        "room_type": "entrance", 
        "event": "trap_or_guard", 
        "threat": 1
    })
    
    # Cards 2-4: The Gauntlet
    for _ in range(deck_size - 2):
        # Mix of combat and puzzle rooms for ruins/labs
        event_type = random.choice(["combat", "puzzle", "hazard"])
        deck.append({
            "room_type": "chamber", 
            "event": event_type, 
            "threat": 2
        })
        
    # Final Card: The Climax
    deck.append({
        "room_type": "climax_chamber", 
        "event": "boss_combat" if random.random() > 0.3 else "grand_puzzle", 
        "threat": 3
    })
    
    return deck
