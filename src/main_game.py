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

class OstrakaGame:
    def __init__(self):
        pygame.init()
        self.CELL_SIZE = 40  
        self.GRID_WIDTH = 20  
        self.GRID_HEIGHT = 15 
        self.UI_HEIGHT = 180 
        self.LOG_WIDTH = 350
        self.WINDOW_WIDTH = (self.CELL_SIZE * self.GRID_WIDTH) + self.LOG_WIDTH
        self.WINDOW_HEIGHT = self.CELL_SIZE * self.GRID_HEIGHT + self.UI_HEIGHT 

        self.screen = pygame.display.set_mode((self.WINDOW_WIDTH, self.WINDOW_HEIGHT))
        pygame.display.set_caption("Ostraka: Aether & Iron (Async Engine)")

        self.COLORS = {
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

        self.font = pygame.font.SysFont("consolas", 16)
        self.icon_font = pygame.font.SysFont("consolas", 20, bold=True)
        self.title_font = pygame.font.SysFont("consolas", 36, bold=True)

        # Global State
        self.app_state = "MAIN_MENU"
        self.status_text = "System Online. Async Loop Running."
        self.transition_target = None
        self.map_data = {"entities": [], "meta": {}}
        self.context_menu = {
            "active": False, "x": 0, "y": 0, 
            "target_name": None, "target_id": None, "target_pos": None, 
            "options": [], "page": "main"
        }

    def load_map_data(self):
        """Reads the state via engine (which uses StateManager/Pydantic now)."""
        state = engine.load_state()
        if "local_map_state" in state:
            md = state["local_map_state"]
            md["meta"] = state.get("meta", {})
            md["combat_log"] = state.get("combat_log", [])
            return md
        return {"entities": [], "meta": {}}

    def get_camera_offset(self, map_data):
        player_pos = [0, 0] 
        map_w, map_h = map_data.get("meta", {}).get("grid_size", [50, 50])
        for e in map_data.get("entities", []):
            if e.type == "player":
                player_pos = e.pos
                break
        cam_x = max(0, min(player_pos[0] - (self.GRID_WIDTH // 2), map_w - self.GRID_WIDTH))
        cam_y = max(0, min(player_pos[1] - (self.GRID_HEIGHT // 2), map_h - self.GRID_HEIGHT))
        return cam_x, cam_y

    def draw_grid(self):
        map_width = self.WINDOW_WIDTH - self.LOG_WIDTH
        for x in range(0, map_width + 1, self.CELL_SIZE): 
            pygame.draw.line(self.screen, self.COLORS["grid"], (x, 0), (x, self.WINDOW_HEIGHT - self.UI_HEIGHT))
        for y in range(0, self.WINDOW_HEIGHT - self.UI_HEIGHT + 1, self.CELL_SIZE): 
            pygame.draw.line(self.screen, self.COLORS["grid"], (0, y), (map_width, y))

    def draw_entities(self, map_data, cam_x, cam_y):
        for entity in map_data.get("entities", []):
            grid_x = entity.pos[0] - cam_x
            grid_y = entity.pos[1] - cam_y
            if 0 <= grid_x < self.GRID_WIDTH and 0 <= grid_y < self.GRID_HEIGHT:
                pixel_x, pixel_y = grid_x * self.CELL_SIZE, grid_y * self.CELL_SIZE
                tags = entity.tags
                ent_type = entity.type
                color = self.COLORS.get(ent_type, (150, 150, 150))
                
                if "water" in tags: color = self.COLORS["water"]
                elif "plant" in tags: color = self.COLORS["plant"]
                elif "wood" in tags: color = self.COLORS["wood"]
                elif "stone" in tags: color = self.COLORS["stone"]
                elif "cold" in tags: color = self.COLORS["cold"]
                if "wall" in tags: color = self.COLORS["wall"]
                if "terrain" in tags or ent_type == "terrain": color = self.COLORS["terrain"]
                if ent_type == "npc": color = self.COLORS["npc"]
                if ent_type == "hostile": color = self.COLORS["hostile"]
                if ent_type == "player": color = self.COLORS["player"]
                if "dead" in tags: color = self.COLORS["dead"]
                
                pygame.draw.rect(self.screen, color, (pixel_x + 2, pixel_y + 2, self.CELL_SIZE - 4, self.CELL_SIZE - 4))
                if ent_type != "terrain" and "dead" not in tags:
                    initial = "@" if ent_type == "player" else entity.name[0].upper()
                    text_surf = self.icon_font.render(initial, True, (255, 255, 255))
                    self.screen.blit(text_surf, text_surf.get_rect(center=(pixel_x + self.CELL_SIZE // 2, pixel_y + self.CELL_SIZE // 2)))

    def draw_context_menu(self):
        if not self.context_menu["active"]: return
        mx, my = pygame.mouse.get_pos(); mw, oh, hh = 180, 30, 30; opts = self.context_menu["options"]
        mr = pygame.Rect(self.context_menu["x"], self.context_menu["y"], mw, (len(opts) * oh) + hh)
        pygame.draw.rect(self.screen, self.COLORS["menu_bg"], mr); pygame.draw.rect(self.screen, self.COLORS["menu_border"], mr, 2)
        title = self.context_menu["target_name"] if self.context_menu["target_name"] else "Location"
        self.screen.blit(self.font.render(title, True, self.COLORS["title"]), (mr.x + 10, mr.y + 5))
        pygame.draw.line(self.screen, self.COLORS["menu_border"], (mr.x, mr.y + hh), (mr.right, mr.y + hh), 1)
        for i, opt in enumerate(opts):
            opt_rect = pygame.Rect(mr.x, mr.y + hh + (i * oh), mw, oh)
            if opt_rect.collidepoint(mx, my): pygame.draw.rect(self.screen, self.COLORS["menu_hover"], opt_rect)
            self.screen.blit(self.font.render(opt, True, self.COLORS["text"]), (opt_rect.x + 10, opt_rect.y + 5))

    def generate_menu_options(self, target, player, map_data, page="main"):
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

    async def trigger_narration(self):
        self.status_text = "Director: [Thinking...]"
        new_text = await narrator.generate_flavor_text()
        self.status_text = f"Director: {new_text}"

    async def start_game(self):
        clock = pygame.time.Clock()
        self.map_data = self.load_map_data()
        log_rect = pygame.Rect(self.WINDOW_WIDTH - self.LOG_WIDTH, 0, self.LOG_WIDTH, self.WINDOW_HEIGHT - self.UI_HEIGHT)
        
        while True:
            mx, my = pygame.mouse.get_pos()
            cam_x, cam_y = self.get_camera_offset(self.map_data)
            
            # --- RENDER LOGIC ---
            if self.app_state == "MAIN_MENU":
                self.screen.fill(self.COLORS["bg"])
                title_surf = self.title_font.render("SHATTERLANDS", True, self.COLORS["title"])
                self.screen.blit(title_surf, title_surf.get_rect(center=(self.WINDOW_WIDTH // 2, self.WINDOW_HEIGHT // 4)))
                bx = (self.WINDOW_WIDTH // 2) - 100
                btns = [
                    {"rect": pygame.Rect(bx, self.WINDOW_HEIGHT // 2, 200, 50), "text": "New Game", "action": "NEW_GAME"},
                    {"rect": pygame.Rect(bx, self.WINDOW_HEIGHT // 2 + 70, 200, 50), "text": "Continue", "action": "LOAD_GAME"},
                    {"rect": pygame.Rect(bx, self.WINDOW_HEIGHT // 2 + 140, 200, 50), "text": "Quit", "action": "QUIT"}
                ]
                for btn in btns:
                    pygame.draw.rect(self.screen, self.COLORS["menu_hover"] if btn["rect"].collidepoint(mx, my) else self.COLORS["menu_bg"], btn["rect"])
                    pygame.draw.rect(self.screen, self.COLORS["menu_border"], btn["rect"], 2)
                    text_surf = self.font.render(btn["text"], True, self.COLORS["text"])
                    self.screen.blit(text_surf, text_surf.get_rect(center=btn["rect"].center))

            elif self.app_state == "CHARACTER_SHEET":
                self.draw_tactical_screen_base(self.map_data, cam_x, cam_y)
                clickable_zones = ui_manager.draw_multi_tab_menu(self.screen, self.map_data, self.font, self.title_font, self.COLORS, self.WINDOW_WIDTH, self.WINDOW_HEIGHT)

            elif self.app_state == "PLAYING":
                self.draw_tactical_screen_base(self.map_data, cam_x, cam_y)
                ui_manager.draw_combat_log(self.screen, self.map_data, log_rect, self.font, self.title_font, self.COLORS)
                if my < self.WINDOW_HEIGHT - self.UI_HEIGHT and not self.context_menu["active"] and not log_rect.collidepoint(mx, my):
                    gx, gy = (mx // self.CELL_SIZE) + cam_x, (my // self.CELL_SIZE) + cam_y
                    hovered = next((e for e in self.map_data.get("entities", []) if e.pos == [gx, gy]), None)
                    if hovered: ui_manager.draw_hover_tooltip(self.screen, hovered, (mx, my), self.font, self.COLORS)

            elif self.app_state == "TRANSITION_PROMPT":
                self.draw_tactical_screen_base(self.map_data, cam_x, cam_y)
                by, bn = self.draw_transition_prompt_ui()

            elif self.app_state == "GAME_OVER":
                self.screen.fill((0, 0, 0))
                msg = self.title_font.render("\u2620\ufe0f GAME OVER \u2620\ufe0f", True, self.COLORS["hostile"])
                self.screen.blit(msg, msg.get_rect(center=(self.WINDOW_WIDTH//2, self.WINDOW_HEIGHT//2 - 40)))

            # --- EVENT LOGIC ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                
                if self.app_state == "MAIN_MENU":
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        for btn in btns:
                            if btn["rect"].collidepoint(event.pos):
                                if btn["action"] == "NEW_GAME": 
                                    engine.start_new_game(); self.map_data = self.load_map_data(); self.status_text = "Director: A new journey."; self.app_state = "PLAYING"
                                elif btn["action"] == "LOAD_GAME": 
                                    self.map_data = self.load_map_data(); self.status_text = "Director: Welcome back."; self.app_state = "PLAYING"
                                elif btn["action"] == "QUIT": pygame.quit(); sys.exit()
                
                elif self.app_state == "CHARACTER_SHEET":
                    player = next((e for e in self.map_data.get("entities", []) if e.type == "player"), None)
                    p_id = player.id if player else None
                    if event.type == pygame.KEYDOWN and event.key in [pygame.K_c, pygame.K_ESCAPE]: self.app_state = "PLAYING"
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        if event.button == 1:
                            for zone in clickable_zones:
                                if zone["rect"].collidepoint(event.pos):
                                    if zone["action"] == "switch_tab": ui_manager.UI_STATE["active_tab"] = zone["target"]
                                    elif zone["action"] == "unequip": engine.execute_unequip(p_id, zone["slot"]); self.map_data = self.load_map_data()
                                    elif zone["action"] == "context_action":
                                        if zone["choice"] == "Equip": engine.execute_equip(p_id, zone["item"])
                                        elif zone["choice"] == "Drop": engine.execute_drop(p_id, zone["item"])
                                        elif zone["choice"] == "Use": engine.execute_use(p_id, zone["item"])
                                        ui_manager.UI_STATE["context_menu"]["active"] = False; self.map_data = self.load_map_data()
                
                elif self.app_state == "PLAYING":
                    player = next((e for e in self.map_data.get("entities", []) if e.type == "player"), None)
                    p_id = player.id if player else None
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE: self.app_state = "MAIN_MENU"
                        elif event.key == pygame.K_c: self.app_state = "CHARACTER_SHEET"
                        elif event.key == pygame.K_SPACE: engine.end_player_turn(); self.map_data = self.load_map_data(); self.status_text = "System: Pulse reset."
                        elif player and "dead" not in player.tags:
                            px, py = player.pos
                            if event.key in [pygame.K_w, pygame.K_UP]: self.attempt_player_move(p_id, px, py - 1)
                            elif event.key in [pygame.K_s, pygame.K_DOWN]: self.attempt_player_move(p_id, px, py + 1)
                            elif event.key in [pygame.K_a, pygame.K_LEFT]: self.attempt_player_move(p_id, px - 1, py)
                            elif event.key in [pygame.K_d, pygame.K_RIGHT]: self.attempt_player_move(p_id, px + 1, py)
                            self.map_data = self.load_map_data()
                    
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        mx, my = event.pos
                        if log_rect.collidepoint(mx, my): continue 
                        gx, gy = (mx // self.CELL_SIZE) + cam_x, (my // self.CELL_SIZE) + cam_y
                        ents = [e for e in self.map_data.get("entities", []) if e.pos == [gx, gy]]
                        clicked_entity = next((e for e in ents if e.type in ["hostile", "npc", "player"] and "dead" not in e.tags), None)
                        if not clicked_entity and ents: clicked_entity = ents[0]
                        
                        if event.button == 1:
                            if self.context_menu["active"]:
                                mw, oh, hh = 180, 30, 30; mr = pygame.Rect(self.context_menu["x"], self.context_menu["y"], mw, (len(self.context_menu["options"]) * oh) + hh)
                                if mr.collidepoint(mx, my):
                                    if my > self.context_menu["y"] + hh:
                                        idx = (my - (self.context_menu["y"] + hh)) // oh
                                        if idx < len(self.context_menu["options"]):
                                            await self.handle_menu_selection(self.context_menu["options"][idx], p_id, self.context_menu["target_id"], self.context_menu["target_pos"])
                                self.context_menu["active"] = False
                            elif my < self.WINDOW_HEIGHT - self.UI_HEIGHT:
                                if clicked_entity and "hostile" in clicked_entity.tags and "dead" not in clicked_entity.tags:
                                    await self.handle_menu_selection("Attack", p_id, clicked_entity.id, [gx, gy])
                                elif not clicked_entity: self.attempt_player_move(p_id, gx, gy)
                        elif event.button == 3:
                            if my < self.WINDOW_HEIGHT - self.UI_HEIGHT:
                                self.context_menu["active"] = True; self.context_menu["x"], self.context_menu["y"] = mx, my; self.context_menu["page"] = "main"; self.context_menu["target_pos"] = [gx, gy]
                                self.context_menu["target_name"] = clicked_entity.name if clicked_entity else None
                                self.context_menu["target_id"] = clicked_entity.id if clicked_entity else None
                                self.context_menu["options"] = self.generate_menu_options(clicked_entity, player, self.map_data, "main")

                elif self.app_state == "TRANSITION_PROMPT":
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        by, bn = self.draw_transition_prompt_ui()
                        if by.collidepoint(event.pos): 
                            engine.execute_transition(self.transition_target[0], self.transition_target[1])
                            self.map_data = self.load_map_data(); self.app_state = "PLAYING"
                        elif bn.collidepoint(event.pos): self.app_state = "PLAYING"

            pygame.display.flip()
            await asyncio.sleep(0.016) # ~60 FPS

    def draw_tactical_screen_base(self, map_data, cam_x, cam_y):
        self.screen.fill(self.COLORS["bg"]); self.draw_grid(); self.draw_entities(map_data, cam_x, cam_y); self.draw_context_menu()
        campaign = map_data.get("meta", {}).get("campaign_tracker", {})
        if campaign.get("active_subplot"):
            ui_manager.draw_text(self.screen, f"OBJECTIVE: {campaign['active_subplot']}", 20, 20, self.font, self.COLORS["gold"])
        pygame.draw.rect(self.screen, self.COLORS["ui_bg"], (0, self.WINDOW_HEIGHT - self.UI_HEIGHT, self.WINDOW_WIDTH, self.UI_HEIGHT))
        pygame.draw.line(self.screen, (100, 100, 100), (0, self.WINDOW_HEIGHT - self.UI_HEIGHT), (self.WINDOW_WIDTH, self.WINDOW_HEIGHT - self.UI_HEIGHT), 2)
        ui_manager.draw_text_wrapped(self.screen, self.status_text, self.COLORS["text"], pygame.Rect(15, self.WINDOW_HEIGHT - self.UI_HEIGHT + 15, (self.WINDOW_WIDTH - self.LOG_WIDTH) - 30, self.UI_HEIGHT - 30), self.font)
        player = next((e for e in map_data.get("entities", []) if e.type == "player"), None)
        if player:
            vitals_x = (self.WINDOW_WIDTH - self.LOG_WIDTH) - 420
            self.screen.blit(self.font.render(f"JAX: HP {player.hp}/{player.max_hp}", True, self.COLORS["title"]), (vitals_x, self.WINDOW_HEIGHT - self.UI_HEIGHT + 15))
            self.screen.blit(self.font.render(f"STAMINA: {player.resources.stamina}", True, self.COLORS["stamina"]), (vitals_x + 180, self.WINDOW_HEIGHT - self.UI_HEIGHT + 15))
            self.screen.blit(self.font.render(f"FOCUS: {player.resources.focus}", True, self.COLORS["focus"]), (vitals_x + 300, self.WINDOW_HEIGHT - self.UI_HEIGHT + 15))

    def draw_transition_prompt_ui(self):
        pr = pygame.Rect((self.WINDOW_WIDTH - 300)//2, (self.WINDOW_HEIGHT - 150)//2, 300, 150)
        pygame.draw.rect(self.screen, self.COLORS["menu_bg"], pr); pygame.draw.rect(self.screen, self.COLORS["menu_border"], pr, 2)
        text_surf = self.font.render("Travel to a new region?", True, self.COLORS["text"])
        self.screen.blit(text_surf, text_surf.get_rect(center=(self.WINDOW_WIDTH//2, self.WINDOW_HEIGHT//2 - 30)))
        by, bn = pygame.Rect(self.WINDOW_WIDTH//2 - 90, self.WINDOW_HEIGHT//2 + 10, 80, 40), pygame.Rect(self.WINDOW_WIDTH//2 + 10, self.WINDOW_HEIGHT//2 + 10, 80, 40)
        return by, bn

    def attempt_player_move(self, p_id, gx, gy):
        gw, gh = self.map_data.get("meta", {}).get("grid_size", [50, 50])
        if gx <= 0 or gx >= gw - 1 or gy <= 0 or gy >= gh - 1:
            self.app_state = "TRANSITION_PROMPT"; self.transition_target = [gx, gy]
        else:
            res = engine.execute_move(p_id, gx, gy)
            self.status_text = f"System: {res}"; self.map_data = self.load_map_data()

    async def handle_menu_selection(self, sel, p_id, t_id, t_pos):
        if sel == "Cancel": return
        self.status_text = f"System: {sel}..."; res = ""
        if sel == "More Actions...": self.context_menu["page"] = "more"; return 
        if sel == "Attack": res = engine.execute_attack(p_id, t_id)
        elif sel == "Loot": res = engine.execute_loot(p_id, t_id)
        elif sel == "Move Here": res = engine.execute_move(p_id, t_pos[0], t_pos[1])
        elif sel == "[Investigate]": 
            self.status_text = "Director: [Analyzing Seed...]"
            res = await engine.investigate_seed(p_id, t_id)
        elif sel.startswith("["): res = engine.execute_stat_action(p_id, t_id, sel)
        
        self.status_text = f"System: {res}"; self.map_data = self.load_map_data()
        if "No" not in res and "Exhausted" not in res:
            await self.trigger_narration()

def main():
    game = OstrakaGame()
    asyncio.run(game.start_game())

if __name__ == "__main__":
    main()
