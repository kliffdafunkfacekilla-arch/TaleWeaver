import json
import random
import requests

# CONFIGURATION
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1:8b-instruct-q3_K_L"

def generate_story_glue(seed_event, state):
    """
    Narrative Weaver AI: Bridges a random map event into the campaign context.
    """
    tracker = state.get("meta", {}).get("campaign_tracker", {})
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
        response = requests.post(OLLAMA_URL, json=payload, timeout=15)
        if response.status_code == 200:
            data = response.json()
            # Most Ollama responses are in "response" key
            raw_content = data.get("response", "{}")
            weaver_data = json.loads(raw_content)
            return weaver_data
    except Exception as e:
        print(f"[Weaver Error] AI failed: {e}")

    # FALLBACK DATA
    return {
        "story_hook": f"The signs are clear: {seed_event}. It feels like an echo of your past.",
        "involved_factions": ["wild_beasts"],
        "dominant_theme": "combat"
    }

def build_mechanical_deck(weaver_data, region_threat_level=1):
    """
    Mechanical Deck Builder: Translates AI narrative themes into a sequence of challenges.
    """
    deck_size = random.randint(3, 5)
    theme = weaver_data.get("dominant_theme", "combat")
    factions = weaver_data.get("involved_factions", ["wild_beasts"])
    
    deck = []
    
    # Weighting logic
    # Combat theme weighs heavily toward combat cards
    # Stealth theme weighs toward hazards and social
    # Puzzle theme weighs toward hazards
    
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
        
    # Force the final card to be a climax
    deck[-1]["type"] = "climax"
    deck[-1]["threat"] += 1 # Bosses are harder
    
    return deck
