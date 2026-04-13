import json
import random

def load_json(filepath):
    try:
        with open(filepath, "r", encoding="utf-8-sig") as f: return json.load(f)
    except: return {}

def generate_local_map(global_pos=[0,0], entry_pos=[25, 25], player_data=None, quest_deck=None):
    world_map = load_json("data/world_map.json")
    world_data = load_json("data/world_regions.json")
    story_data = load_json("data/story_quests.json")
    templates = load_json("data/entity_templates.json")
    
    coord_string = f"{global_pos[0]},{global_pos[1]}"
    region_id = world_map.get("map_chunks", {}).get(coord_string, world_map.get("default_region", "pine_forest"))
    region = world_data.get("regions", {}).get(region_id)
    if not region: return False

    current_weather = random.choice(region.get("weather_pool", ["clear"]))
    map_tags = region.get("biome_tags", []) + [current_weather]

    map_state = {
        "meta": {"global_pos": global_pos, "region_id": region_id, "map_name": region["name"], "grid_size": [50, 50], "map_tags": map_tags},
        "environment": f"You are in {region['name']}. The weather is {current_weather}.", "entities": [], "latest_action": {}, "ai_directive": ""
    }

    if player_data:
        player_data["pos"] = entry_pos
        map_state["entities"].append(player_data)
    else:
        # THE NEW OSTRAKA CHASSIS (Stat-Logic 2.0)
        new_player = {
            "id": "char_01", "name": "Captain Jax", "type": "player", "pos": entry_pos,
            "species": "Human",
            "tracks": {"offense": "Might", "defense": "Reflexes"},
            "hp": 20, "max_hp": 20, "composure": 15, "max_composure": 15,
            "resources": {"stamina": 10, "max_stamina": 10, "focus": 10, "max_focus": 10},
            "stats": {
                "Might": 4, "Endurance": 5, "Reflexes": 3, "Finesse": 2, "Vitality": 4, "Fortitude": 5,
                "Knowledge": 3, "Logic": 2, "Awareness": 6, "Intuition": 5, "Charm": 2, "Willpower": 4
            },
            "equipment": {"weapon": "Heavy Boarding Hook", "armor": "Leather River-Coat", "accessory": "Aether-Compass"},
            "inventory": ["Torch", "Bandage", "Bottle of Fir-Gin"],
            "skills": ["Grapple/Throw", "Calculated Trap", "Armor Crack"],
            "tags": ["player", "flesh", "river_folk", "biped", "amphibious", "whisker-sense"]
        }
        map_state["entities"].append(new_player)

    spawn_pool = region.get("flora", []) + region.get("fauna", []) + region.get("factions", [])
    if not spawn_pool: spawn_pool = ["crate"]
    
    layout = region.get("layout_type", "random")
    grid_w, grid_h = 50, 50

    if layout == "horizontal_road":
        road_y_center = 25
        for x in range(grid_w):
            for y_offset in [-1, 0, 1]:
                stone = templates.get("cobblestone").copy()
                stone["id"] = f"terr_{x}_{road_y_center + y_offset}"; stone["pos"] = [x, road_y_center + y_offset]
                map_state["entities"].append(stone)
        for _ in range(12):
            prop = templates.get(random.choice(spawn_pool))
            if prop:
                e = prop.copy(); e["id"] = f"ent_{random.randint(1000, 9999)}"
                e["pos"] = [random.randint(2, 47), road_y_center - random.randint(2, 6) if random.choice([True, False]) else road_y_center + random.randint(2, 6)]
                map_state["entities"].append(e)

    elif layout == "urban_grid":
        for x in range(0, grid_w, 2):
            for y in range(0, grid_h, 2):
                stone = templates.get("cobblestone").copy()
                stone["id"] = f"terr_{x}_{y}"; stone["pos"] = [x, y]
                map_state["entities"].append(stone)
        for b_x in range(5, 45, 10):
            for b_y in range(5, 45, 10):
                if random.random() < 0.7:
                    for wx in range(b_x, b_x + 5):
                        for wy in range(b_y, b_y + 5):
                            if wx == b_x or wx == b_x + 4 or wy == b_y or wy == b_y + 4:
                                if wx == b_x + 2 and wy == b_y + 4: continue 
                                wall = templates.get("stone_wall").copy()
                                wall["id"] = f"wall_{wx}_{wy}_{random.randint(10,99)}"; wall["pos"] = [wx, wy]
                                map_state["entities"].append(wall)
        for _ in range(10):
            prop = templates.get(random.choice(spawn_pool))
            if prop:
                e = prop.copy(); e["id"] = f"ent_{random.randint(1000, 9999)}"
                e["pos"] = [random.randint(2, 47), random.randint(2, 47)]
                map_state["entities"].append(e)

    elif layout == "clusters":
        num_clusters = random.randint(4, 7)
        for _ in range(num_clusters):
            center_x, center_y = random.randint(5, 45), random.randint(5, 45)
            for _ in range(random.randint(3, 8)):
                prop = templates.get(random.choice(spawn_pool))
                if prop:
                    e = prop.copy(); e["id"] = f"ent_{random.randint(1000, 9999)}"
                    e["pos"] = [center_x + random.randint(-3, 3), center_y + random.randint(-3, 3)]
                    map_state["entities"].append(e)

    for quest in story_data.get("active_quests", []):
        if quest.get("target_region") == region_id:
            map_state["meta"]["map_tags"].extend(quest.get("injected_tags", []))
            for inj_entity in quest.get("injected_entities", []):
                template = templates.get(inj_entity["template_id"])
                if template:
                    e = template.copy(); e["id"] = f"quest_{random.randint(1000, 9999)}"; e["pos"] = inj_entity["guaranteed_pos"]
                    map_state["entities"].append(e)

    # --- MACRO QUEST OBJECTIVE SPAWNING ---
    if quest_deck and len(quest_deck) > 0:
        step = quest_deck[0]
        if step.get("type") == "explore_interior":
            b_type = step.get("building_type", "bandit_camp")
            # Spawn a distinct quest prop
            q_prop = {
                "id": "quest_loc_01", 
                "name": "Quest Location", "type": "prop", 
                "pos": [15, 15], # Fixed pos for simplicity in this version
                "building_type": b_type,
                "tags": ["quest_entrance", "solid", "high_value"]
            }
            map_state["entities"].append(q_prop)

    # --- INJECT STORY SEED ---
    seed_type = random.choice(["wrecked_sump_cart", "bloody_satchel"])
    seed_tmpl = templates.get(seed_type)
    if seed_tmpl:
        s = seed_tmpl.copy()
        s["id"] = f"seed_{random.randint(1000, 9999)}"
        # Find a walkable spot near the center
        s["pos"] = [random.randint(20, 30), random.randint(20, 30)]
        map_state["entities"].append(s)

    with open("local_map_state.json", "w", encoding="utf-8") as f: json.dump(map_state, f, indent=2)
    return True

def generate_interior_room(card_data):
    """Builds a structured tactical grid based on the room card."""
    room_type = card_data.get("room_type", "generic_room")
    threat = card_data.get("threat", 0)
    
    # Initialize a fresh map state dictionary
    new_map = {
        "meta": {"grid_size": [15, 15], "room_type": room_type, "in_combat": False},
        "entities": []
    }
    
    # BOX THE ROOM WITH WALLS (Standard Architecture)
    for x in range(15):
        for y in range(15):
            if x == 0 or x == 14 or y == 0 or y == 14:
                # Leave a gap for the door at [7, 0]
                if x == 7 and y == 0: continue
                new_map["entities"].append({"name": "Stone Wall", "type": "prop", "tags": ["wall", "solid"], "pos": [x, y]})
    
    # Add the Player
    new_map["entities"].append({
        "id": "char_01", "name": "Captain Jax", "type": "player", "pos": [7, 14],
        "species": "Human", "tracks": {"offense": "Might", "defense": "Reflexes"},
        "hp": 20, "max_hp": 20, "resources": {"stamina": 10, "max_stamina": 10, "focus": 10, "max_focus": 10},
        "stats": {"Might": 4, "Reflexes": 3, "Awareness": 6}, "tags": ["player", "flesh"]
    })
    
    # Spawn a door to the next room at the top of the map
    new_map["entities"].append({"name": "Heavy Door", "type": "prop", "tags": ["transition_door", "solid"], "pos": [7, 0]})
    
    # If it's a threat room, spawn enemies
    if threat > 0:
        new_map["meta"]["in_combat"] = True
        # Simple threat-based spawn for now
        for i in range(threat + 1):
            new_map["entities"].append({
                "id": f"interior_enemy_{i}", "name": "Dungeon Guard", "type": "hostile", 
                "pos": [random.randint(2, 12), random.randint(2, 10)],
                "hp": 10, "max_hp": 10, "tags": ["hostile", "flesh"]
            })
        
    return new_map
