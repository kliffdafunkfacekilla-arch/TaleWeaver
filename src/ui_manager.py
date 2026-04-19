import pygame
import textwrap
from typing import List, Dict, Any, Tuple, Optional

# UI_STATE: Tracks transient UI selections (e.g. active tab in character sheet)
UI_STATE = {
    "active_tab": "Inventory",
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
    # ... logic for each tab content ...
    
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
