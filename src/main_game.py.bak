import pygame
import sys
import json
import asyncio
import os

# Internal imports
import engine
import narrator
import entities
import ui_manager
import actions
from entities import Entity

pygame.init()

CELL_SIZE = 40  
GRID_WIDTH = 20  
GRID_HEIGHT = 15 
UI_HEIGHT = 180 
LOG_WIDTH = 350
WINDOW_WIDTH = (CELL_SIZE * GRID_WIDTH) + LOG_WIDTH
WINDOW_HEIGHT = CELL_SIZE * GRID_HEIGHT + UI_HEIGHT 

screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Ostraka: Aether & Iron (Async)")

COLORS = {
    "bg": (20, 25, 25), "grid": (40, 45, 45),
    "player": (50, 150, 255), "hostile": (220, 50, 50), "npc": (200, 180, 50),
    "dead": (100, 20, 20), "terrain": (60, 65, 65), "wall": (100, 100, 105),
    "wood": (110, 70, 40), "plant": (40, 120, 40), "water": (40, 100, 160),
    "cold": (180, 220, 240), "stone": (90, 90, 90),
    "text": (220, 220, 220), "ui_bg": (15, 15, 20),
    "menu_bg": (40, 40, 50), "menu_hover": (70, 70, 90), "menu_border": (150, 150, 150),
    "title": (255, 215, 0), "stamina": (100, 255, 100), "focus": (200, 100, 255),
    "warning": (255, 200, 0), "danger": (255, 50, 50), "gold": (218, 165, 32)
}

font = pygame.font.SysFont("consolas", 16)
icon_font = pygame.font.SysFont("consolas", 20, bold=True)
title_font = pygame.font.SysFont("consolas", 36, bold=True)

# Global State
app_state = "MAIN_MENU"
status_text = "System Online. Async Loop Running."
transition_target = None
map_data = {"entities": [], "meta": {}}

context_menu = {
    "active": False, "x": 0, "y": 0, 
    "target_name": None, "target_id": None, "target_pos": None, 
    "options": [], "page": "main"
}

def load_map_data():
    """Reads the state via engine (which uses StateManager/Pydantic now)."""
    state = engine.load_state()
    if "local_map_state" in state:
        md = state["local_map_state"]
        # Ensure UI-expected structure
        md["meta"] = state.get("meta", {})
        md["combat_log"] = state.get("combat_log", [])
        return md
    return {"entities": [], "meta": {}}

def get_camera_offset(map_data):
    player_pos = [0, 0] 
    map_w, map_h = map_data.get("meta", {}).get("grid_size", [50, 50])
    for e in map_data.get("entities", []):
        if e.type == "player":
            player_pos = e.pos
            break
    cam_x = max(0, min(player_pos[0] - (GRID_WIDTH // 2), map_w - GRID_WIDTH))
    cam_y = max(0, min(player_pos[1] - (GRID_HEIGHT // 2), map_h - GRID_HEIGHT))
    return cam_x, cam_y

def draw_grid():
    map_width = WINDOW_WIDTH - LOG_WIDTH
    for x in range(0, map_width + 1, CELL_SIZE): pygame.draw.line(screen, COLORS["grid"], (x, 0), (x, WINDOW_HEIGHT - UI_HEIGHT))
    for y in range(0, WINDOW_HEIGHT - UI_HEIGHT + 1, CELL_SIZE): pygame.draw.line(screen, COLORS["grid"], (0, y), (map_width, y))

def draw_entities(map_data, cam_x, cam_y):
    for entity in map_data.get("entities", []):
        grid_x = entity.pos[0] - cam_x
        grid_y = entity.pos[1] - cam_y
        if 0 <= grid_x < GRID_WIDTH and 0 <= grid_y < GRID_HEIGHT:
            pixel_x, pixel_y = grid_x * CELL_SIZE, grid_y * CELL_SIZE
            tags = entity.tags
            ent_type = entity.type
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
                initial = "@" if ent_type == "player" else entity.name[0].upper()
                text_surf = icon_font.render(initial, True, (255, 255, 255))
                screen.blit(text_surf, text_surf.get_rect(center=(pixel_x + CELL_SIZE // 2, pixel_y + CELL_SIZE // 2)))

def draw_context_menu():
    if not context_menu["active"]: return
    mx, my = pygame.mouse.get_pos(); mw, oh, hh = 180, 30, 30; opts = context_menu["options"]
    mr = pygame.Rect(context_menu["x"], context_menu["y"], mw, (len(opts) * oh) + hh)
    pygame.draw.rect(screen, COLORS["menu_bg"], mr); pygame.draw.rect(screen, COLORS["menu_border"], mr, 2)
    title = context_menu["target_name"] if context_menu["target_name"] else "Location"
    screen.blit(font.render(title, True, COLORS["title"]), (mr.x + 10, mr.y + 5))
    pygame.draw.line(screen, COLORS["menu_border"], (mr.x, mr.y + hh), (mr.right, mr.y + hh), 1)
    for i, opt in enumerate(opts):
        opt_rect = pygame.Rect(mr.x, mr.y + hh + (i * oh), mw, oh)
        if opt_rect.collidepoint(mx, my): pygame.draw.rect(screen, COLORS["menu_hover"], opt_rect)
        screen.blit(font.render(opt, True, COLORS["text"]), (opt_rect.x + 10, opt_rect.y + 5))

def generate_menu_options(target, player, map_data, page="main"):
    if not player: return ["Cancel"]
    learned_skills = player.skills
    valid_actions = actions.get_valid_actions(player, target, learned_skills=learned_skills)
    options = []
    if page == "main":
        if not target: options.append("Move Here"); options.append("Examine Area")
        elif target == player: options.append("Examine Self")
        else:
            if "hostile" in target.tags and "dead" not in target.tags: options.append("Attack")
            if "item" in target.tags or "dead" in target.tags: options.append("Loot")
            if "container" in target.tags: options.append("Open")
            if "story_seed" in target.tags: options.append("[Investigate]")
            if any(t in target.tags for t in ["transition_door", "next_room_door", "exit_door", "quest_entrance"]):
                is_combat = map_data.get("meta", {}).get("in_combat", False)
                if not is_combat:
                    if "quest_entrance" in target.tags: options.append("[Enter Quest Location]")
                    else: options.append("[Go Through]" if any(t in target.tags for t in ["transition_door", "next_room_door"]) else "[Exit to Surface]")
            if "building" in target.tags: options.append("[Enter]")
        for skill in learned_skills:
            if skill in valid_actions: options.append(skill)
        stat_actions = []
        for act in valid_actions:
            if act in learned_skills: continue
            best_stat = entities.get_best_stat_for_action(player, act)
            if best_stat: stat_actions.append((act, best_stat, entities.get_stat(player, best_stat)))
        stat_actions.sort(key=lambda x: x[2], reverse=True)
        for i in range(min(2, len(stat_actions))): options.append(f"[{stat_actions[i][1]}] {stat_actions[i][0]}")
        options.append("Examine")
        if len(valid_actions) > 3: options.append("More Actions...")
    elif page == "more":
        for act in valid_actions:
            bs = entities.get_best_stat_for_action(player, act); options.append(f"[{bs}] {act}" if bs else act)
        options.append("Back")
    options.append("Cancel"); seen = set(); return [x for x in options if not (x in seen or seen.add(x))]

async def trigger_narration():
    global status_text
    status_text = "Director: [Thinking...]"
    new_text = await narrator.generate_flavor_text()
    status_text = f"Director: {new_text}"

async def main():
    global status_text, app_state, transition_target, map_data
    clock = pygame.time.Clock()
    map_data = load_map_data()
    log_rect = pygame.Rect(WINDOW_WIDTH - LOG_WIDTH, 0, LOG_WIDTH, WINDOW_HEIGHT - UI_HEIGHT)
    
    while True:
        mx, my = pygame.mouse.get_pos()
        cam_x, cam_y = get_camera_offset(map_data)
        
        # --- RENDER LOGIC ---
        if app_state == "MAIN_MENU":
            screen.fill(COLORS["bg"])
            screen.blit(title_font.render("SHATTERLANDS", True, COLORS["title"]), title_font.render("SHATTERLANDS", True, COLORS["title"]).get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 4)))
            bx = (WINDOW_WIDTH // 2) - 100
            btns = [
                {"rect": pygame.Rect(bx, WINDOW_HEIGHT // 2, 200, 50), "text": "New Game", "action": "NEW_GAME"},
                {"rect": pygame.Rect(bx, WINDOW_HEIGHT // 2 + 70, 200, 50), "text": "Continue", "action": "LOAD_GAME"},
                {"rect": pygame.Rect(bx, WINDOW_HEIGHT // 2 + 140, 200, 50), "text": "Quit", "action": "QUIT"}
            ]
            for btn in btns:
                pygame.draw.rect(screen, COLORS["menu_hover"] if btn["rect"].collidepoint(mx, my) else COLORS["menu_bg"], btn["rect"])
                pygame.draw.rect(screen, COLORS["menu_border"], btn["rect"], 2)
                screen.blit(font.render(btn["text"], True, COLORS["text"]), font.render(btn["text"], True, COLORS["text"]).get_rect(center=btn["rect"].center))

        elif app_state == "CHARACTER_SHEET":
            draw_tactical_screen_base(map_data, cam_x, cam_y)
            clickable_zones = ui_manager.draw_multi_tab_menu(screen, map_data, font, title_font, COLORS, WINDOW_WIDTH, WINDOW_HEIGHT)

        elif app_state == "PLAYING":
            draw_tactical_screen_base(map_data, cam_x, cam_y)
            ui_manager.draw_combat_log(screen, map_data, log_rect, font, title_font, COLORS)
            if my < WINDOW_HEIGHT - UI_HEIGHT and not context_menu["active"] and not log_rect.collidepoint(mx, my):
                gx, gy = (mx // CELL_SIZE) + cam_x, (my // CELL_SIZE) + cam_y
                hovered = next((e for e in map_data.get("entities", []) if e.pos == [gx, gy]), None)
                if hovered: ui_manager.draw_hover_tooltip(screen, hovered, (mx, my), font, COLORS)

        elif app_state == "TRANSITION_PROMPT":
            draw_tactical_screen_base(map_data, cam_x, cam_y)
            by, bn = draw_transition_prompt_ui()

        elif app_state == "GAME_OVER":
            screen.fill((0, 0, 0))
            msg = title_font.render("☠️ GAME OVER ☠️", True, COLORS["hostile"])
            screen.blit(msg, msg.get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 - 40)))

        # --- EVENT LOGIC ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            
            if app_state == "MAIN_MENU":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for btn in btns:
                        if btn["rect"].collidepoint(event.pos):
                            if btn["action"] == "NEW_GAME": engine.start_new_game(); map_data = load_map_data(); status_text = "Director: A new journey."; app_state = "PLAYING"
                            elif btn["action"] == "LOAD_GAME": map_data = load_map_data(); status_text = "Director: Welcome back."; app_state = "PLAYING"
                            elif btn["action"] == "QUIT": pygame.quit(); sys.exit()
            
            elif app_state == "CHARACTER_SHEET":
                player = next((e for e in map_data.get("entities", []) if e.type == "player"), None)
                p_id = player.id if player else None
                if event.type == pygame.KEYDOWN and event.key in [pygame.K_c, pygame.K_ESCAPE]: app_state = "PLAYING"
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        for zone in clickable_zones:
                            if zone["rect"].collidepoint(event.pos):
                                if zone["action"] == "switch_tab": ui_manager.UI_STATE["active_tab"] = zone["target"]
                                elif zone["action"] == "unequip": engine.execute_unequip(p_id, zone["slot"]); map_data = load_map_data()
                                elif zone["action"] == "context_action":
                                    if zone["choice"] == "Equip": engine.execute_equip(p_id, zone["item"])
                                    elif zone["choice"] == "Drop": engine.execute_drop(p_id, zone["item"])
                                    elif zone["choice"] == "Use": engine.execute_use(p_id, zone["item"])
                                    ui_manager.UI_STATE["context_menu"]["active"] = False; map_data = load_map_data()
            
            elif app_state == "PLAYING":
                player = next((e for e in map_data.get("entities", []) if e.type == "player"), None)
                p_id = player.id if player else None
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE: app_state = "MAIN_MENU"
                    elif event.key == pygame.K_c: app_state = "CHARACTER_SHEET"
                    elif event.key == pygame.K_SPACE: engine.end_player_turn(); map_data = load_map_data(); status_text = "System: Pulse reset."
                    elif player and "dead" not in player.tags:
                        px, py = player.pos
                        if event.key in [pygame.K_w, pygame.K_UP]: attempt_player_move(p_id, px, py - 1)
                        elif event.key in [pygame.K_s, pygame.K_DOWN]: attempt_player_move(p_id, px, py + 1)
                        elif event.key in [pygame.K_a, pygame.K_LEFT]: attempt_player_move(p_id, px - 1, py)
                        elif event.key in [pygame.K_d, pygame.K_RIGHT]: attempt_player_move(p_id, px + 1, py)
                        map_data = load_map_data()
                
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = event.pos
                    if log_rect.collidepoint(mx, my): continue 
                    gx, gy = (mx // CELL_SIZE) + cam_x, (my // CELL_SIZE) + cam_y
                    ents = [e for e in map_data.get("entities", []) if e.pos == [gx, gy]]
                    clicked_entity = next((e for e in ents if e.type in ["hostile", "npc", "player"] and "dead" not in e.tags), None)
                    if not clicked_entity and ents: clicked_entity = ents[0]
                    
                    if event.button == 1:
                        if context_menu["active"]:
                            mw, oh, hh = 180, 30, 30; mr = pygame.Rect(context_menu["x"], context_menu["y"], mw, (len(context_menu["options"]) * oh) + hh)
                            if mr.collidepoint(mx, my):
                                if my > context_menu["y"] + hh:
                                    idx = (my - (context_menu["y"] + hh)) // oh
                                    if idx < len(context_menu["options"]):
                                        await handle_menu_selection(context_menu["options"][idx], p_id, context_menu["target_id"], context_menu["target_pos"])
                            context_menu["active"] = False
                        elif my < WINDOW_HEIGHT - UI_HEIGHT:
                            if clicked_entity and "hostile" in clicked_entity.tags and "dead" not in clicked_entity.tags:
                                await handle_menu_selection("Attack", p_id, clicked_entity.id, [gx, gy])
                            elif not clicked_entity: attempt_player_move(p_id, gx, gy)
                    elif event.button == 3:
                        if my < WINDOW_HEIGHT - UI_HEIGHT:
                            context_menu["active"] = True; context_menu["x"], context_menu["y"] = mx, my; context_menu["page"] = "main"; context_menu["target_pos"] = [gx, gy]
                            context_menu["target_name"] = clicked_entity.name if clicked_entity else None
                            context_menu["target_id"] = clicked_entity.id if clicked_entity else None
                            context_menu["options"] = generate_menu_options(clicked_entity, player, map_data, "main")

            elif app_state == "TRANSITION_PROMPT":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    by, bn = draw_transition_prompt_ui()
                    if by.collidepoint(event.pos): engine.execute_transition(transition_target[0], transition_target[1]); map_data = load_map_data(); app_state = "PLAYING"
                    elif bn.collidepoint(event.pos): app_state = "PLAYING"

        pygame.display.flip()
        await asyncio.sleep(0.016) # ~60 FPS

def draw_tactical_screen_base(map_data, cam_x, cam_y):
    screen.fill(COLORS["bg"]); draw_grid(); draw_entities(map_data, cam_x, cam_y); draw_context_menu()
    campaign = map_data.get("meta", {}).get("campaign_tracker", {})
    if campaign.get("active_subplot"):
        ui_manager.draw_text(screen, f"OBJECTIVE: {campaign['active_subplot']}", 20, 20, font, COLORS["gold"])
    pygame.draw.rect(screen, COLORS["ui_bg"], (0, WINDOW_HEIGHT - UI_HEIGHT, WINDOW_WIDTH, UI_HEIGHT))
    pygame.draw.line(screen, (100, 100, 100), (0, WINDOW_HEIGHT - UI_HEIGHT), (WINDOW_WIDTH, WINDOW_HEIGHT - UI_HEIGHT), 2)
    ui_manager.draw_text_wrapped(screen, status_text, COLORS["text"], pygame.Rect(15, WINDOW_HEIGHT - UI_HEIGHT + 15, (WINDOW_WIDTH - LOG_WIDTH) - 30, UI_HEIGHT - 30), font)
    player = next((e for e in map_data.get("entities", []) if e.type == "player"), None)
    if player:
        vitals_x = (WINDOW_WIDTH - LOG_WIDTH) - 420
        screen.blit(font.render(f"JAX: HP {player.hp}/{player.max_hp}", True, COLORS["title"]), (vitals_x, WINDOW_HEIGHT - UI_HEIGHT + 15))
        screen.blit(font.render(f"STAMINA: {player.resources.stamina}", True, COLORS["stamina"]), (vitals_x + 180, WINDOW_HEIGHT - UI_HEIGHT + 15))
        screen.blit(font.render(f"FOCUS: {player.resources.focus}", True, COLORS["focus"]), (vitals_x + 300, WINDOW_HEIGHT - UI_HEIGHT + 15))

def draw_transition_prompt_ui():
    pr = pygame.Rect((WINDOW_WIDTH - 300)//2, (WINDOW_HEIGHT - 150)//2, 300, 150)
    pygame.draw.rect(screen, COLORS["menu_bg"], pr); pygame.draw.rect(screen, COLORS["menu_border"], pr, 2)
    screen.blit(font.render("Travel to a new region?", True, COLORS["text"]), font.render("Travel to a new region?", True, COLORS["text"]).get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 - 30)))
    by, bn = pygame.Rect(WINDOW_WIDTH//2 - 90, WINDOW_HEIGHT//2 + 10, 80, 40), pygame.Rect(WINDOW_WIDTH//2 + 10, WINDOW_HEIGHT//2 + 10, 80, 40)
    return by, bn

def attempt_player_move(p_id, gx, gy):
    global status_text, app_state, transition_target, map_data
    gw, gh = map_data.get("meta", {}).get("grid_size", [50, 50])
    if gx <= 0 or gx >= gw - 1 or gy <= 0 or gy >= gh - 1:
        app_state = "TRANSITION_PROMPT"; transition_target = [gx, gy]
    else:
        res = engine.execute_move(p_id, gx, gy)
        status_text = f"System: {res}"; map_data = load_map_data()

async def handle_menu_selection(sel, p_id, t_id, t_pos):
    global status_text, map_data
    if sel == "Cancel": return
    status_text = f"System: {sel}..."; res = ""
    if sel == "More Actions...": context_menu["page"] = "more"; return 
    if sel == "Attack": res = engine.execute_attack(p_id, t_id)
    elif sel == "Loot": res = engine.execute_loot(p_id, t_id)
    elif sel == "Move Here": res = engine.execute_move(p_id, t_pos[0], t_pos[1])
    elif sel == "[Investigate]": 
        status_text = "Director: [Analyzing Seed...]"
        res = engine.investigate_seed(p_id, t_id)
    elif sel.startswith("["): res = engine.execute_stat_action(p_id, t_id, sel)
    
    status_text = f"System: {res}"; map_data = load_map_data()
    if "No" not in res and "Exhausted" not in res:
        await trigger_narration()

if __name__ == "__main__":
    asyncio.run(main())
