"""
ACTION_REGISTRY: Defines all possible stat-based and contextual actions.
Following the Ostraka Design Bible for Stat-Specific identities.
"""

ACTION_REGISTRY = {
    # --- MIGHT (Mass & Force) ---
    "Bash": {"stats": ["Might"], "targets": ["hostile", "prop"], "tags": ["solid"], "cost": {"type": "stamina", "val": 1}, "category": "Combat", "desc": "Brutal strike with mass and force."},
    "Suplex": {"stats": ["Might"], "targets": ["hostile"], "tags": ["flesh"], "cost": {"type": "stamina", "val": 2}, "category": "Combat", "desc": "Grapple and throw an enemy with raw power."},
    "Lifting": {"stats": ["Might"], "targets": ["prop"], "tags": ["heavy"], "cost": {"type": "stamina", "val": 1}, "category": "Utility", "desc": "Move massive debris or loads."},
    "Scaling": {"stats": ["Might"], "targets": ["terrain"], "tags": ["vertical"], "cost": {"type": "stamina", "val": 1}, "category": "Utility", "desc": "Upper-body sheer force climbing."},
    "Structural Load": {"stats": ["Might"], "targets": ["prop", "terrain"], "tags": ["solid"], "cost": {"type": "focus", "val": 1}, "category": "Knowledge", "desc": "Assess weight limits and mass."},
    "Looming": {"stats": ["Might"], "targets": ["npc"], "tags": [], "cost": {"type": "stamina", "val": 1}, "category": "Social", "desc": "Physical intimidation by mass."},

    # --- ENDURANCE (Stasis & Structure) ---
    "Anchor": {"stats": ["Endurance"], "targets": ["player"], "tags": [], "cost": {"type": "stamina", "val": 1}, "category": "Combat", "desc": "Bracing in place to reduce damage."},
    "March": {"stats": ["Endurance"], "targets": ["player"], "tags": [], "cost": {"type": "stamina", "val": 1}, "category": "Utility", "desc": "Ignore difficult terrain penalty through stamina."},
    "Recognize Fatigue": {"stats": ["Endurance"], "targets": ["npc", "hostile"], "tags": ["flesh"], "cost": {"type": "focus", "val": 1}, "category": "Knowledge", "desc": "Identify physical exhaustion in others."},
    "Stoic Resistance": {"stats": ["Endurance"], "targets": ["npc"], "tags": [], "cost": {"type": "stamina", "val": 1}, "category": "Social", "desc": "Outlasting rivals and enduring pressure."},

    # --- FINESSE (Precision & Bypass) ---
    "Surgical Strike": {"stats": ["Finesse"], "targets": ["hostile"], "tags": ["armored"], "cost": {"type": "stamina", "val": 1}, "category": "Combat", "desc": "Strike ignoring physical protection."},
    "Pick Lock": {"stats": ["Finesse"], "targets": ["prop"], "tags": ["locked"], "cost": {"type": "focus", "val": 1}, "category": "Utility", "desc": "Bypassing mechanisms by touch."},
    "Anatomical Precision": {"stats": ["Finesse"], "targets": ["hostile", "npc"], "tags": ["flesh"], "cost": {"type": "focus", "val": 1}, "category": "Knowledge", "desc": "Identify biological weak points."},
    "Sleight of Hand": {"stats": ["Finesse"], "targets": ["npc"], "tags": [], "cost": {"type": "stamina", "val": 1}, "category": "Social", "desc": "Planting evidence or subtle gestures."},

    # --- REFLEX (Momentum & Speed) ---
    "Whirlwind": {"stats": ["Reflexes"], "targets": ["hostile"], "tags": ["multiple"], "cost": {"type": "stamina", "val": 2}, "category": "Combat", "desc": "Striking multiple targets in a blur."},
    "Slide Under": {"stats": ["Reflexes"], "targets": ["terrain"], "tags": ["closing"], "cost": {"type": "stamina", "val": 1}, "category": "Utility", "desc": "Moving before path is closed."},
    "Kinetic Trajectory": {"stats": ["Reflexes"], "targets": ["hostile", "prop"], "tags": ["projectile"], "cost": {"type": "focus", "val": 1}, "category": "Knowledge", "desc": "Predicting movement patterns on the fly."},
    "Fast-talk": {"stats": ["Reflexes"], "targets": ["npc"], "tags": [], "cost": {"type": "focus", "val": 1}, "category": "Social", "desc": "Overwhelming others with social speed."},

    # --- VITALITY (Biology & Life) ---
    "Predatory Bite": {"stats": ["Vitality"], "targets": ["hostile"], "tags": ["flesh"], "cost": {"type": "stamina", "val": 1}, "category": "Combat", "desc": "Visceral unarmed attack."},
    "Field Patch": {"stats": ["Vitality"], "targets": ["player", "npc"], "tags": ["flesh", "wounded"], "cost": {"type": "stamina", "val": 1}, "category": "Utility", "desc": "Triage and stabilization of wounds."},
    "Blood-Sense": {"stats": ["Vitality"], "targets": ["hostile", "npc"], "tags": ["flesh"], "cost": {"type": "focus", "val": 1}, "category": "Knowledge", "desc": "Sense HP and hidden injuries intuitively."},
    "Read Tells": {"stats": ["Vitality"], "targets": ["npc"], "tags": [], "cost": {"type": "focus", "val": 1}, "category": "Social", "desc": "Reading heart rate and pupils to detect lies."},

    # --- FORTITUDE (Matter & Heat) ---
    "Shatter Shield": {"stats": ["Fortitude"], "targets": ["hostile"], "tags": ["shielded"], "cost": {"type": "stamina", "val": 1}, "category": "Combat", "desc": "Dealing matter damage to gear."},
    "Thermal Walk": {"stats": ["Fortitude"], "targets": ["terrain"], "tags": ["heat", "acid"], "cost": {"type": "stamina", "val": 1}, "category": "Utility", "desc": "Enduring environmental hazards safely."},
    "Material Flaws": {"stats": ["Fortitude"], "targets": ["prop", "terrain"], "tags": ["solid"], "cost": {"type": "focus", "val": 1}, "category": "Knowledge", "desc": "Identifying hardness and flaws in cover."},
    "Unflinching": {"stats": ["Fortitude"], "targets": ["npc"], "tags": [], "cost": {"type": "focus", "val": 1}, "category": "Social", "desc": "Staring down threats without blinking."},

    # --- KNOWLEDGE (Arcane & Data) ---
    "Counter-Spell": {"stats": ["Knowledge"], "targets": ["hostile"], "tags": ["magical"], "cost": {"type": "focus", "val": 1}, "category": "Combat", "desc": "Nullifying magical flaws."},
    "Override Mechanism": {"stats": ["Knowledge"], "targets": ["prop"], "tags": ["ancient"], "cost": {"type": "focus", "val": 1}, "category": "Utility", "desc": "Solving ancient locks by ear."},
    "Lore Recall": {"stats": ["Knowledge"], "targets": ["prop", "terrain"], "tags": ["historic"], "cost": {"type": "focus", "val": 1}, "category": "Knowledge", "desc": "Recalling hidden histories and theories."},
    "Case Law": {"stats": ["Knowledge"], "targets": ["npc"], "tags": [], "cost": {"type": "focus", "val": 1}, "category": "Social", "desc": "Quoting precedent to bypass bureaucracy."},

    # --- LOGIC (Math & Geometry) ---
    "Ricochet": {"stats": ["Logic"], "targets": ["hostile"], "tags": ["cover"], "cost": {"type": "focus", "val": 1}, "category": "Combat", "desc": "Calculated shots ignoring physical cover."},
    "Geometric Puzzle": {"stats": ["Logic"], "targets": ["prop", "terrain"], "tags": ["puzzle"], "cost": {"type": "focus", "val": 1}, "category": "Utility", "desc": "Mapping mazes and solving math-locks."},
    "Tactical Analysis": {"stats": ["Logic"], "targets": ["hostile", "terrain"], "tags": [], "cost": {"type": "focus", "val": 1}, "category": "Knowledge", "desc": "Calculating exact areas of effect."},
    "Deduction": {"stats": ["Logic"], "targets": ["npc"], "tags": [], "cost": {"type": "focus", "val": 1}, "category": "Social", "desc": "Identifying logical fallacies in NPC arguments."},

    # --- AWARENESS (Perception & Light) ---
    "Sniping": {"stats": ["Awareness"], "targets": ["hostile"], "tags": ["far"], "cost": {"type": "focus", "val": 1}, "category": "Combat", "desc": "Precision fire from extreme distance."},
    "Spot Hidden": {"stats": ["Awareness"], "targets": ["terrain", "prop"], "tags": ["hidden"], "cost": {"type": "focus", "val": 1}, "category": "Utility", "desc": "Finding doors without touching anything."},
    "Env-Observation": {"stats": ["Awareness"], "targets": ["terrain"], "tags": [], "cost": {"type": "focus", "val": 1}, "category": "Knowledge", "desc": "Assessing tactical layouts visually."},
    "Read the Room": {"stats": ["Awareness"], "targets": ["npc"], "tags": [], "cost": {"type": "focus", "val": 1}, "category": "Social", "desc": "Noticing hidden weapons or micro-expressions."},

    # --- INTUITION (Entropy & Probability) ---
    "Jinx": {"stats": ["Intuition"], "targets": ["hostile"], "tags": [], "cost": {"type": "focus", "val": 1}, "category": "Combat", "desc": "Forcing enemy rerolls through bad luck."},
    "Sixth Sense": {"stats": ["Intuition"], "targets": ["player"], "tags": [], "cost": {"type": "focus", "val": 1}, "category": "Utility", "desc": "Sensing ambushes and safer paths."},
    "Omen Reading": {"stats": ["Intuition"], "targets": ["prop", "terrain"], "tags": ["mysterious"], "cost": {"type": "focus", "val": 1}, "category": "Knowledge", "desc": "Getting reliable gut feelings on artifacts."},
    "Provoke": {"stats": ["Intuition"], "targets": ["npc", "hostile"], "tags": [], "cost": {"type": "focus", "val": 1}, "category": "Social", "desc": "Provoking emotional reactions to test intent."},

    # --- CHARM (Spirit & Emotion) ---
    "Command Strike": {"stats": ["Charm"], "targets": ["hostile"], "tags": [], "cost": {"type": "focus", "val": 1}, "category": "Combat", "desc": "Forcing enemies into tactical position."},
    "Distraction": {"stats": ["Charm"], "targets": ["npc", "hostile"], "tags": [], "cost": {"type": "focus", "val": 1}, "category": "Utility", "desc": "Creating dazzling distractions to slip past."},
    "Mass Profile": {"stats": ["Charm"], "targets": ["npc"], "tags": ["group"], "cost": {"type": "focus", "val": 1}, "category": "Knowledge", "desc": "Understanding cultural zeitgeists."},
    "Persuade": {"stats": ["Charm"], "targets": ["npc"], "tags": [], "cost": {"type": "focus", "val": 1}, "category": "Social", "desc": "Emotional resonance and leadership."},

    # --- WILLPOWER (Law & Authority) ---
    "Dominate": {"stats": ["Willpower"], "targets": ["npc", "hostile"], "tags": [], "cost": {"type": "focus", "val": 1}, "category": "Combat", "desc": "Drawing aggro across an entire zone."},
    "Bind": {"stats": ["Willpower"], "targets": ["npc", "hostile"], "tags": ["magical"], "cost": {"type": "focus", "val": 2}, "category": "Utility", "desc": "Binding enemies to physical contracts."},
    "Celestial Study": {"stats": ["Willpower"], "targets": ["prop", "terrain"], "tags": ["legal"], "cost": {"type": "focus", "val": 1}, "category": "Knowledge", "desc": "Identifying loopholes in magical law."},
    "Command Obedience": {"stats": ["Willpower"], "targets": ["npc"], "tags": [], "cost": {"type": "focus", "val": 1}, "category": "Social", "desc": "Authoritarian intimidation / absolute command."},
    
    "Disengage": {
        "stats": ["Vitality", "Finesse"],
        "targets": ["player"],
        "tags": [],
        "cost": {"type": "stamina", "val": 1},
        "category": "Maneuver",
        "desc": "Prepare to safely move out of hostile threat zones."
    },
    
    # Generic Actions (Not stat gated)
    "Examine": {"stats": [], "targets": ["prop", "npc", "hostile", "player", "terrain"], "tags": [], "cost": {"type": "focus", "val": 0}, "category": "General", "desc": "A basic look at the target."},
    "Loot": {"stats": [], "targets": ["prop", "npc", "hostile"], "tags": ["dead", "container"], "cost": {"type": "stamina", "val": 0}, "category": "General", "desc": "Take items from target."},
    "Open": {"stats": [], "targets": ["prop"], "tags": ["container"], "cost": {"type": "stamina", "val": 0}, "category": "General", "desc": "Interact with a container."}
}

def get_valid_actions(player, target_entity):
    """Returns a list of action names valid for the given target."""
    valid = []
    if not target_entity:
        return ["Move Here", "Examine Area", "Cancel"]
        
    target_type = target_entity.get("type", "prop")
    target_tags = target_entity.get("tags", [])
    
    for action_name, data in ACTION_REGISTRY.items():
        # Check type match
        type_match = target_type in data["targets"]
        # Check tag match (if specified)
        tag_match = True
        if data["tags"]:
            tag_match = any(tag in target_tags for tag in data["tags"])
            
        if type_match and tag_match:
            valid.append(action_name)
            
    return valid

def get_best_stat_for_action(player, action_name):
    """Determines which stat the player is best at for a specific action."""
    data = ACTION_REGISTRY.get(action_name)
    if not data or not data["stats"]: return None
    
    stats = player.get("stats", {})
    best_stat = data["stats"][0]
    best_val = -float('inf')
    
    for stat in data["stats"]:
        # Handle "Reflexes" (Design Bible) vs "Reflex" (Action List)
        lookup_stat = "Reflexes" if stat == "Reflex" else stat
        val = stats.get(lookup_stat, 0)
        if val > best_val:
            best_val = val
            best_stat = stat
            
    return best_stat
