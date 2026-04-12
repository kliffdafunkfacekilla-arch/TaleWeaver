import pygame
import sys
import json
import engine
import narrator
import entities
import ui_manager
import actions
import threading

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
    menu_width, opt_h, head_h = 180, 30, 30
    menu_rect = pygame.Rect(context_menu["x"], context_menu["y"], menu_width, (len(context_menu["options"]) * opt_h) + head_h)
    pygame.draw.rect(screen, COLORS["menu_bg"], menu_rect)
    pygame.draw.rect(screen, COLORS["menu_border"], menu_rect, 2)
    target_name = context_menu.get("target_name") or "Terrain"
    if len(target_name) > 18: target_name = target_name[:15] + "..."
    screen.blit(font.render(target_name, True, COLORS["title"]), (context_menu["x"] + 10, context_menu["y"] + 5))
    pygame.draw.line(screen, COLORS["menu_border"], (context_menu["x"], context_menu["y"] + head_h), (context_menu["x"] + menu_width, context_menu["y"] + head_h))
    mx, my = pygame.mouse.get_pos()
    for i, option in enumerate(context_menu["options"]):
        opt_rect = pygame.Rect(context_menu["x"], context_menu["y"] + head_h + (i * opt_h), menu_width, opt_h)
        if opt_rect.collidepoint(mx, my): pygame.draw.rect(screen, COLORS["menu_hover"], opt_rect)
        screen.blit(font.render(option, True, COLORS["text"]), (opt_rect.x + 10, opt_rect.y + 5))

def generate_menu_options(entity, player, page="main"):
    if not entity: return ["Move Here", "Examine Area", "Cancel"]
    tags = entity.get("tags", []); ent_type = entity.get("type", "prop")
    valid_actions = actions.get_valid_actions(player, entity)
    options = []
    if page == "main":
        if "player" in tags: options.append("Examine Self")
        if "container" in tags: options.append("Open")
        if "dead" in tags: options.append("Loot")
        if ent_type == "hostile" and "dead" not in tags: options.append("Attack")
        stat_actions = []
        for act in valid_actions:
            best_stat = entities.get_best_stat_for_action(player, act)
            if best_stat: stat_actions.append((act, best_stat, entities.get_stat(player, best_stat)))
        stat_actions.sort(key=lambda x: x[2], reverse=True)
        for i in range(min(2, len(stat_actions))): options.append(f"[{stat_actions[i][1]}] {stat_actions[i][0]}")
        options.append("Examine")
        if len(valid_actions) > 3: options.append("More Actions...")
    elif page == "more":
        for act in valid_actions:
            bs = entities.get_best_stat_for_action(player, act)
            if bs: options.append(f"[{bs}] {act}")
            else: options.append(act)
        options.append("Back")
    options.append("Cancel"); seen = set()
    return [x for x in options if not (x in seen or seen.add(x))]

def draw_main_menu():
    screen.fill(COLORS["bg"])
    screen.blit(title_font.render("SHATTERLANDS", True, COLORS["title"]), title_font.render("SHATTERLANDS", True, COLORS["title"]).get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 4)))
    mx, my = pygame.mouse.get_pos(); bx = (WINDOW_WIDTH // 2) - 100
    btns = [{"rect": pygame.Rect(bx, WINDOW_HEIGHT // 2, 200, 50), "text": "New Game", "action": "NEW_GAME"}, {"rect": pygame.Rect(bx, WINDOW_HEIGHT // 2 + 70, 200, 50), "text": "Continue", "action": "LOAD_GAME"}, {"rect": pygame.Rect(bx, WINDOW_HEIGHT // 2 + 140, 200, 50), "text": "Quit", "action": "QUIT"}]
    for btn in btns:
        pygame.draw.rect(screen, COLORS["menu_hover"] if btn["rect"].collidepoint(mx, my) else COLORS["menu_bg"], btn["rect"])
        pygame.draw.rect(screen, COLORS["menu_border"], btn["rect"], 2)
        screen.blit(font.render(btn["text"], True, COLORS["text"]), font.render(btn["text"], True, COLORS["text"]).get_rect(center=btn["rect"].center))
    pygame.display.flip(); return btns

def draw_tactical_screen(map_data, cam_x, cam_y):
    screen.fill(COLORS["bg"]); draw_grid(); draw_entities(map_data, cam_x, cam_y); draw_context_menu()
    pygame.draw.rect(screen, COLORS["ui_bg"], (0, WINDOW_HEIGHT - UI_HEIGHT, WINDOW_WIDTH, UI_HEIGHT))
    pygame.draw.line(screen, (100, 100, 100), (0, WINDOW_HEIGHT - UI_HEIGHT), (WINDOW_WIDTH, WINDOW_HEIGHT - UI_HEIGHT), 2)
    draw_text_wrapped(screen, status_text, COLORS["text"], pygame.Rect(15, WINDOW_HEIGHT - UI_HEIGHT + 15, WINDOW_WIDTH - 30, UI_HEIGHT - 30), font)
    
    # MODE INDICATOR
    is_combat = map_data.get("meta", {}).get("in_combat", False)
    global_pos = map_data.get("meta", {}).get("global_pos", [0,0])
    player = next((e for e in map_data.get("entities", []) if e["type"] == "player"), None)
    if is_combat:
        mode_color = COLORS["hostile"]
        mode_text = "🚨 ENCOUNTER MODE 🚨"
    else:
        mode_color = COLORS["npc"]
        mode_text = "👁️ EXPLORE MODE (Free)"
        
    screen.blit(title_font.render(mode_text, True, mode_color), (WINDOW_WIDTH - 350, 10))
    
    # RIGID PULSE HUD (Only show in combat)
    if is_combat:
        beats = player.get("resources", {}).get("beats", {}) if player else {}
        m, s, f = beats.get("move", 0), beats.get("stamina", 0), beats.get("focus", 0)
        tactic = entities.get_best_clash_tactic(player) if player else "N/A"
        beat_str = f"PULSE: M:[{m}] S:[{s}] F:[{f}] | Tactic: {tactic}"
        screen.blit(font.render(beat_str, True, COLORS["title"]), (WINDOW_WIDTH - 350, 40))
    else:
        screen.blit(font.render(f"World: {global_pos} | Clock: {map_data.get('meta', {}).get('clock', 0)}", True, (100, 100, 100)), (WINDOW_WIDTH - 350, 40))

def draw_transition_prompt():
    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT)); overlay.set_alpha(150); overlay.fill((0, 0, 0)); screen.blit(overlay, (0, 0))
    pr = pygame.Rect((WINDOW_WIDTH - 300)//2, (WINDOW_HEIGHT - 150)//2, 300, 150); pygame.draw.rect(screen, COLORS["menu_bg"], pr); pygame.draw.rect(screen, COLORS["menu_border"], pr, 2)
    screen.blit(font.render("Travel to a new region?", True, COLORS["text"]), font.render("Travel to a new region?", True, COLORS["text"]).get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 - 30)))
    by, bn = pygame.Rect(WINDOW_WIDTH//2 - 90, WINDOW_HEIGHT//2 + 10, 80, 40), pygame.Rect(WINDOW_WIDTH//2 + 10, WINDOW_HEIGHT//2 + 10, 80, 40)
    mx, my = pygame.mouse.get_pos(); pygame.draw.rect(screen, COLORS["menu_hover"] if by.collidepoint(mx, my) else COLORS["ui_bg"], by); pygame.draw.rect(screen, COLORS["menu_hover"] if bn.collidepoint(mx, my) else COLORS["ui_bg"], bn)
    pygame.draw.rect(screen, COLORS["menu_border"], by, 1); pygame.draw.rect(screen, COLORS["menu_border"], bn, 1)
    screen.blit(font.render("Yes", True, COLORS["text"]), font.render("Yes", True, COLORS["text"]).get_rect(center=by.center)); screen.blit(font.render("No", True, COLORS["text"]), font.render("No", True, COLORS["text"]).get_rect(center=bn.center))
    pygame.display.flip(); return by, bn

def attempt_move(grid_x, grid_y, map_data):
    global app_state, transition_target, status_text
    gw, gh = map_data.get("meta", {}).get("grid_size", [50, 50])
    for e in map_data.get("entities", []):
        if e["pos"] == [grid_x, grid_y] and ("solid" in e.get("tags", []) or e.get("hp", 0) > 0):
            status_text = f"System: Path blocked by {e['name']}."; return 
    if grid_x <= 0 or grid_x >= gw - 1 or grid_y <= 0 or grid_y >= gh - 1:
        app_state = "TRANSITION_PROMPT"; transition_target = [grid_x, grid_y]; status_text = "System: Awaiting confirmation..."
    else:
        res = engine.execute_move("char_01", grid_x, grid_y)
        if "beats" in res: status_text = f"System: {res}"
        else: status_text = f"System: Moved to [{grid_x}, {grid_y}]."

def trigger_narration():
    global status_text; status_text = "Director: [Thinking...]"; new_text = narrator.generate_flavor_text(); status_text = f"Director: {new_text}"

def main():
    global status_text, app_state, transition_target
    clock = pygame.time.Clock(); map_data = load_map_data(); cam_x, cam_y = get_camera_offset(map_data)
    while True:
        if app_state == "MAIN_MENU":
            btns = draw_main_menu()
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for btn in btns:
                        if btn["rect"].collidepoint(event.pos):
                            if btn["action"] == "NEW_GAME": engine.start_new_game(); map_data = load_map_data(); status_text = "Director: A new journey."; app_state = "PLAYING"
                            elif btn["action"] == "LOAD_GAME": map_data = load_map_data(); status_text = "Director: Welcome back."; app_state = "PLAYING"
                            elif btn["action"] == "QUIT": pygame.quit(); sys.exit()
        elif app_state == "CHARACTER_SHEET":
            draw_tactical_screen(map_data, cam_x, cam_y); clickable_zones = ui_manager.draw_multi_tab_menu(screen, map_data, font, title_font, COLORS, WINDOW_WIDTH, WINDOW_HEIGHT)
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                elif event.type == pygame.KEYDOWN and event.key in [pygame.K_c, pygame.K_ESCAPE]: ui_manager.UI_STATE["context_menu"]["active"] = False; app_state = "PLAYING"
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    cz_hit = False
                    if event.button == 1:
                        for zone in clickable_zones:
                            if zone["rect"].collidepoint(event.pos):
                                cz_hit = True
                                if zone["action"] == "switch_tab": ui_manager.UI_STATE["active_tab"] = zone["target"]
                                elif zone["action"] == "unequip": engine.execute_unequip("char_01", zone["slot"]); map_data = load_map_data()
                                elif zone["action"] == "context_action":
                                    if zone["choice"] == "Equip": engine.execute_equip("char_01", zone["item"])
                                    elif zone["choice"] == "Drop": engine.execute_drop("char_01", zone["item"])
                                    elif zone["choice"] == "Use": engine.execute_use("char_01", zone["item"])
                                    ui_manager.UI_STATE["context_menu"]["active"] = False; map_data = load_map_data()
                                break
                        if not cz_hit: ui_manager.UI_STATE["context_menu"]["active"] = False
                    elif event.button == 3:
                        for zone in clickable_zones:
                            if zone["rect"].collidepoint(event.pos) and zone["action"] == "inventory_item":
                                item = zone["item"]; options = ["Equip" if item in actions.get_valid_actions(None, None) else "Use", "Drop"]; ui_manager.UI_STATE["context_menu"] = {"active": True, "x": event.pos[0], "y": event.pos[1], "item": item, "options": options}
            pygame.display.flip()
        elif app_state == "PLAYING":
            # Check for Death State
            player = next((e for e in map_data.get("entities", []) if e["type"] == "player"), None)
            if player and player.get("hp", 0) <= 0:
                print("\n[DEAD] CAPTAIN JAX HAS DIED. THE DRIFT CLAIMS ANOTHER. [DEAD]")
                app_state = "GAME_OVER"
                continue

            draw_tactical_screen(map_data, cam_x, cam_y)
            cam_x, cam_y = get_camera_offset(map_data)
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE: app_state = "MAIN_MENU"
                    elif event.key == pygame.K_c: app_state = "CHARACTER_SHEET"
                    elif event.key == pygame.K_SPACE: engine.end_player_turn(); map_data = load_map_data(); status_text = "System: Pulse reset."
                    else:
                        if player and "dead" not in player.get("tags", []):
                            px, py = player["pos"]
                            if event.key in [pygame.K_w, pygame.K_UP]: attempt_move(px, py - 1, map_data)
                            elif event.key in [pygame.K_s, pygame.K_DOWN]: attempt_move(px, py + 1, map_data)
                            elif event.key in [pygame.K_a, pygame.K_LEFT]: attempt_move(px - 1, py, map_data)
                            elif event.key in [pygame.K_d, pygame.K_RIGHT]: attempt_move(px + 1, py, map_data)
                            map_data = load_map_data()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = event.pos; gx, gy = (mx // CELL_SIZE) + cam_x, (my // CELL_SIZE) + cam_y
                    ents = [e for e in map_data.get("entities", []) if e["pos"] == [gx, gy]]; clicked_entity = None
                    # PRIORITIZE LIVING HOSTILES
                    clicked_entity = next((e for e in ents if e.get("type") == "hostile" and "dead" not in e.get("tags", [])), None)
                    if not clicked_entity: clicked_entity = next((e for e in ents if e.get("type") == "npc" and "dead" not in e.get("tags", [])), None)
                    if not clicked_entity: clicked_entity = next((e for e in ents if e.get("type") == "player"), None)
                    if not clicked_entity: clicked_entity = next((e for e in ents if "dead" in e.get("tags", [])), None)
                    if not clicked_entity: clicked_entity = next((e for e in ents if e.get("type") == "prop"), None)
                    if not clicked_entity and ents: clicked_entity = ents[0]
                    if player and "dead" in player.get("tags", []): continue
                    if event.button == 1:
                        if context_menu["active"]:
                            mw, oh, hh = 180, 30, 30; mr = pygame.Rect(context_menu["x"], context_menu["y"], mw, (len(context_menu["options"]) * oh) + hh)
                            if mr.collidepoint(mx, my):
                                if my > context_menu["y"] + hh:
                                    idx = (my - (context_menu["y"] + hh)) // oh
                                    if idx < len(context_menu["options"]):
                                        sel = context_menu["options"][idx]
                                        if sel == "More Actions...": context_menu["page"] = "more"; target = next((e for e in map_data["entities"] if e.get("id") == context_menu["target_id"]), None); context_menu["options"] = generate_menu_options(target, player, "more"); continue
                                        elif sel == "Back": context_menu["page"] = "main"; target = next((e for e in map_data["entities"] if e.get("id") == context_menu["target_id"]), None); context_menu["options"] = generate_menu_options(target, player, "main"); continue
                                        if sel != "Cancel":
                                            status_text = f"System: {sel}..."; draw_tactical_screen(map_data, cam_x, cam_y); pygame.display.flip()
                                            if sel in ["Loot", "Open"]: engine.execute_loot("char_01", context_menu["target_id"])
                                            elif sel == "Attack": engine.execute_attack("char_01", context_menu["target_id"])
                                            elif sel == "Examine": engine.execute_examine("char_01", context_menu["target_id"])
                                            elif sel == "Move Here": attempt_move(context_menu["target_pos"][0], context_menu["target_pos"][1], map_data)
                                            elif sel == "Examine Area": engine.execute_examine_area("char_01", context_menu["target_pos"][0], context_menu["target_pos"][1])
                                            elif sel == "Examine Self": engine.execute_examine("char_01", "char_01")
                                            elif sel.startswith("["): engine.execute_stat_action("char_01", context_menu["target_id"], sel)
                                            map_data = load_map_data()
                                            if sel not in ["Move Here", "Cancel", "Loot", "Open"] and not sel.startswith("["): threading.Thread(target=trigger_narration, daemon=True).start()
                            context_menu["active"] = False; continue
                        elif my < WINDOW_HEIGHT - UI_HEIGHT:
                            if clicked_entity and "hostile" in clicked_entity.get("tags", []) and "dead" not in clicked_entity.get("tags", []):
                                status_text = "System: Attacking..."; draw_tactical_screen(map_data, cam_x, cam_y); pygame.display.flip()
                                res = engine.execute_attack("char_01", clicked_entity.get("id", clicked_entity["name"]))
                                map_data = load_map_data()
                                # ONLY NARRATE IF ACTION SUCCEEDED
                                if "No stamina beats" not in res and "Not enough stamina" not in res:
                                    threading.Thread(target=trigger_narration, daemon=True).start()
                            elif not clicked_entity: attempt_move(gx, gy, map_data); map_data = load_map_data()
                    elif event.button == 3:
                        if my < WINDOW_HEIGHT - UI_HEIGHT: context_menu["active"] = True; context_menu["x"], context_menu["y"] = mx, my; context_menu["page"] = "main"; context_menu["target_pos"] = [gx, gy]; context_menu["target_name"] = clicked_entity["name"] if clicked_entity else None; context_menu["target_id"] = clicked_entity.get("id", clicked_entity["name"]) if clicked_entity else None; context_menu["options"] = generate_menu_options(clicked_entity, player, "main")
            mx, my = pygame.mouse.get_pos()
            if not context_menu["active"] and my < WINDOW_HEIGHT - UI_HEIGHT:
                hgx, hgy = (mx // CELL_SIZE) + cam_x, (my // CELL_SIZE) + cam_y; ents = [e for e in map_data.get("entities", []) if e["pos"] == [hgx, hgy]]; hovered = None
                for pt in ["player", "hostile", "npc"]:
                    if not hovered: hovered = next((e for e in ents if e.get("type") == pt), None)
                if not hovered: hovered = next((e for e in ents if "dead" in e.get("tags", [])), None)
                if not hovered: hovered = next((e for e in ents if e.get("type") == "prop"), None)
                if hovered: ui_manager.draw_hover_tooltip(screen, hovered, (mx, my), font, COLORS)
            pygame.display.flip()
        elif app_state == "TRANSITION_PROMPT":
            draw_tactical_screen(map_data, cam_x, cam_y); by, bn = draw_transition_prompt()
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if by.collidepoint(event.pos): engine.execute_transition(transition_target[0], transition_target[1]); map_data = load_map_data(); cam_x, cam_y = get_camera_offset(map_data); status_text = "Director: Entering region."; app_state = "PLAYING"
                    elif bn.collidepoint(event.pos): status_text = "System: Cancelled."; app_state = "PLAYING"
        elif app_state == "GAME_OVER":
            screen.fill((0, 0, 0))
            msg = title_font.render("☠️ GAME OVER ☠️", True, COLORS["hostile"])
            sub = font.render("Captain Jax has returned to the Drift.", True, COLORS["text"])
            tip = font.render("Press ESC to return to Main Menu", True, (100, 100, 100))
            screen.blit(msg, msg.get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 - 40)))
            screen.blit(sub, sub.get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 + 10)))
            screen.blit(tip, tip.get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 + 50)))
            pygame.display.flip()
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: app_state = "MAIN_MENU"
        clock.tick(30)

if __name__ == "__main__":
    main()
