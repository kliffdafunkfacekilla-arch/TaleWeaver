"""
ACTION_REGISTRY: Defines all possible stat-based and contextual actions.
Following the Ostraka Design Bible for Stat-Specific identities.
"""

ACTION_REGISTRY = {
    # --- MIGHT (Mass & Force) ---
    "Bash": {"stats": ["Might"], "targets": ["hostile", "prop"], "tags": ["solid"], "cost": {"type": "stamina", "val": 1}, "category": "Combat", "desc": "Brutal strike with mass and force."},
    "Suplex": {"stats": ["Might"], "targets": ["hostile"], "tags": ["flesh"], "cost": {"type": "stamina", "val": 2}, "category": "Combat", "desc": "Grapple and throw an enemy with raw power."},
    "Looming": {"stats": ["Might"], "targets": ["npc"], "tags": [], "cost": {"type": "stamina", "val": 1}, "category": "Social", "desc": "Physical intimidation by mass."},
    "Intimidate": {"stats": ["Might"], "targets": ["npc"], "tags": [], "cost": {"type": "stamina", "val": 1}, "category": "Social Combat", "desc": "Using physical presence to break mental resolve.", "offense": True},

    # --- ENDURANCE (Stasis & Structure) ---
    "Anchor": {"stats": ["Endurance"], "targets": ["player"], "tags": [], "cost": {"type": "stamina", "val": 1}, "category": "Combat", "desc": "Bracing in place to reduce damage."},
    "Stoic Resistance": {"stats": ["Endurance"], "targets": ["npc"], "tags": [], "cost": {"type": "stamina", "val": 1}, "category": "Social", "desc": "Outlasting rivals and enduring pressure."},

    # --- FINESSE (Precision & Bypass) ---
    "Surgical Strike": {"stats": ["Finesse"], "targets": ["hostile"], "tags": ["armored"], "cost": {"type": "stamina", "val": 1}, "category": "Combat", "desc": "Strike ignoring physical protection."},
    "Sleight of Hand": {"stats": ["Finesse"], "targets": ["npc"], "tags": [], "cost": {"type": "stamina", "val": 1}, "category": "Social", "desc": "Planting evidence or subtle gestures."},

    # --- REFLEX (Momentum & Speed) ---
    "Whirlwind": {"stats": ["Reflexes"], "targets": ["hostile"], "tags": ["multiple"], "cost": {"type": "stamina", "val": 2}, "category": "Combat", "desc": "Striking multiple targets in a blur."},
    "Fast-talk": {"stats": ["Reflexes"], "targets": ["npc"], "tags": [], "cost": {"type": "focus", "val": 1}, "category": "Social", "desc": "Overwhelming others with social speed."},

    # --- VITALITY (Biology & Life) ---
    "Predatory Bite": {"stats": ["Vitality"], "targets": ["hostile"], "tags": ["flesh"], "cost": {"type": "stamina", "val": 1}, "category": "Combat", "desc": "Visceral unarmed attack."},
    "Read Tells": {"stats": ["Vitality"], "targets": ["npc"], "tags": [], "cost": {"type": "focus", "val": 1}, "category": "Social", "desc": "Reading heart rate and pupils to detect lies."},

    # --- FORTITUDE (Matter & Heat) ---
    "Shatter Shield": {"stats": ["Fortitude"], "targets": ["hostile"], "tags": ["shielded"], "cost": {"type": "stamina", "val": 1}, "category": "Combat", "desc": "Dealing matter damage to gear."},
    "Unflinching": {"stats": ["Fortitude"], "targets": ["npc"], "tags": [], "cost": {"type": "focus", "val": 1}, "category": "Social", "desc": "Staring down threats without blinking."},

    # --- KNOWLEDGE (Arcane & Data) ---
    "Counter-Spell": {"stats": ["Knowledge"], "targets": ["hostile"], "tags": ["magical"], "cost": {"type": "focus", "val": 1}, "category": "Combat", "desc": "Nullifying magical flaws."},
    "Case Law": {"stats": ["Knowledge"], "targets": ["npc"], "tags": [], "cost": {"type": "focus", "val": 1}, "category": "Social", "desc": "Quoting precedent to bypass bureaucracy."},
    "Logical Defense": {"stats": ["Knowledge"], "targets": ["player"], "tags": [], "cost": {"type": "focus", "val": 1}, "category": "Social Combat", "desc": "Using deep data to shield against logical fallacies.", "defense": True},

    # --- LOGIC (Math & Geometry) ---
    "Ricochet": {"stats": ["Logic"], "targets": ["hostile"], "tags": ["cover"], "cost": {"type": "focus", "val": 1}, "category": "Combat", "desc": "Calculated shots ignoring physical cover."},
    "Deduction Check": {"stats": ["Logic"], "targets": ["npc", "prop"], "tags": [], "cost": {"type": "focus", "val": 1}, "category": "Social", "desc": "Using evidence to force a breakthrough."},
    "Logic Strike": {"stats": ["Logic"], "targets": ["npc"], "tags": [], "cost": {"type": "focus", "val": 1}, "category": "Social Combat", "desc": "Dismantling an argument with cold facts.", "offense": True},

    # --- AWARENESS (Perception & Light) ---
    "Sniping": {"stats": ["Awareness"], "targets": ["hostile"], "tags": ["far"], "cost": {"type": "focus", "val": 1}, "category": "Combat", "desc": "Precision fire from extreme distance."},
    "Read the Room": {"stats": ["Awareness"], "targets": ["npc"], "tags": [], "cost": {"type": "focus", "val": 1}, "category": "Social", "desc": "Noticing hidden weapons or micro-expressions."},

    # --- INTUITION (Entropy & Probability) ---
    "Jinx": {"stats": ["Intuition"], "targets": ["hostile"], "tags": [], "cost": {"type": "focus", "val": 1}, "category": "Combat", "desc": "Forcing enemy rerolls through bad luck."},
    "Provoke": {"stats": ["Intuition"], "targets": ["npc", "hostile"], "tags": [], "cost": {"type": "focus", "val": 1}, "category": "Social", "desc": "Provoking emotional reactions to test intent."},
    "Insight Attack": {"stats": ["Intuition"], "targets": ["npc"], "tags": [], "cost": {"type": "focus", "val": 1}, "category": "Social Combat", "desc": "Correcting a target's lie with raw intuition.", "offense": True},

    # --- CHARM (Spirit & Emotion) ---
    "Command Strike": {"stats": ["Charm"], "targets": ["hostile"], "tags": [], "cost": {"type": "focus", "val": 1}, "category": "Combat", "desc": "Forcing enemies into tactical position."},
    "Persuade": {"stats": ["Charm", "Logic"], "targets": ["npc"], "tags": [], "cost": {"type": "focus", "val": 1}, "category": "Social Combat", "desc": "A mix of emotional appeal and rational proof.", "offense": True},
    "Beguile": {"stats": ["Charm"], "targets": ["npc"], "tags": [], "cost": {"type": "focus", "val": 1}, "category": "Social Combat", "desc": "Pure emotional resonance and charisma.", "offense": True},

    # --- WILLPOWER (Law & Authority) ---
    "Dominate": {"stats": ["Willpower"], "targets": ["npc", "hostile"], "tags": [], "cost": {"type": "focus", "val": 1}, "category": "Combat", "desc": "Drawing aggro across an entire zone."},
    "Command Obedience": {"stats": ["Willpower"], "targets": ["npc"], "tags": [], "cost": {"type": "focus", "val": 1}, "category": "Social", "desc": "Authoritarian intimidation / absolute command."},
    "Mental Fortitude": {"stats": ["Willpower"], "targets": ["player"], "tags": [], "cost": {"type": "focus", "val": 1}, "category": "Social Combat", "desc": "Refusing to yield to social pressure.", "defense": True},
    
    "Examine": {"stats": [], "targets": ["prop", "npc", "hostile", "player", "terrain"], "tags": [], "cost": {"type": "focus", "val": 0}, "category": "General", "desc": "A basic look at the target."},
    "Loot": {"stats": [], "targets": ["prop", "npc", "hostile"], "tags": ["dead", "container"], "cost": {"type": "stamina", "val": 0}, "category": "General", "desc": "Take items from target."},
    "Open": {"stats": [], "targets": ["prop"], "tags": ["container"], "cost": {"type": "stamina", "val": 0}, "category": "General", "desc": "Interact with a container."}
}

SOCIAL_OFFENSE_TRACKS = ["Charm", "Logic", "Intuition", "Might"]
SOCIAL_DEFENSE_TRACKS = ["Willpower", "Knowledge", "Intuition"]

import json
import urllib.request
import time
import re

class IntentResolver:
    def __init__(self, model="llama3.1:8b-instruct-q3_K_L", url="http://localhost:11434/api/generate"):
        self.model = model
        self.url = url

    def parse_player_input(self, player_text, current_scene_context):
        """Translates natural language to strict JSON actions via Ollama with robust regex extraction."""
        
        system_prompt = (
            "You are a strict technical parser for a game engine. "
            "Translate the player's text into a single JSON object. "
            "Valid actions are: MOVE, ATTACK, EXAMINE, LOOT, TALK, USE, DEDUCE, QUESTION, SOCIAL_ATTACK. "
            "SOCIAL_ATTACK is for using social skills in a mental combat context. "
            "If the action is 'DEDUCE', the 'parameters' must be the player's full reasoning string. "
            "Schema: {\"action\": \"...\", \"target\": \"...\", \"parameters\": \"...\"}. "
            "Return ONLY the JSON. No conversation, no markdown."
        )

        prompt = f"System: {system_prompt}\nContext: {current_scene_context}\nPlayer: {player_text}"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_ctx": 1024, "temperature": 0.0}
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(self.url, data=data, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode("utf-8"))
                ai_response = result.get("response", "").strip()
                
                json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                if json_match: ai_response = json_match.group(0)
                
                return json.loads(ai_response)
        except Exception as e:
            print(f"[Parser Error] Failed to resolve intent: {e}")
            return {"action": "UNKNOWN", "target": "None", "parameters": str(e)}

def get_valid_actions(player, target_entity, learned_skills=None):
    valid = []
    if not target_entity: return ["Move Here", "Examine Area", "Cancel"]
        
    target_type = target_entity.get("type", "prop")
    target_tags = target_entity.get("tags", [])
    
    for action_name, data in ACTION_REGISTRY.items():
        type_match = target_type in data.get("targets", [])
        tag_match = True
        if data.get("tags"):
            tag_match = any(tag in target_tags for tag in data["tags"])
        if type_match and tag_match:
            valid.append(action_name)

    return valid

def get_best_stat_for_action(player, action_name):
    data = ACTION_REGISTRY.get(action_name)
    stats = player.get("stats", {})
    if not data or not data.get("stats"): return None
    
    best_stat = data["stats"][0]
    best_val = -float('inf')
    for stat in data["stats"]:
        lookup_stat = "Reflexes" if stat == "Reflex" else stat
        val = stats.get(lookup_stat, 0)
        if val > best_val:
            best_val = val
            best_stat = stat
    return best_stat
