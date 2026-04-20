import pygame
import sys
import json
import asyncio
import os
import heapq
from typing import List, Dict, Any, Tuple, Optional

# Internal imports
import engine
import narrator
import entities
import ui_manager
import actions

class OstrakaGame:
    """
    The main application class for Ostraka: Aether & Iron.
    """
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
        pygame.display.set_caption("Ostraka: Aether & Iron (Iceberg Weaver Active)")

        self.COLORS = {
            "bg": (20, 25, 25), "grid": (40, 45, 45),
            "player": (50, 150, 255), "hostile": (220, 50, 50), "npc": (200, 180, 50),
            "dead": (100, 20, 20), "terrain": (60, 65, 65), "wall": (100, 100, 105),
            "wood": (110, 70, 40), "plant": (40, 120, 40), "water": (40, 100, 160),
            "cold": (180, 220, 240), "stone": (90, 90, 90),
            "text": (220, 220, 220), "ui_bg": (15, 15, 20),
            "menu_bg": (30, 35, 40), "menu_hover": (60, 70, 80), "menu_border": (120, 130, 140),
            "title": (255, 215, 0), "stamina": (100, 255, 100), "focus": (200, 100, 255),
            "warning": (255, 200, 0), "danger": (255, 50, 50), "gold": (218, 165, 32)
        }

        self.font = pygame.font.SysFont("consolas", 16)
        self.icon_font = pygame.font.SysFont("consolas", 20, bold=True)
        self.title_font = pygame.font.SysFont("consolas", 36, bold=True)

        self.app_state = "MAIN_MENU"
        self.status_text = "System Online. Iceberg Weaver Ready."
        self.transition_target: Optional[List[int]] = None
        self.map_data: Dict[str, Any] = {"entities": [], "meta": {}}
        
        # Character Creation transient state
        self.char_build = {
            "stage": 0, # 0: Kingdom, 1: SubType, 2: Genetic Variation (Size/Exp), 3: Skill Tracks, 4: Finalize
            "name": "Jax",
            "kingdom": "Mammals",
            "sub_type": "T1",
            "size_shift": "NONE",
            "exp": {"Might": 0, "Logic": 0, "Endurance": 0, "Knowledge": 0, "Finesse": 0, "Awareness": 0, "Reflexes": 0, "Intuition": 0, "Vitality": 0, "Charm": 0, "Fortitude": 0, "Willpower": 0},
            "tracks": [],
            "points_body": 3,
            "points_mind": 3
        }
        
        self.move_queue: List[Tuple[int, int]] = []
        self.is_animating = False
        self.anim_timer = 0
        self.step_delay = 4 
        
    async def load_map_data(self) -> Dict[str, Any]:
        """Retrieves serialized map data asynchronously."""
        state = await engine.load_state()
        if "local_map_state" in state:
            md = state["local_map_state"]
            
            # NORMALIZATION: Ensure all entities are plain dicts for the UI layer
            raw_entities = md.get("entities", [])
            normalized = []
            for e in raw_entities:
                if hasattr(e, "model_dump"):
                    normalized.append(e.model_dump())
                elif hasattr(e, "__dict__") and not isinstance(e, dict):
                    normalized.append(dict(e))
                else:
                    normalized.append(e)
            md["entities"] = normalized

            md["meta"] = state.get("meta", {})
            md["combat_log"] = state.get("combat_log", [])
            return md
        return {"entities": [], "meta": {}}

    def get_camera_offset(self, map_data: Dict[str, Any]) -> Tuple[int, int]:
        player_pos = [0, 0] 
        map_w, map_h = map_data.get("meta", {}).get("grid_size", [100, 100])
        for e in map_data.get("entities", []):
            if e.get("type") == "player":
                player_pos = e.get("pos", [0,0])
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

    def draw_entities(self, map_data: Dict[str, Any], cam_x: int, cam_y: int):
        for entity in map_data.get("entities", []):
            pos = entity.get("pos", [0,0])
            grid_x = pos[0] - cam_x
            grid_y = pos[1] - cam_y
            if 0 <= grid_x < self.GRID_WIDTH and 0 <= grid_y < self.GRID_HEIGHT:
                pixel_x, pixel_y = grid_x * self.CELL_SIZE, grid_y * self.CELL_SIZE
                tags = entity.get("tags", [])
                ent_type = entity.get("type", "terrain")
                color = self.COLORS.get(ent_type, (150, 150, 150))
                
                if "water" in tags: color = self.COLORS["water"]
                elif "plant" in tags: color = self.COLORS["plant"]
                elif "wall" in tags: color = self.COLORS["wall"]
                if ent_type == "npc": color = self.COLORS["npc"]
                if ent_type == "hostile": color = self.COLORS["hostile"]
                if ent_type == "player": color = self.COLORS["player"]
                if "dead" in tags: color = self.COLORS["dead"]
                
                pygame.draw.rect(self.screen, color, (pixel_x + 2, pixel_y + 2, self.CELL_SIZE - 4, self.CELL_SIZE - 4))
                if ent_type != "terrain" and "dead" not in tags:
                    name = entity.get("name", "Unknown")
                    icons = {"player": "👤", "Coyote": "🐺", "Fauna Field Hare": "🐇", "Flora Iron Wheat": "🌾", "Scrap Heap": "📦", "bandit": "👤"}
                    symbol = icons.get("player" if ent_type == "player" else name, name[0].upper())
                    text_surf = self.icon_font.render(symbol, True, (255, 255, 255))
                    self.screen.blit(text_surf, text_surf.get_rect(center=(pixel_x + self.CELL_SIZE // 2, pixel_y + self.CELL_SIZE // 2)))

    async def start_game(self):
        clock = pygame.time.Clock()
        self.map_data = await self.load_map_data()
        log_rect = pygame.Rect(self.WINDOW_WIDTH - self.LOG_WIDTH, 0, self.LOG_WIDTH, self.WINDOW_HEIGHT - self.UI_HEIGHT)
        
        while True:
            mx, my = pygame.mouse.get_pos()
            cam_x, cam_y = self.get_camera_offset(self.map_data)
            
            if self.app_state == "MAIN_MENU":
                btns = self.draw_main_menu_ui(mx, my)
            elif self.app_state == "CHARACTER_CREATOR":
                creator_btns = self.draw_character_creator_ui(mx, my)
            elif self.app_state == "CHARACTER_SHEET":
                self.draw_tactical_screen_base(self.map_data, cam_x, cam_y)
                clickable_zones = ui_manager.draw_multi_tab_menu(self.screen, self.map_data, self.font, self.title_font, self.COLORS, self.WINDOW_WIDTH, self.WINDOW_HEIGHT)
            elif self.app_state == "PLAYING":
                self.draw_tactical_screen_base(self.map_data, cam_x, cam_y)
                ui_manager.draw_combat_log(self.screen, self.map_data, log_rect, self.font, self.title_font, self.COLORS)
                
                ctx = ui_manager.UI_STATE["context_menu"]
                if my < self.WINDOW_HEIGHT - self.UI_HEIGHT and not ctx["active"] and mx < self.WINDOW_WIDTH - self.LOG_WIDTH:
                    gx, gy = (mx // self.CELL_SIZE) + cam_x, (my // self.CELL_SIZE) + cam_y
                    hovered = next((e for e in self.map_data.get("entities", []) if e.get("pos") == [gx, gy]), None)
                    if hovered: ui_manager.draw_hover_tooltip(self.screen, hovered, (mx, my), self.font, self.COLORS)
                
                ui_manager.draw_context_menu(self.screen, self.font, self.COLORS, self.WINDOW_WIDTH, self.WINDOW_HEIGHT)

            elif self.app_state == "TRANSITION_PROMPT":
                self.draw_tactical_screen_base(self.map_data, cam_x, cam_y)
                by, bn = self.draw_transition_prompt_ui()

            elif self.app_state == "GAME_OVER":
                self.screen.fill((0, 0, 0))
                msg = self.title_font.render("\u2620\ufe0f GAME OVER \u2620\ufe0f", True, self.COLORS["hostile"])
                self.screen.blit(msg, msg.get_rect(center=(self.WINDOW_WIDTH//2, self.WINDOW_HEIGHT//2 - 40)))

            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                
                if self.app_state == "MAIN_MENU":
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        for btn in btns:
                            if btn["rect"].collidepoint(event.pos):
                                if btn["action"] == "CHARACTER_CREATOR": 
                                    self.app_state = "CHARACTER_CREATOR"
                                elif btn["action"] == "LOAD_GAME": 
                                    self.map_data = await self.load_map_data(); self.app_state = "PLAYING"
                                elif btn["action"] == "QUIT": pygame.quit(); sys.exit()

                elif self.app_state == "CHARACTER_CREATOR":
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        # Stage-specific buttons
                        active = creator_btns
                        for b in active["kingdoms"]:
                            if b["rect"].collidepoint(event.pos): self.char_build["kingdom"] = b["val"]
                        
                        for b in active["subtypes"]:
                            if b["rect"].collidepoint(event.pos): self.char_build["sub_type"] = b["val"]
                        
                        for b in active["variation"]:
                            if b["rect"].collidepoint(event.pos):
                                if b["action"] == "set_size": self.char_build["size_shift"] = b["val"]
                                elif b["action"] == "add_exp":
                                    p_key = b["p_key"]
                                    if self.char_build[p_key] > 0:
                                        self.char_build["exp"][b["val"]] += 1
                                        self.char_build[p_key] -= 1
                        
                        for b in active["tracks"]:
                            if b["rect"].collidepoint(event.pos):
                                t = b["val"]
                                if t in self.char_build["tracks"]: self.char_build["tracks"].remove(t)
                                elif len(self.char_build["tracks"]) < 6: self.char_build["tracks"].append(t)
                        
                        for b in active["nav"]:
                            if b["rect"].collidepoint(event.pos):
                                if b["action"] == "next_stage":
                                    if self.char_build["stage"] < 4: self.char_build["stage"] += 1
                                    else:
                                        # Finalize and start
                                        await engine.start_new_game(self.char_build)
                                        self.map_data = await self.load_map_data()
                                        self.app_state = "PLAYING"
                                elif b["action"] == "prev_stage":
                                    self.char_build["stage"] = max(0, self.char_build["stage"] - 1)

                elif self.app_state == "CHARACTER_SHEET":
                    if event.type == pygame.KEYDOWN and event.key in [pygame.K_c, pygame.K_ESCAPE]: self.app_state = "PLAYING"
                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        for zone in clickable_zones:
                            if zone["rect"].collidepoint(event.pos):
                                if zone["action"] == "switch_tab": ui_manager.UI_STATE["active_tab"] = zone["target"]
                
                elif self.app_state == "PLAYING":
                    player = next((e for e in self.map_data.get("entities", []) if e.get("type") == "player"), None)
                    p_id = player.get("id") if player else None
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE: self.app_state = "MAIN_MENU"
                        elif event.key == pygame.K_c: self.app_state = "CHARACTER_SHEET"
                        elif event.key == pygame.K_SPACE: await engine.end_player_turn(); self.map_data = await self.load_map_data()
                    
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        mx, my = event.pos
                        if mx >= self.WINDOW_WIDTH - self.LOG_WIDTH: continue
                        gx, gy = (mx // self.CELL_SIZE) + cam_x, (my // self.CELL_SIZE) + cam_y
                        ctx = ui_manager.UI_STATE["context_menu"]
                        
                        if event.button == 1: 
                            if ctx["active"]:
                                mw, oh, hh = 180, 30, 30; mr = pygame.Rect(ctx["pos"][0], ctx["pos"][1], mw, (len(ctx["options"]) * oh) + hh)
                                if mr.collidepoint(mx, my):
                                    if my > ctx["pos"][1] + hh:
                                        idx = (my - (ctx["pos"][1] + hh)) // oh
                                        if idx < len(ctx["options"]):
                                            await self.handle_menu_selection(ctx["options"][idx], p_id, ctx["target_id"], ctx["target_pos"])
                                ctx["active"] = False
                            elif my < self.WINDOW_HEIGHT - self.UI_HEIGHT:
                                await self.attempt_player_move(p_id, gx, gy)
                                
                        elif event.button == 3: 
                            if my < self.WINDOW_HEIGHT - self.UI_HEIGHT:
                                ents = [e for e in self.map_data.get("entities", []) if e.get("pos") == [gx, gy]]
                                clicked_entity = next((e for e in ents if e.get("type") in ["hostile", "npc", "player"] and "dead" not in e.get("tags",[])), None)
                                if not clicked_entity and ents: clicked_entity = ents[0]
                                options = ui_manager.generate_menu_options(clicked_entity, player, "main")
                                ui_manager.UI_STATE["context_menu"] = {
                                    "active": True, "pos": (mx, my), "options": options,
                                    "target_id": clicked_entity.get("id") if clicked_entity else None,
                                    "target_name": clicked_entity.get("name") if clicked_entity else "Location",
                                    "target_pos": [gx, gy]
                                }

                elif self.app_state == "TRANSITION_PROMPT":
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        by, bn = self.draw_transition_prompt_ui()
                        if by.collidepoint(event.pos): 
                            await engine.execute_transition(self.transition_target[0], self.transition_target[1])
                            self.map_data = await self.load_map_data(); self.app_state = "PLAYING"
                        elif bn.collidepoint(event.pos): self.app_state = "PLAYING"

            if self.move_queue and not self.is_animating:
                self.is_animating = True; self.anim_timer = 0
            
            if self.is_animating:
                self.anim_timer += 1
                if self.anim_timer >= self.step_delay:
                    if self.move_queue:
                        next_step = self.move_queue.pop(0)
                        player = next((e for e in self.map_data.get("entities", []) if e.get("type") == "player"), None)
                        if player:
                            gw, gh = self.map_data.get("meta", {}).get("grid_size", [100, 100])
                            if next_step[0] <= 0 or next_step[0] >= gw-1 or next_step[1] <= 0 or next_step[1] >= gh-1:
                                self.transition_target = next_step; self.app_state = "TRANSITION_PROMPT"; self.move_queue = []
                            else:
                                await engine.execute_move(player.get("id"), next_step[0], next_step[1])
                                self.map_data = await self.load_map_data()
                    else: self.is_animating = False
                    self.anim_timer = 0

            pygame.display.flip(); await asyncio.sleep(0.016)

    def draw_main_menu_ui(self, mx, my):
        self.screen.fill(self.COLORS["bg"])
        title_surf = self.title_font.render("SHATTERLANDS", True, self.COLORS["title"])
        self.screen.blit(title_surf, title_surf.get_rect(center=(self.WINDOW_WIDTH // 2, self.WINDOW_HEIGHT // 4)))
        bx = (self.WINDOW_WIDTH // 2) - 100
        btns = [{"rect": pygame.Rect(bx, self.WINDOW_HEIGHT // 2, 200, 50), "text": "New Game", "action": "CHARACTER_CREATOR"}, {"rect": pygame.Rect(bx, self.WINDOW_HEIGHT // 2 + 70, 200, 50), "text": "Continue", "action": "LOAD_GAME"}, {"rect": pygame.Rect(bx, self.WINDOW_HEIGHT // 2 + 140, 200, 50), "text": "Quit", "action": "QUIT"}]
        for btn in btns:
            pygame.draw.rect(self.screen, self.COLORS["menu_hover"] if btn["rect"].collidepoint(mx, my) else self.COLORS["menu_bg"], btn["rect"])
            pygame.draw.rect(self.screen, self.COLORS["menu_border"], btn["rect"], 2)
            text_surf = self.font.render(btn["text"], True, self.COLORS["text"])
            self.screen.blit(text_surf, text_surf.get_rect(center=btn["rect"].center))
        return btns

    def draw_character_creator_ui(self, mx, my):
        self.screen.fill(self.COLORS["bg"])
        draw_text = ui_manager.draw_text
        stage = self.char_build["stage"]
        
        stages = ["Kingdom", "Sub-Type", "Variation", "Training", "Finalize"]
        header_text = f"CHARACTER SYNTHESIS - {stages[stage].upper()}"
        draw_text(self.screen, header_text, 50, 50, self.title_font, self.COLORS["title"])
        
        btns = {"kingdoms": [], "subtypes": [], "variation": [], "tracks": [], "nav": []}
        
        if stage == 0: # Kingdom
            draw_text(self.screen, "1. SELECT BIOLOGICAL KINGDOM", 50, 120, self.font, self.COLORS["warning"])
            kingdoms = ["Mammals", "Avians", "Reptiles & Amphibians", "Aquatics", "Insects & Arthropods", "Plants & Myconids"]
            for i, k in enumerate(kingdoms):
                row, col = i // 3, i % 3
                rect = pygame.Rect(50 + (col * 240), 150 + (row * 35), 230, 30)
                is_sel = self.char_build["kingdom"] == k
                pygame.draw.rect(self.screen, self.COLORS["menu_hover"] if is_sel or rect.collidepoint(mx, my) else self.COLORS["menu_bg"], rect)
                pygame.draw.rect(self.screen, self.COLORS["menu_border"], rect, 1)
                draw_text(self.screen, k, rect.x + 10, rect.y + 5, self.font, (255, 255, 255) if is_sel else (150, 150, 150))
                btns["kingdoms"].append({"rect": rect, "action": "set_kingdom", "val": k})
        
        elif stage == 1: # Sub-Type
            draw_text(self.screen, f"2. SELECT {self.char_build['kingdom'].upper()} SUB-TYPE", 50, 120, self.font, self.COLORS["warning"])
            subtypes = [
                ("T1", "The Balancer: Rounded arrays."),
                ("T2", "The Heavy: Might & Durability."),
                ("T3", "The Predator: Reflexes & Speed."),
                ("T4", "The Specialist: Technical/Mental Processing.")
            ]
            for i, (st, desc) in enumerate(subtypes):
                rect = pygame.Rect(50, 160 + (i * 60), 600, 50)
                is_sel = self.char_build["sub_type"] == st
                pygame.draw.rect(self.screen, self.COLORS["menu_hover"] if is_sel or rect.collidepoint(mx, my) else self.COLORS["menu_bg"], rect)
                pygame.draw.rect(self.screen, self.COLORS["menu_border"], rect, 1)
                draw_text(self.screen, st, rect.x + 10, rect.y + 15, self.title_font, (255, 255, 255) if is_sel else (150, 150, 150))
                draw_text(self.screen, desc, rect.x + 80, rect.y + 18, self.font, (200, 200, 200))
                btns["subtypes"].append({"rect": rect, "action": "set_subtype", "val": st})

        elif stage == 2: # Genetic Variation
            draw_text(self.screen, "3. GENETIC VARIATION & LIFE EXPERIENCE", 50, 120, self.font, self.COLORS["warning"])
            
            # Size Shift
            draw_text(self.screen, f"SIZE SHIFT: {self.char_build['size_shift']}", 50, 155, self.font, self.COLORS["title"])
            for i, opt in enumerate(["DOWN", "NONE", "UP"]):
                rect = pygame.Rect(50 + (i * 100), 180, 80, 30)
                is_sel = self.char_build["size_shift"] == opt
                pygame.draw.rect(self.screen, self.COLORS["menu_hover"] if is_sel or rect.collidepoint(mx, my) else self.COLORS["menu_bg"], rect)
                pygame.draw.rect(self.screen, self.COLORS["menu_border"], rect, 1)
                draw_text(self.screen, opt, rect.x + 10, rect.y + 5, self.font, (255, 255, 255) if is_sel else (150, 150, 150))
                btns["variation"].append({"rect": rect, "action": "set_size", "val": opt})

            # Stats (3B / 3M)
            from modules.character_engine import BODY_STATS, MIND_STATS
            draw_text(self.screen, f"LIFE EXPERIENCE (Body: {self.char_build['points_body']}, Mind: {self.char_build['points_mind']})", 400, 155, self.font, self.COLORS["warning"])
            
            def draw_stat_row(group, gx, gy, p_key):
                for i, s in enumerate(group):
                    rect = pygame.Rect(gx, gy + (i * 30), 180, 25)
                    val = self.char_build["exp"][s]
                    draw_text(self.screen, f"{s}: {val}", rect.x, rect.y, self.font, self.COLORS["text"])
                    plus_rect = pygame.Rect(rect.right - 25, rect.y, 25, 25)
                    pygame.draw.rect(self.screen, self.COLORS["menu_bg"], plus_rect); pygame.draw.rect(self.screen, self.COLORS["menu_border"], plus_rect, 1)
                    draw_text(self.screen, "+", plus_rect.x + 7, plus_rect.y + 2, self.font, (255, 255, 255))
                    btns["variation"].append({"rect": plus_rect, "action": "add_exp", "val": s, "p_key": p_key})

            draw_stat_row(BODY_STATS, 400, 180, "points_body")
            draw_stat_row(MIND_STATS, 620, 180, "points_mind")

        elif stage == 3: # Professional Training
            draw_text(self.screen, f"4. PROFESSIONAL TRAINING (Locked: {len(self.char_build['tracks'])}/6)", 50, 110, self.font, self.COLORS["warning"])
            track_mapping = engine.load_json_data(engine.TRACK_MAPPING_FILE)
            all_tracks = list(track_mapping.keys())[:24]
            for i, t in enumerate(all_tracks):
                row, col = i // 3, i % 3
                rect = pygame.Rect(50 + (col * 240), 140 + (row * 35), 230, 30)
                is_sel = t in self.char_build["tracks"]
                pygame.draw.rect(self.screen, (0, 100, 200) if is_sel else (self.COLORS["menu_hover"] if rect.collidepoint(mx, my) else self.COLORS["menu_bg"]), rect)
                pygame.draw.rect(self.screen, self.COLORS["menu_border"], rect, 1)
                draw_text(self.screen, t, rect.x + 10, rect.y + 5, self.font, (255, 255, 255) if is_sel else (150, 150, 150))
                btns["tracks"].append({"rect": rect, "action": "toggle_track", "val": t})

        elif stage == 4: # Final Preview
            draw_text(self.screen, "5. FINAL CHASSIS PREVIEW", 50, 120, self.font, self.COLORS["warning"])
            # Temporary "Simulated" Preview (Real math happens in engine upon start)
            draw_text(self.screen, f"KINGDOM: {self.char_build['kingdom']} ({self.char_build['sub_type']})", 50, 160, self.title_font, self.COLORS["title"])
            draw_text(self.screen, f"SIZE: {self.char_build['size_shift']}", 50, 200, self.font, self.COLORS["text"])
            draw_text(self.screen, "TRACKS:", 50, 230, self.font, self.COLORS["warning"])
            for i, t in enumerate(self.char_build["tracks"]):
                draw_text(self.screen, f"- {t}", 70, 255 + (i * 25), self.font, self.COLORS["text"])
            
            draw_text(self.screen, "Stat baselines and Hard Cap (8) will be enforced upon entry.", 400, 230, self.font, (100,255,100))
            draw_text(self.screen, "ALL CHOICES ARE FINAL FOR SESSION ZERO.", 400, 260, self.font, self.COLORS["danger"])

        # Navigation
        if stage > 0:
            prev_rect = pygame.Rect(50, 520, 100, 40)
            pygame.draw.rect(self.screen, self.COLORS["menu_bg"], prev_rect); pygame.draw.rect(self.screen, self.COLORS["menu_border"], prev_rect, 1)
            draw_text(self.screen, "< PREV", prev_rect.x + 15, prev_rect.y + 10, self.font, (255,255,255))
            btns["nav"].append({"rect": prev_rect, "action": "prev_stage"})
            
        next_text = "INITIALIZE CHASSIS" if stage == 4 else "NEXT >"
        next_rect = pygame.Rect(650, 520, 180, 40)
        can_next = True
        if stage == 2: can_next = (self.char_build["points_body"] == 0 and self.char_build["points_mind"] == 0)
        elif stage == 3: can_next = (len(self.char_build["tracks"]) == 6)
        
        pygame.draw.rect(self.screen, (0, 150, 0) if can_next else (50, 50, 50), next_rect)
        pygame.draw.rect(self.screen, self.COLORS["menu_border"], next_rect, 1)
        draw_text(self.screen, next_text, next_rect.x + 15, next_rect.y + 10, self.font, (255,255,255))
        if can_next: btns["nav"].append({"rect": next_rect, "action": "next_stage"})
        
        return btns

    def draw_tactical_screen_base(self, map_data: Dict[str, Any], cam_x: int, cam_y: int):
        self.screen.fill(self.COLORS["bg"]); self.draw_grid(); self.draw_entities(map_data, cam_x, cam_y)
        pygame.draw.rect(self.screen, self.COLORS["ui_bg"], (0, self.WINDOW_HEIGHT - self.UI_HEIGHT, self.WINDOW_WIDTH, self.UI_HEIGHT))
        pygame.draw.line(self.screen, (100, 100, 100), (0, self.WINDOW_HEIGHT - self.UI_HEIGHT), (self.WINDOW_WIDTH, self.WINDOW_HEIGHT - self.UI_HEIGHT), 2)
        ui_manager.draw_text_wrapped(self.screen, self.status_text, self.COLORS["text"], pygame.Rect(15, self.WINDOW_HEIGHT - self.UI_HEIGHT + 15, (self.WINDOW_WIDTH - self.LOG_WIDTH) - 30, self.UI_HEIGHT - 30), self.font)
        player = next((e for e in map_data.get("entities", []) if e.get("type") == "player"), None)
        if player:
            vitals_x = (self.WINDOW_WIDTH - self.LOG_WIDTH) - 420
            ui_manager.draw_text(self.screen, f"JAX: HP {player.get('hp')}/{player.get('max_hp')}", vitals_x, self.WINDOW_HEIGHT - self.UI_HEIGHT + 15, self.font, self.COLORS["title"])
            res = player.get("resources", {})
            ui_manager.draw_text(self.screen, f"STAMINA: {res.get('stamina')}", vitals_x + 180, self.WINDOW_HEIGHT - self.UI_HEIGHT + 15, self.font, self.COLORS["stamina"])

    def draw_transition_prompt_ui(self) -> Tuple[pygame.Rect, pygame.Rect]:
        pr = pygame.Rect((self.WINDOW_WIDTH - 350)//2, (self.WINDOW_HEIGHT - 180)//2, 350, 180)
        pygame.draw.rect(self.screen, self.COLORS["menu_bg"], pr); pygame.draw.rect(self.screen, self.COLORS["menu_border"], pr, 2)
        ui_manager.draw_text(self.screen, "Venture to new lands?", pr.centerx - 90, pr.centery - 40, self.font, self.COLORS["text"])
        by, bn = pygame.Rect(pr.centerx - 90, pr.centery + 10, 80, 40), pygame.Rect(pr.centerx + 10, pr.centery + 10, 80, 40)
        pygame.draw.rect(self.screen, (60, 60, 70), by); pygame.draw.rect(self.screen, (60, 60, 70), bn)
        ui_manager.draw_text(self.screen, "YES", by.centerx - 15, by.centery - 10, self.font, (255,255,255)); ui_manager.draw_text(self.screen, "NO", bn.centerx - 10, bn.centery - 10, self.font, (255,255,255))
        return by, bn

    def find_path(self, start: Tuple[int, int], end: Tuple[int, int]) -> List[Tuple[int, int]]:
        gw, gh = self.map_data.get("meta", {}).get("grid_size", [100, 100])
        ents = self.map_data.get("entities", [])
        def is_blocked(x, y):
            if x < 0 or x >= gw or y < 0 or y >= gh: return True
            return any(e.get("pos") == [x, y] and ("solid" in e.get("tags",[]) or (e.get("type") == "hostile" and "dead" not in e.get("tags",[]))) for e in ents)
        open_set = []; heapq.heappush(open_set, (0, start)); came_from = {}; g_score = {start: 0}; f_score = {start: abs(start[0] - end[0]) + abs(start[1] - end[1])}
        while open_set:
            current = heapq.heappop(open_set)[1]
            if current == end:
                path = []; 
                while current in came_from: path.append(current); current = came_from[current]
                path.reverse(); return path
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                neighbor = (current[0] + dx, current[1] + dy)
                if is_blocked(neighbor[0], neighbor[1]): continue
                tg = g_score[current] + 1
                if tg < g_score.get(neighbor, float('inf')):
                    came_from[neighbor] = current; g_score[neighbor] = tg; f_score[neighbor] = tg + abs(neighbor[0] - end[0]) + abs(neighbor[1] - end[1]); heapq.heappush(open_set, (f_score[neighbor], neighbor))
        return []

    async def attempt_player_move(self, p_id: str, gx: int, gy: int):
        if self.is_animating: return
        player = next((e for e in self.map_data.get("entities", []) if e.get("type") == "player"), None)
        if not player: return
        path = self.find_path(tuple(player.get("pos", [0,0])), (gx, gy))
        if path: self.move_queue = path
        else: self.status_text = "System: Path blocked or too far."

    async def handle_menu_selection(self, sel: str, p_id: str, t_id: str, t_pos: List[int]):
        if sel == "Cancel": return
        self.status_text = f"Action: {sel}..."; res = ""
        if sel == "Attack": res = await engine.execute_attack(p_id, t_id)
        elif sel == "Loot": res = await engine.execute_loot(p_id, t_id)
        elif sel == "Move Here": await self.attempt_player_move(p_id, t_pos[0], t_pos[1]); return
        elif sel == "Examine": res = await engine.execute_examine(p_id, t_id)
        self.status_text = f"System: {res}"; self.map_data = await self.load_map_data()
        if "No" not in res: await self.trigger_narration()

    async def trigger_narration(self):
        # AI narration hook (placeholder)
        pass

def main():
    game = OstrakaGame(); asyncio.run(game.start_game())

if __name__ == "__main__":
    main()
