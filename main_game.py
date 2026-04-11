import pygame
import sys
import json
import engine
import narrator
import entities
import ui_manager
import actions

pygame.init()

CELL_SIZE = 40  
GRID_WIDTH = 20  
GRID_HEIGHT = 15 
UI_HEIGHT = 180 
WINDOW_WIDTH = CELL_SIZE * GRID_WIDTH
WINDOW_HEIGHT = CELL_SIZE * GRID_HEIGHT + UI_HEIGHT 

screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Shatterlands: Tactical View")

COLORS = {
    "bg": (20, 25, 25), "grid": (40, 45, 45),
    "player": (50, 150, 255), "hostile": (220, 50, 50), "npc": (200, 180, 50),
    "dead": (100, 20, 20), "terrain": (60, 65, 65), "wall": (100, 100, 105),
    "wood": (110, 70, 40), "plant": (40, 120, 40), "water": (40, 100, 160),
    "cold": (180, 220, 240), "stone": (90, 90, 90),
    "text": (220, 220, 220), "ui_bg": (15, 15, 20),
    "menu_bg": (40, 40, 50), "menu_hover": (70, 70, 90), "menu_border": (150, 150, 150),
    "title": (255, 215, 0)
}

font = pygame.font.SysFont("consolas", 16)
icon_font = pygame.font.SysFont("consolas", 20, bold=True)
title_font = pygame.font.SysFont("consolas", 36, bold=True)

app_state = "MAIN_MENU"
status_text = "System Online. Immersive Sim Engine active."
transition_target = None

context_menu = {
    "active": False, "x": 0, "y": 0, 
    "target_name": None, "target_id": None, "target_pos": None, 
    "options": [], "page": "main"
}

def load_map_data():
    try:
        with open("local_map_state.json", "r") as f: return json.load(f)
    except FileNotFoundError: return {"entities": []}

def get_camera_offset(map_data):
    player_pos = [25, 25] 
    map_w, map_h = map_data.get("meta", {}).get("grid_size", [50, 50])
    for e in map_data.get("entities", []):
        if e.get("type") == "player":
            player_pos = e["pos"]
            break
    cam_x = max(0, min(player_pos[0] - (GRID_WIDTH // 2), map_w - GRID_WIDTH))
    cam_y = max(0, min(player_pos[1] - (GRID_HEIGHT // 2), map_h - GRID_HEIGHT))
    return cam_x, cam_y

def draw_grid():
    for x in range(0, WINDOW_WIDTH, CELL_SIZE): pygame.draw.line(screen, COLORS["grid"], (x, 0), (x, WINDOW_HEIGHT - UI_HEIGHT))
    for y in range(0, WINDOW_HEIGHT - UI_HEIGHT, CELL_SIZE): pygame.draw.line(screen, COLORS["grid"], (0, y), (WINDOW_WIDTH, y))

def draw_entities(map_data, cam_x, cam_y):
    for entity in map_data.get("entities", []):
        grid_x = entity["pos"][0] - cam_x
        grid_y = entity["pos"][1] - cam_y
        if 0 <= grid_x < GRID_WIDTH and 0 <= grid_y < GRID_HEIGHT:
            pixel_x, pixel_y = grid_x * CELL_SIZE, grid_y * CELL_SIZE
            tags = entity.get("tags", [])
            ent_type = entity.get("type", "prop")
            
            color = COLORS.get(ent_type, (150, 150, 150))
            if "water" in tags: color = COLORS["water"]
            elif "plant" in tags: color = COLORS["plant"]
            elif "wood" in tags: color = COLORS["wood"]
            elif "stone" in tags: color = COLORS["stone"]
            elif "cold" in tags: color = COLORS["cold"]
            
            if "wall" in tags: color = COLORS["wall"]
            if "terrain" in tags or ent_type == "terrain": color = COLORS["terrain"]
            if ent_type == "npc": color = COLORS["npc"]
            if ent_type == "hostile": color = COLORS["hostile"]
            if ent_type == "player": color = COLORS["player"]
            if "dead" in tags: color = COLORS["dead"]
            
            pygame.draw.rect(screen, color, (pixel_x + 2, pixel_y + 2, CELL_SIZE - 4, CELL_SIZE - 4))
            
            if ent_type != "terrain" and "dead" not in tags:
                initial = "@" if ent_type == "player" else entity["name"][0].upper()
                text_surf = icon_font.render(initial, True, (240, 240, 240))
                shadow_surf = icon_font.render(initial, True, (20, 20, 20))
                text_rect = text_surf.get_rect(center=(pixel_x + CELL_SIZE//2, pixel_y + CELL_SIZE//2))
                screen.blit(shadow_surf, (text_rect.x + 1, text_rect.y + 1))
                screen.blit(text_surf, text_rect)

def draw_text_wrapped(surface, text, color, rect, font, line_spacing=4):
    words = text.split(' ')
    lines, current_line = [], []
    for word in words:
        if font.size(' '.join(current_line + [word]))[0] <= rect.width: current_line.append(word)
        else:
            lines.append(' '.join(current_line))
            current_line = [word]
    lines.append(' '.join(current_line))
    y = rect.y
    for line in lines:
        surface.blit(font.render(line, True, color), (rect.x, y))
        y += font.size(line)[1] + line_spacing

def draw_context_menu():
    if not context_menu["active"]: return
    menu_width = 180
    option_height = 30
    header_height = 30
    menu_height = (len(context_menu["options"]) * option_height) + header_height
    menu_rect = pygame.Rect(context_menu["x"], context_menu["y"], menu_width, menu_height)
    pygame.draw.rect(screen, COLORS["menu_bg"], menu_rect)
    pygame.draw.rect(screen, COLORS["menu_border"], menu_rect, 2)
    target_name = context_menu.get("target_name") or "Empty Terrain"
    if len(target_name) > 18: target_name = target_name[:15] + "..."
    screen.blit(font.render(target_name, True, COLORS["title"]), (context_menu["x"] + 10, context_menu["y"] + 5))
    pygame.draw.line(screen, COLORS["menu_border"], (context_menu["x"], context_menu["y"] + header_height), (context_menu["x"] + menu_width, context_menu["y"] + header_height))
    mouse_x, mouse_y = pygame.mouse.get_pos()
    for i, option in enumerate(context_menu["options"]):
        opt_rect = pygame.Rect(context_menu["x"], context_menu["y"] + header_height + (i * option_height), menu_width, option_height)
        if opt_rect.collidepoint(mouse_x, mouse_y): pygame.draw.rect(screen, COLORS["menu_hover"], opt_rect)
        screen.blit(font.render(option, True, COLORS["text"]), (opt_rect.x + 10, opt_rect.y + 5))

def generate_menu_options(entity, player, page="main"):
    if not entity: return ["Move Here", "Examine Area", "Cancel"]
    
    tags = entity.get("tags", [])
    ent_type = entity.get("type", "prop")
    
    # Get all valid actions from registry
    valid_actions = actions.get_valid_actions(player, entity)
    options = []

    if page == "main":
        if "player" in tags: options.append("Examine Self")
        
        # 1. Essential context actions
        if "container" in tags: options.append("Open")
        if "dead" in tags: options.append("Loot")
        if ent_type == "hostile" and "dead" not in tags: options.append("Attack")
        
        # 2. Most logical stat actions (Top 2 unique logical ones)
        # We find actions that the player is actually "good" at
        stat_actions = []
        for act in valid_actions:
            best_stat = entities.get_best_stat_for_action(player, act)
            if best_stat: # Only include actions that actually use stats
                stat_val = entities.get_stat(player, best_stat)
                stat_actions.append((act, best_stat, stat_val))
        
        # Sort by player's stat value
        stat_actions.sort(key=lambda x: x[2], reverse=True)
        
        # Take top 2
        for i in range(min(2, len(stat_actions))):
            act, stat, val = stat_actions[i]
            options.append(f"[{stat}] {act}")
            
        options.append("Examine")
        if len(valid_actions) > 3: # Loot, Open, Examine already take space
            options.append("More Actions...")
            
    elif page == "more":
        # Show all valid actions from the registry
        for act in valid_actions:
            best_stat = entities.get_best_stat_for_action(player, act)
            if best_stat:
                options.append(f"[{best_stat}] {act}")
            else:
                options.append(act) # Generic actions like Loot
        options.append("Back")

    options.append("Cancel")
    
    # Remove duplicates while preserving order
    seen = set()
    return [x for x in options if not (x in seen or seen.add(x))]

def draw_main_menu():
    screen.fill(COLORS["bg"])
    screen.blit(title_font.render("SHATTERLANDS", True, COLORS["title"]), title_font.render("SHATTERLANDS", True, COLORS["title"]).get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 4)))
    screen.blit(font.render("Tactical Sim Engine", True, COLORS["text"]), font.render("Tactical Sim Engine", True, COLORS["text"]).get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 4 + 40)))
    mouse_x, mouse_y = pygame.mouse.get_pos()
    btn_x = (WINDOW_WIDTH // 2) - 100
    buttons = [
        {"rect": pygame.Rect(btn_x, WINDOW_HEIGHT // 2, 200, 50), "text": "New Game", "action": "NEW_GAME"},
        {"rect": pygame.Rect(btn_x, WINDOW_HEIGHT // 2 + 70, 200, 50), "text": "Continue", "action": "LOAD_GAME"},
        {"rect": pygame.Rect(btn_x, WINDOW_HEIGHT // 2 + 140, 200, 50), "text": "Quit", "action": "QUIT"}
    ]
    for btn in buttons:
        pygame.draw.rect(screen, COLORS["menu_hover"] if btn["rect"].collidepoint(mouse_x, mouse_y) else COLORS["menu_bg"], btn["rect"])
        pygame.draw.rect(screen, COLORS["menu_border"], btn["rect"], 2)
        screen.blit(font.render(btn["text"], True, COLORS["text"]), font.render(btn["text"], True, COLORS["text"]).get_rect(center=btn["rect"].center))
    pygame.display.flip()
    return buttons

def draw_tactical_screen(map_data, cam_x, cam_y):
    screen.fill(COLORS["bg"])
    draw_grid()
    draw_entities(map_data, cam_x, cam_y)
    draw_context_menu()
    pygame.draw.rect(screen, COLORS["ui_bg"], (0, WINDOW_HEIGHT - UI_HEIGHT, WINDOW_WIDTH, UI_HEIGHT))
    pygame.draw.line(screen, (100, 100, 100), (0, WINDOW_HEIGHT - UI_HEIGHT), (WINDOW_WIDTH, WINDOW_HEIGHT - UI_HEIGHT), 2)
    draw_text_wrapped(screen, status_text, COLORS["text"], pygame.Rect(15, WINDOW_HEIGHT - UI_HEIGHT + 15, WINDOW_WIDTH - 30, UI_HEIGHT - 30), font)
    global_pos = map_data.get("meta", {}).get("global_pos", [0,0])
    screen.blit(font.render(f"World: {global_pos} | Local: {cam_x},{cam_y} | Time: {map_data.get('meta', {}).get('clock', 0)}", True, (100, 100, 100)), (WINDOW_WIDTH - 350, 10))

def draw_transition_prompt():
    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    overlay.set_alpha(150)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))
    prompt_rect = pygame.Rect((WINDOW_WIDTH - 300)//2, (WINDOW_HEIGHT - 150)//2, 300, 150)
    pygame.draw.rect(screen, COLORS["menu_bg"], prompt_rect)
    pygame.draw.rect(screen, COLORS["menu_border"], prompt_rect, 2)
    text_surf = font.render("Travel to a new region?", True, COLORS["text"])
    screen.blit(text_surf, text_surf.get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 - 30)))
    btn_yes = pygame.Rect(WINDOW_WIDTH//2 - 90, WINDOW_HEIGHT//2 + 10, 80, 40)
    btn_no = pygame.Rect(WINDOW_WIDTH//2 + 10, WINDOW_HEIGHT//2 + 10, 80, 40)
    mouse_x, mouse_y = pygame.mouse.get_pos()
    pygame.draw.rect(screen, COLORS["menu_hover"] if btn_yes.collidepoint(mouse_x, mouse_y) else COLORS["ui_bg"], btn_yes)
    pygame.draw.rect(screen, COLORS["menu_hover"] if btn_no.collidepoint(mouse_x, mouse_y) else COLORS["ui_bg"], btn_no)
    pygame.draw.rect(screen, COLORS["menu_border"], btn_yes, 1)
    pygame.draw.rect(screen, COLORS["menu_border"], btn_no, 1)
    screen.blit(font.render("Yes", True, COLORS["text"]), font.render("Yes", True, COLORS["text"]).get_rect(center=btn_yes.center))
    screen.blit(font.render("No", True, COLORS["text"]), font.render("No", True, COLORS["text"]).get_rect(center=btn_no.center))
    pygame.display.flip()
    return btn_yes, btn_no

def attempt_move(grid_x, grid_y, map_data):
    global app_state, transition_target, status_text
    grid_w, grid_h = map_data.get("meta", {}).get("grid_size", [50, 50])
    
    for e in map_data.get("entities", []):
        if e["pos"] == [grid_x, grid_y] and ("solid" in e.get("tags", []) or e.get("hp", 0) > 0):
            status_text = f"System: Path blocked by {e['name']}."
            return 

    if grid_x <= 0 or grid_x >= grid_w - 1 or grid_y <= 0 or grid_y >= grid_h - 1:
        app_state = "TRANSITION_PROMPT"
        transition_target = [grid_x, grid_y]
        status_text = "System: Awaiting travel confirmation..."
    else:
        engine.execute_move("char_01", grid_x, grid_y)
        status_text = f"System: Valerius moved to [{grid_x}, {grid_y}]."

def main():
    global status_text, app_state, transition_target
    clock = pygame.time.Clock()
    map_data = load_map_data()
    cam_x, cam_y = get_camera_offset(map_data)

    while True:
        if app_state == "MAIN_MENU":
            buttons = draw_main_menu()
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for btn in buttons:
                        if btn["rect"].collidepoint(event.pos[0], event.pos[1]):
                            if btn["action"] == "NEW_GAME":
                                engine.start_new_game()
                                map_data = load_map_data()
                                status_text = "Director: A new journey begins."
                                app_state = "PLAYING"
                            elif btn["action"] == "LOAD_GAME":
                                map_data = load_map_data()
                                status_text = "Director: Welcome back."
                                app_state = "PLAYING"
                            elif btn["action"] == "QUIT":
                                pygame.quit(); sys.exit()

        elif app_state == "CHARACTER_SHEET":
            draw_tactical_screen(map_data, cam_x, cam_y)
            clickable_zones = ui_manager.draw_multi_tab_menu(screen, map_data, font, title_font, COLORS, WINDOW_WIDTH, WINDOW_HEIGHT)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                elif event.type == pygame.KEYDOWN and event.key in [pygame.K_c, pygame.K_ESCAPE]:
                    ui_manager.UI_STATE["context_menu"]["active"] = False
                    app_state = "PLAYING"
                
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    clicked_zone = False
                    
                    if event.button == 1: # LEFT CLICK
                        for zone in clickable_zones:
                            if zone["rect"].collidepoint(event.pos):
                                clicked_zone = True
                                
                                if zone["action"] == "switch_tab":
                                    ui_manager.UI_STATE["active_tab"] = zone["target"]
                                    ui_manager.UI_STATE["context_menu"]["active"] = False
                                    
                                elif zone["action"] == "unequip":
                                    engine.execute_unequip("char_01", zone["slot"])
                                    map_data = load_map_data()
                                    
                                elif zone["action"] == "context_action":
                                    if zone["choice"] == "Equip": engine.execute_equip("char_01", zone["item"])
                                    elif zone["choice"] == "Drop": engine.execute_drop("char_01", zone["item"])
                                    elif zone["choice"] == "Use": engine.execute_use("char_01", zone["item"])
                                    ui_manager.UI_STATE["context_menu"]["active"] = False
                                    map_data = load_map_data()
                                break
                        
                        if not clicked_zone: ui_manager.UI_STATE["context_menu"]["active"] = False
                            
                    elif event.button == 3: # RIGHT CLICK
                        for zone in clickable_zones:
                            if zone["rect"].collidepoint(event.pos) and zone["action"] == "inventory_item":
                                item = zone["item"]
                                options = []
                                items_db = entities.load_items()
                                if item in items_db.get("weapons", {}) or item in items_db.get("armor", {}) or item in items_db.get("accessories", {}):
                                    options.append("Equip")
                                else:
                                    options.append("Use")
                                options.append("Drop")
                                
                                ui_manager.UI_STATE["context_menu"] = {
                                    "active": True, "x": event.pos[0], "y": event.pos[1],
                                    "item": item, "options": options
                                }

        elif app_state == "PLAYING":
            cam_x, cam_y = get_camera_offset(map_data)
            player = next((e for e in map_data.get("entities", []) if e["type"] == "player"), None)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE: app_state = "MAIN_MENU"
                    elif event.key == pygame.K_c: app_state = "CHARACTER_SHEET"
                    else:
                        if player:
                            if "dead" in player.get("tags", []):
                                status_text = "System: YOU ARE DEAD. Game Over. (Press ESC)"
                            else:
                                px, py = player["pos"]
                                if event.key in [pygame.K_w, pygame.K_UP]: attempt_move(px, py - 1, map_data)
                                elif event.key in [pygame.K_s, pygame.K_DOWN]: attempt_move(px, py + 1, map_data)
                                elif event.key in [pygame.K_a, pygame.K_LEFT]: attempt_move(px - 1, py, map_data)
                                elif event.key in [pygame.K_d, pygame.K_RIGHT]: attempt_move(px + 1, py, map_data)
                
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_x, mouse_y = event.pos
                    grid_x = (mouse_x // CELL_SIZE) + cam_x
                    grid_y = (mouse_y // CELL_SIZE) + cam_y
                    
                    # FIX 2: Priority Sorting so we click Bodies instead of Floors
                    ents_at_pos = [e for e in map_data.get("entities", []) if e["pos"] == [grid_x, grid_y]]
                    clicked_entity = None
                    for p_type in ["player", "hostile", "npc"]:
                        if not clicked_entity: clicked_entity = next((e for e in ents_at_pos if e.get("type") == p_type), None)
                    if not clicked_entity: clicked_entity = next((e for e in ents_at_pos if "dead" in e.get("tags", [])), None)
                    if not clicked_entity: clicked_entity = next((e for e in ents_at_pos if e.get("type") == "prop"), None)
                    if not clicked_entity: clicked_entity = ents_at_pos[0] if ents_at_pos else None
                    
                    if player and "dead" in player.get("tags", []):
                        status_text = "System: YOU ARE DEAD. Game Over. (Press ESC)"
                        context_menu["active"] = False
                        continue

                    if event.button == 1: 
                        if context_menu["active"]:
                            menu_width, option_height, header_height = 180, 30, 30
                            menu_rect = pygame.Rect(context_menu["x"], context_menu["y"], menu_width, (len(context_menu["options"]) * option_height) + header_height)
                            
                            if menu_rect.collidepoint(mouse_x, mouse_y):
                                if mouse_y > context_menu["y"] + header_height:
                                    index = (mouse_y - (context_menu["y"] + header_height)) // option_height
                                    if index < len(context_menu["options"]):
                                        selection = context_menu["options"][index]
                                        
                                        if selection == "More Actions...":
                                            context_menu["page"] = "more"
                                            # We need to find the target entity again or store it in context_menu
                                            # For now, let's look it up by ID/Pos
                                            target = next((e for e in map_data.get("entities", []) if e.get("id") == context_menu["target_id"]), None)
                                            context_menu["options"] = generate_menu_options(target, player, page="more")
                                            continue # Keep menu open
                                            
                                        elif selection == "Back":
                                            context_menu["page"] = "main"
                                            target = next((e for e in map_data.get("entities", []) if e.get("id") == context_menu["target_id"]), None)
                                            context_menu["options"] = generate_menu_options(target, player, page="main")
                                            continue # Keep menu open

                                        if selection != "Cancel":
                                            status_text = f"System: Executing {selection}..."
                                            draw_tactical_screen(map_data, cam_x, cam_y); pygame.display.flip()
                                            
                                            if selection in ["Loot", "Open"]: 
                                                res = engine.execute_loot("char_01", context_menu["target_id"])
                                                if res == "Too far.": status_text = "System: Too far away to loot!"
                                                elif res == "Empty.": status_text = "System: Target is empty."
                                                else: status_text = "System: Looted all items."
                                            elif selection == "Attack": 
                                                engine.execute_attack("char_01", context_menu["target_id"])
                                            elif selection == "Examine": 
                                                engine.execute_examine("char_01", context_menu["target_id"])
                                            elif selection == "Move Here": 
                                                attempt_move(context_menu["target_pos"][0], context_menu["target_pos"][1], map_data)
                                            elif selection == "Examine Area": 
                                                engine.execute_examine_area("char_01", context_menu["target_pos"][0], context_menu["target_pos"][1])
                                            elif selection == "Examine Self": 
                                                engine.execute_examine("char_01", "char_01")
                                            # NEW STAT ACTION ROUTER
                                            elif selection.startswith("[") and "]" in selection:
                                                engine.execute_stat_action("char_01", context_menu["target_id"], selection)
                                            
                                            if selection not in ["Move Here", "Cancel", "Loot", "Open"] and not selection.startswith("["):
                                                status_text = f"Director: {narrator.generate_flavor_text()}"
                            
                            context_menu["active"] = False
                            continue

                        elif mouse_y < WINDOW_HEIGHT - UI_HEIGHT:
                            if clicked_entity and "hostile" in clicked_entity.get("tags", []):
                                status_text = "System: Attacking... (AI is thinking)"
                                draw_tactical_screen(map_data, cam_x, cam_y); pygame.display.flip()
                                engine.execute_attack("char_01", clicked_entity.get("id", clicked_entity["name"]))
                                status_text = f"Director: {narrator.generate_flavor_text()}"
                            elif not clicked_entity:
                                attempt_move(grid_x, grid_y, map_data)

                    elif event.button == 3:
                        if mouse_y < WINDOW_HEIGHT - UI_HEIGHT:
                            context_menu["active"] = True
                            context_menu["x"] = mouse_x
                            context_menu["y"] = mouse_y
                            context_menu["page"] = "main"
                            context_menu["target_pos"] = [grid_x, grid_y]
                            context_menu["target_name"] = clicked_entity["name"] if clicked_entity else None
                            context_menu["target_id"] = clicked_entity.get("id", clicked_entity["name"]) if clicked_entity else None
                            # FIX: Pass the player entity to the menu generator
                            context_menu["options"] = generate_menu_options(clicked_entity, player, page="main")

            # --- End of PLAYING event loop ---
            map_data = load_map_data()
            cam_x, cam_y = get_camera_offset(map_data)
            draw_tactical_screen(map_data, cam_x, cam_y)
            
            # --- NEW: AT-A-GLANCE HOVER TOOLTIPS ---
            mouse_x, mouse_y = pygame.mouse.get_pos()
            # Only draw tooltips if we are on the map (not the UI) and no menus are open
            if not context_menu["active"] and mouse_y < WINDOW_HEIGHT - UI_HEIGHT:
                hover_grid_x = (mouse_x // CELL_SIZE) + cam_x
                hover_grid_y = (mouse_y // CELL_SIZE) + cam_y
                
                # Use our Z-Index logic to prioritize bodies over the floor
                ents_at_pos = [e for e in map_data.get("entities", []) if e["pos"] == [hover_grid_x, hover_grid_y]]
                hovered_ent = None
                for p_type in ["player", "hostile", "npc"]:
                    if not hovered_ent: hovered_ent = next((e for e in ents_at_pos if e.get("type") == p_type), None)
                if not hovered_ent: hovered_ent = next((e for e in ents_at_pos if "dead" in e.get("tags", [])), None)
                if not hovered_ent: hovered_ent = next((e for e in ents_at_pos if e.get("type") == "prop"), None)
                
                if hovered_ent:
                    ui_manager.draw_hover_tooltip(screen, hovered_ent, (mouse_x, mouse_y), font, COLORS)
            # ----------------------------------------

            pygame.display.flip()
            
        elif app_state == "TRANSITION_PROMPT":
            draw_tactical_screen(map_data, cam_x, cam_y)
            btn_yes, btn_no = draw_transition_prompt()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if btn_yes.collidepoint(event.pos):
                        engine.execute_transition(transition_target[0], transition_target[1])
                        map_data = load_map_data()
                        cam_x, cam_y = get_camera_offset(map_data)
                        status_text = "Director: You have entered a new region."
                        app_state = "PLAYING"
                    elif btn_no.collidepoint(event.pos):
                        status_text = "System: Transition cancelled."
                        app_state = "PLAYING"

        clock.tick(30)

if __name__ == "__main__":
    main()
