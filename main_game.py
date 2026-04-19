import pygame
import threading
import json
import os
import time
import sys
from queue import Queue

# Core Ostraka Pipeline Imports
import actions
import engine
import narrator
import map_generator
import ui_manager

# Configuration & Constants (Targeting 1280x720 Unified Layout)
WINDOW_W = 1280
WINDOW_H = 720

# UI Regions
HEADER_RECT = pygame.Rect(0, 0, 1280, 50)
MAP_RECT = pygame.Rect(0, 50, 800, 400)
CONSOLE_RECT = pygame.Rect(0, 450, 800, 220)
INPUT_RECT = pygame.Rect(0, 670, 800, 50)
SIDEBAR_RECT = pygame.Rect(800, 0, 480, 720)

MAP_GRID_W, MAP_GRID_H = 20, 10
CELL_SIZE = 40

COLORS = {
    "bg": (10, 10, 15),
    "grid": (30, 30, 35),
    "player": (100, 200, 255),
    "hostile": (255, 80, 80),
    "npc": (200, 255, 100),
    "prop": (180, 180, 160),
    "text": (220, 220, 220),
    "title": (255, 215, 0),
    "dead": (60, 60, 65),
    "menu_bg": (20, 20, 25),
    "menu_border": (60, 60, 75),
    "menu_hover": (45, 45, 60),
    "ui_bg": (15, 15, 20),
    "stamina": (100, 255, 150),
    "focus": (200, 150, 255),
    "water": (50, 100, 255),
    "plant": (80, 180, 100),
    "wall": (100, 100, 110)
}

class OstrakaGame:
    def __init__(self):
        """Initializes the Integrated Ostraka Unified UI."""
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        pygame.display.set_caption("OSTRAKA: THE WEAVER'S DESK")
        self.clock = pygame.time.Clock()
        
        # 1. Pipeline Handlers
        self.parser = actions.IntentResolver()
        self.game_physicist = engine.GameEngine()
        self.storyteller = narrator.Narrator()
        
        # 2. Map Rendering
        self.map_renderer = map_generator.MapGenerator(CELL_SIZE, MAP_GRID_W, MAP_GRID_H, SIDEBAR_W=480)
        self.font = pygame.font.SysFont("Consolas", 18)
        self.title_font = pygame.font.SysFont("Consolas", 26, bold=True)
        self.small_font = pygame.font.SysFont("Consolas", 14)
        
        # 3. Game State
        self.state = engine.load_state()
        self.game_state = "EXPLORATION"
        
        # UI State integration
        self.clickable_regions = []
        self.player_text = ""
        self.cursor_visible = True
        self.last_cursor_blink = time.time()
        
        # Find Jax correctly
        player = self._get_player()
        if player:
            self.current_x, self.current_y = player["pos"]
        else:
            self.current_x, self.current_y = 50, 50 # Fallback
            
        self.running = True
        
        # Initial logs
        if not self.state.get("combat_log"):
            self.state["combat_log"] = ["Director: Simulation initialized. Welcome to the Shatterlands."]

    def _get_player(self):
        return next((e for e in self.state["local_map_state"].get("entities", []) if e.get("type") == "player"), None)

    def _get_world_context(self):
        """Reads active campaign data for AI immersion."""
        try:
            with open("data/Saves/campaign_active.json", "r") as f:
                camp = json.load(f)
            node = camp["nodes"][camp["current_node_index"]]
            return f"Goal: {camp['locked_goal']}. Objective: {node.get('task')}"
        except:
            meta = self.state["local_map_state"].get("meta", {})
            region = meta.get("region_id", "Unknown")
            return f"You are exploring the {region} region. Active Mode: {meta.get('encounter_mode','EXPLORATION')}"

    def _handle_pipeline_turn(self, player_text):
        """Orchestrates the turn resolution within the unified UI console."""
        ctx = self._get_world_context()
        player = self._get_player()
        
        engine.log_message(f"> {player_text}", state=self.state)
        
        # 1. Intent Parsing
        intent = self.parser.parse_player_input(player_text, ctx)
        
        # 2. Physics Resolution
        # Force refresh state before execution to handle async changes
        self.state = engine.load_state() 
        res = self.game_physicist.execute_action(intent, player, self.state)
        
        # Update local diorama coords if move succeeded
        if res["status"] == "SUCCESS":
            self.current_x, self.current_y = player["pos"]
        
        # 3. Narrative Generation
        story = self.storyteller.narrate_turn_result(res, ctx)
        engine.log_message(story, state=self.state)
        
        # 4. Post-Turn Refresh
        self.state = engine.load_state() 
        engine.save_state(self.state)

    def _handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if self.player_text.strip():
                        # Execute turn
                        self._handle_pipeline_turn(self.player_text)
                        self.player_text = ""
                elif event.key == pygame.K_BACKSPACE:
                    self.player_text = self.player_text[:-1]
                elif event.key == pygame.K_TAB:
                    # Toggle sidebar tabs via hotkey
                    tabs = ["Character", "Inventory", "Skills", "Investigation"]
                    idx = -1
                    curr = ui_manager.UI_STATE["active_tab"]
                    if curr in tabs: idx = tabs.index(curr)
                    ui_manager.UI_STATE["active_tab"] = tabs[(idx + 1) % len(tabs)]
                elif len(event.unicode) > 0 and event.key not in [pygame.K_ESCAPE, pygame.K_LSHIFT, pygame.K_RSHIFT, pygame.K_LCTRL, pygame.K_RCTRL]:
                    self.player_text += event.unicode
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                for zone in self.clickable_regions:
                    if zone["rect"].collidepoint(mx, my):
                        self._handle_ui_click(zone)

    def _handle_ui_click(self, zone):
        action = zone.get("action")
        if action == "switch_tab":
            ui_manager.UI_STATE["active_tab"] = zone["target"]
        elif action == "inventory_item":
            self._handle_pipeline_turn(f"use {zone['item']}")

    def start_game(self):
        """Primary Unified Engine Loop."""
        while self.running:
            # 1. PUMP EVENTS
            self._handle_input()
            if not self.running: break

            # Timer for cursor blink
            if time.time() - self.last_cursor_blink > 0.5:
                self.cursor_visible = not self.cursor_visible
                self.last_cursor_blink = time.time()

            # Sync State with File (Engine might have updated it)
            self.state = engine.load_state() 
            meta = self.state["local_map_state"].get("meta", {})
            self.game_state = meta.get("encounter_mode", "EXPLORATION")

            # 2. RENDER VISUALS
            self.screen.fill(COLORS["bg"])
            
            # --- Map Viewport ---
            cam_x = self.current_x - (MAP_GRID_W // 2)
            cam_y = self.current_y - (MAP_GRID_H // 2)
            
            map_surf = pygame.Surface((MAP_RECT.width, MAP_RECT.height))
            map_surf.fill(COLORS["bg"])
            self.map_renderer.draw_grid(map_surf, COLORS, MAP_RECT.height)
            self.map_renderer.draw_entities(map_surf, self.state["local_map_state"], cam_x, cam_y, COLORS, self.font)
            self.screen.blit(map_surf, (MAP_RECT.x, MAP_RECT.y))
            pygame.draw.rect(self.screen, COLORS["menu_border"], MAP_RECT, 1)

            # --- UI Components ---
            ui_manager.draw_header(self.screen, self.state, HEADER_RECT, self.font, self.title_font, COLORS)
            messages = self.state.get("combat_log", [])
            ui_manager.draw_console(self.screen, messages, CONSOLE_RECT, self.font, COLORS, state=self.state)
            ui_manager.draw_input_bar(self.screen, self.player_text, INPUT_RECT, self.font, COLORS, self.cursor_visible)
            self.clickable_regions = ui_manager.draw_sidebar(self.screen, self.state, SIDEBAR_RECT, self.font, self.title_font, COLORS)

            # --- Tooltips ---
            mx, my = pygame.mouse.get_pos()
            if MAP_RECT.collidepoint(mx, my):
                gx = cam_x + (mx - MAP_RECT.x) // CELL_SIZE
                gy = cam_y + (my - MAP_RECT.y) // CELL_SIZE
                hovered = next((e for e in self.state["local_map_state"].get("entities", []) if e["pos"] == [gx, gy]), None)
                if hovered:
                    ui_manager.draw_hover_tooltip(self.screen, hovered, (mx, my), self.small_font, COLORS)

            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()
        print("\nDirector: Simulation terminated. Local sync complete.")

if __name__ == "__main__":
    game = OstrakaGame()
    game.start_game()
