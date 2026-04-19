import aiohttp
import asyncio
import json
import random
import os
from typing import Dict, Any, Optional

# LOCAL AI CONFIGURATION
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1:8b-instruct-q3_K_L"

async def generate_flavor_text() -> str:
    """
    The AI Narrator: Generates gritty, immersive flavor text based on the 
    last mechanical action recorded in the game state.
    
    Returns:
        str: A short (1-2 sentence) narrative description of the game events.
    """
    # Defensive pathing to import engine without circular dependencies
    import engine 
    state = engine.load_state()
    
    latest_action = state.get("latest_action")
    ai_directive = state.get("ai_directive", "NARRATOR MODE: Describe the current scene in a dark, gritty tone. 1 sentence.")
    
    # If no specific action occurred, provide atmospheric flavor
    if not latest_action:
        prompt = f"OSTRAKA NARRATOR: {ai_directive}"
    else:
        actor = latest_action.get("actor", "Someone")
        action = latest_action.get("action", "does something")
        target = latest_action.get("target", "something")
        result = latest_action.get("mechanical_result", "it happens")
        
        prompt = f"""
        You are the Voice of Ostraka, a gritty dark fantasy RPG narrator.
        MECHANICAL EVENT: {actor} used {action} on {target}. RESULT: {result}.
        DIRECTIVE: {ai_directive}
        
        Rules:
        1. Keep it to 2 sentences max. 
        2. Use visceral, steampunk, and mud-and-blood imagery.
        3. Do not mention game mechanics like 'HP', 'dice', or 'checks'.
        4. Respond ONLY with the story text.
        """

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(OLLAMA_URL, json=payload, timeout=12) as response:
                if response.status == 200:
                    data = await response.json()
                    narration = data.get("response", "").strip()
                    # Clean up Ollama conversational preamble if any
                    narration = narration.split(":")[-1].strip()
                    return narration
    except Exception as e:
        print(f"[Narrator Error] AI failed: {e}")

    # FALLBACK ATMOSPHERIC TEXT
    fallbacks = [
        "The air here smells of ozone and recycled grease.",
        "Steel Clatters against stone, echoing through the shadowed alleyways.",
        "A distant steam-vent hiss masks the sound of approaching footsteps.",
        "The Shatterlands offer no mercy to the unprepared."
    ]
    return random.choice(fallbacks)