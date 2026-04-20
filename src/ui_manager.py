import pygame
import textwrap
from typing import List, Dict, Any, Tuple, Optional
import entities
from core.world.time_manager import OstrakaCalendar

# UI_STATE: Tracks transient UI selections (e.g. active tab in character sheet)
UI_STATE = {
    "active_tab": "Inventory",
    "active_zoom_level": "Local",
    "context_menu": {"active": False, "item": None, "pos": (0, 0)}
}

def draw_text(surface: pygame.Surface, text: str, x: int, y: int, font: pygame.font.Font, color: Tuple[int, int, int]):
    """Basic text rendering helper."""
    img = font.render(text, True, color)
    surface.blit(img, (x, y))

def draw_text_wrapped(surface: pygame.Surface, text: str, color: Tuple[int, int, int], rect: pygame.Rect, font: pygame.font.Font):
    """Renders text inside a bounding box with automatic word-wrapping."""
    words = text.split(' ')
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        if font.size(test_line)[0] < rect.width:
            current_line.append(word)
        else:
            lines.append(' '.join(current_line))
            current_line = [word]
    lines.append(' '.join(current_line))
    
    y = rect.top
    for line in lines:
        img = font.render(line, True, color)
        surface.blit(img, (rect.left, y))
        y += font.get_linesize()

def draw_combat_log(surface: pygame.Surface, map_data: Dict[str, Any], rect: pygame.Rect, font: pygame.font.Font, title_font: pygame.font.Font, colors: Dict[str, Tuple[int, int, int]]):
    """Renders the rolling combat/event log on the right side of the screen."""
    pygame.draw.rect(surface, (10, 10, 12), rect)
    pygame.draw.line(surface, (100, 100, 100), (rect.left, 0), (rect.left, rect.bottom), 2)
    
    draw_text(surface, "LOG", rect.left + 15, rect.top + 15, title_font, colors["title"])
    
    log = map_data.get("combat_log", [])
    y = rect.top + 60
    for entry in reversed(log):
        log_rect = pygame.Rect(rect.left + 15, y, rect.width - 30, 100)
        draw_text_wrapped(surface, entry, colors["text"], log_rect, font)
        y += 60 # approx height of log entry
        if y > rect.bottom - 50: break

def draw_multi_tab_menu(surface: pygame.Surface, map_data: Dict[str, Any], font: pygame.font.Font, title_font: pygame.font.Font, colors: Dict[str, Tuple[int, int, int]], win_w: int, win_h: int) -> List[Dict[str, Any]]:
    """
    Renders the overlay Character Sheet/Inventory with multiple tabs.
    Returns a list of 'clickable zones' for the main game loop to handle.
    """
    overlay_rect = pygame.Rect(50, 50, win_w - 100, win_h - 100)
    pygame.draw.rect(surface, colors["menu_bg"], overlay_rect)
    pygame.draw.rect(surface, colors["menu_border"], overlay_rect, 3)
    
    tabs = ["Status", "Inventory", "Skills", "Map"]
    clickable_zones = []
    
    # Render Tab Headers
    for i, tab in enumerate(tabs):
        tab_rect = pygame.Rect(overlay_rect.left + (i * 120), overlay_rect.top, 120, 40)
        is_active = UI_STATE["active_tab"] == tab
        pygame.draw.rect(surface, colors["menu_hover"] if is_active else colors["menu_bg"], tab_rect)
        pygame.draw.rect(surface, colors["menu_border"], tab_rect, 1)
        draw_text(surface, tab, tab_rect.centerx - 30, tab_rect.centery - 10, font, (255, 255, 255) if is_active else (150, 150, 150))
        clickable_zones.append({"rect": tab_rect, "action": "switch_tab", "target": tab})

    # Render Content based on active tab
    content_rect = pygame.Rect(overlay_rect.left + 20, overlay_rect.top + 60, overlay_rect.width - 40, overlay_rect.height - 80)
    
    if UI_STATE["active_tab"] == "Status":
        player = next((e for e in map_data.get("entities", []) if e.type == "player"), None)
        if player:
            draw_text(surface, f"NAME: {player.name.upper()}", content_rect.x, content_rect.y, title_font, colors["title"])
            y = content_rect.y + 50
            for stat, val in player.stats.model_dump().items():
                draw_text(surface, f"{stat}: {val}", content_rect.x, y, font, colors["text"])
                y += 25
    
    elif UI_STATE["active_tab"] == "Inventory":
        player = next((e for e in map_data.get("entities", []) if e.type == "player"), None)
        if player:
            draw_text(surface, "INVENTORY", content_rect.x, content_rect.y, title_font, colors["title"])
            for i, item in enumerate(player.inventory):
                draw_text(surface, f"- {item}", content_rect.x, content_rect.y + 50 + (i * 25), font, colors["text"])

    elif UI_STATE["active_tab"] == "Map":
        draw_text(surface, "4-TIER CARTOGRAPHER", content_rect.x, content_rect.y, title_font, colors["title"])
        
        # Layer Switcher Sidebar
        sidebar_rect = pygame.Rect(content_rect.x, content_rect.y + 60, 150, content_rect.height - 100)
        zoom_levels = ["Global", "Continent", "Region", "Local"]
        
        for i, level in enumerate(zoom_levels):
            level_rect = pygame.Rect(sidebar_rect.x, sidebar_rect.y + (i * 50), 140, 45)
            is_active = UI_STATE["active_zoom_level"] == level
            pygame.draw.rect(surface, colors["menu_hover"] if is_active else (25, 30, 35), level_rect)
            pygame.draw.rect(surface, colors["menu_border"], level_rect, 1)
            draw_text(surface, level, level_rect.x + 10, level_rect.y + 12, font, (255, 255, 255) if is_active else (150, 150, 150))
            clickable_zones.append({"rect": level_rect, "action": "switch_zoom", "target": level})

        # Map Display Area
        map_display_rect = pygame.Rect(content_rect.x + 170, content_rect.y + 60, content_rect.width - 180, content_rect.height - 100)
        pygame.draw.rect(surface, (15, 18, 20), map_display_rect)
        pygame.draw.rect(surface, colors["menu_border"], map_display_rect, 2)

        meta = map_data.get("meta", {})
        raw_coord = meta.get("world_coord", {"gx":5, "gy":5, "cx":50, "cy":50, "rx":50, "ry":50, "lx":50, "ly":50})
        zoom = UI_STATE["active_zoom_level"]

        if zoom == "Global":
            # 10x10 God View
            cell_size = 40
            for x in range(10):
                for y in range(10):
                    rect = pygame.Rect(map_display_rect.centerx + ((x - 5) * cell_size), 
                                       map_display_rect.centery + ((y - 5) * cell_size), cell_size - 4, cell_size - 4)
                    color = (40, 45, 50)
                    if x == raw_coord["gx"] and y == raw_coord["gy"]: color = (0, 180, 255)
                    pygame.draw.rect(surface, color, rect)
            draw_text(surface, f"World Seed: {raw_coord['gx']},{raw_coord['gy']}", map_display_rect.x + 10, map_display_rect.y + 10, font, (200, 200, 200))

        elif zoom == "Continent":
            # 10x10 Window into 100x100 grid
            cell_size = 30
            for rx in range(-5, 6):
                for ry in range(-5, 6):
                    cx, cy = raw_coord["cx"] + rx, raw_coord["cy"] + ry
                    if not (0 <= cx < 100 and 0 <= cy < 100): continue
                    rect = pygame.Rect(map_display_rect.centerx + (rx * cell_size), 
                                       map_display_rect.centery + (ry * cell_size), cell_size - 3, cell_size - 3)
                    color = (30, 35, 40)
                    if rx == 0 and ry == 0: color = (0, 120, 255)
                    pygame.draw.rect(surface, color, rect)
            draw_text(surface, f"Continent: {raw_coord['cx']},{raw_coord['cy']}", map_display_rect.x + 10, map_display_rect.y + 10, font, (200, 200, 200))

        elif zoom == "Region":
            # Neighborhood View
            cell_size = 25
            for rx in range(-8, 9):
                for ry in range(-8, 9):
                    rect = pygame.Rect(map_display_rect.centerx + (rx * cell_size), 
                                       map_display_rect.centery + (ry * cell_size), cell_size - 2, cell_size - 2)
                    color = (25, 30, 35)
                    if rx == 0 and ry == 0: color = (0, 100, 200)
                    pygame.draw.rect(surface, color, rect)
            draw_text(surface, f"Region: {raw_coord['rx']},{raw_coord['ry']}", map_display_rect.x + 10, map_display_rect.y + 10, font, (200, 200, 200))

        elif zoom == "Local":
            # Render the 100x100 Biome Grid as background
            grid = map_data.get("biomes", [])
            if grid:
                cell_w = map_display_rect.width / 100
                cell_h = map_display_rect.height / 100
                
                # Ostraka Biome Color Matrix
                b_colors = {
                    "Chaos Zone / Grind Canyons": (180, 50, 220), # Vibrant Magenta/Purple
                    "Engineer's Range": (220, 230, 255),          # Frosty White/Blue
                    "The Sump": (40, 80, 40),                     # Toxic Murky Green
                    "The Dust Bowl": (180, 160, 110),             # Sandy Beige
                    "The Verdant Tangle": (20, 120, 20),          # Deep Jungle Green 
                    "Heartland Plains": (100, 160, 80),           # Bright Grass Green
                    "Howling Steppes": (140, 140, 120),           # Gritty Grey-Brown
                    "Shifting Wastes": (100, 100, 100)            # Neutral Grey
                }

                # Scale it down to pixels
                for y in range(100):
                    for x in range(100):
                        b_entry = grid[y][x]
                        # Handle both string grid and dict grid (from Clockwork engine)
                        b_type = b_entry["biome"] if isinstance(b_entry, dict) else b_entry
                        color = b_colors.get(b_type, (50, 50, 50))
                        rect = pygame.Rect(map_display_rect.x + x * cell_w, map_display_rect.y + y * cell_h, cell_w + 1, cell_h + 1)
                        pygame.draw.rect(surface, color, rect)

            draw_text(surface, f"POS: {raw_coord['lx']},{raw_coord['ly']}", map_display_rect.x + 10, map_display_rect.y + 10, font, (255, 255, 255))
            
            # Entities
            for ent in map_data.get("entities", []):
                ex, ey = ent.pos
                px = map_display_rect.x + (ex * (map_display_rect.width / 100))
                py = map_display_rect.y + (ey * (map_display_rect.height / 100))
                color = (0, 255, 0) if ent.type == "player" else (255, 255, 255)
                pygame.draw.circle(surface, color, (int(px), int(py)), 3)

    return clickable_zones

def draw_hover_tooltip(surface: pygame.Surface, entity: Any, pos: Tuple[int, int], font: pygame.font.Font, colors: Dict[str, Tuple[int, int, int]]):
    """Draws a small metadata tooltip when hovering over an entity in the tactical grid."""
    mx, my = pos
    text = f"{entity.name} (HP: {entity.hp}/{entity.max_hp})"
    w, h = font.size(text)
    tr = pygame.Rect(mx + 15, my - 25, w + 20, h + 10)
    pygame.draw.rect(surface, colors["menu_bg"], tr)
    pygame.draw.rect(surface, colors["menu_border"], tr, 1)
    draw_text(surface, text, tr.left + 10, tr.top + 5, font, colors["text"])
