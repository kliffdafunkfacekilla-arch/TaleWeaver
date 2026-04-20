import pygame
import textwrap
from typing import List, Dict, Any, Tuple, Optional
import entities
from core.world.time_manager import OstrakaCalendar

# UI_STATE: Tracks transient UI selections (e.g. active tab in character sheet)
UI_STATE = {
    "active_tab": "Inventory",
    "active_zoom_level": "Local",
    "context_menu": {"active": False, "item": None, "pos": (0, 0), "options": [], "target_id": None, "target_name": None, "target_pos": [0,0]}
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

def generate_menu_options(target: Optional[Dict[str, Any]], player: Dict[str, Any], page: str = "main") -> List[str]:
    """Generates a list of valid tactical actions for an entity based on player stats and skills."""
    if not player: return ["Cancel"]
    
    # In Ostraka, valid actions depend on tags and distance
    # Simplified version for the UI manager to present choices
    learned_skills = player.get("skills", [])
    options = []
    
    if page == "main":
        if not target: 
            options.append("Move Here")
            options.append("Examine Area")
        elif target.get("id") == player.get("id"):
            options.append("Examine Self")
        else:
            tags = target.get("tags", [])
            if "hostile" in tags and "dead" not in tags: options.append("Attack")
            if "item" in tags or "dead" in tags: options.append("Loot")
            if "container" in tags: options.append("Open")
            
            # Action logic based on skills
            for skill in learned_skills:
                # Skill logic would go here
                options.append(skill)
                
            options.append("Examine")
            
    options.append("Cancel")
    # De-duplicate
    return list(dict.fromkeys(options))

def draw_context_menu(surface: pygame.Surface, font: pygame.font.Font, colors: Dict[str, Tuple[int, int, int]], win_w: int, win_h: int):
    """Draws the right-click tactical menu."""
    menu = UI_STATE["context_menu"]
    if not menu.get("active"): return
    
    mx, my = pygame.mouse.get_pos()
    opts = menu.get("options", ["Cancel"])
    mw, oh, hh = 180, 30, 30
    mr = pygame.Rect(menu["pos"][0], menu["pos"][1], mw, (len(opts) * oh) + hh)
    
    # Boundary Check
    if mr.right > win_w: mr.right = win_w
    if mr.bottom > win_h: mr.bottom = win_h
    
    pygame.draw.rect(surface, colors["menu_bg"], mr)
    pygame.draw.rect(surface, colors["menu_border"], mr, 2)
    
    title = menu.get("target_name") if menu.get("target_name") else "Location"
    draw_text(surface, title, mr.x + 10, mr.y + 5, font, colors["title"])
    pygame.draw.line(surface, colors["menu_border"], (mr.x, mr.y + hh), (mr.right, mr.y + hh), 1)
    
    for i, opt in enumerate(opts):
        opt_rect = pygame.Rect(mr.x, mr.y + hh + (i * oh), mw, oh)
        if opt_rect.collidepoint(mx, my):
            pygame.draw.rect(surface, colors["menu_hover"], opt_rect)
        draw_text(surface, opt, opt_rect.x + 10, opt_rect.y + 5, font, colors["text"])

def draw_multi_tab_menu(surface: pygame.Surface, map_data: Dict[str, Any], font: pygame.font.Font, title_font: pygame.font.Font, colors: Dict[str, Tuple[int, int, int]], win_w: int, win_h: int) -> List[Dict[str, Any]]:
    """
    Renders the overlay Character Sheet/Inventory with multiple tabs.
    Ensures it DOES NOT overlap the bottom UI bar.
    """
    ui_y_start = 600 # self.WINDOW_HEIGHT - self.UI_HEIGHT
    overlay_rect = pygame.Rect(50, 50, win_w - 100, ui_y_start - 70)
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

    # Render Content
    content_rect = pygame.Rect(overlay_rect.left + 20, overlay_rect.top + 60, overlay_rect.width - 40, overlay_rect.height - 80)
    player_data = next((e for e in map_data.get("entities", []) if e.get("type") == "player"), None)
    
    if not player_data:
        draw_text(surface, "NO PLAYER DATA DETECTED", content_rect.x, content_rect.y, title_font, colors["danger"])
        return clickable_zones

    if UI_STATE["active_tab"] == "Status":
        draw_text(surface, f"NAME: {player_data.get('name','JAX').upper()}", content_rect.x, content_rect.y, title_font, colors["title"])
        y = content_rect.y + 50
        # Character Engine serialized stats
        stats = player_data.get("stats", {})
        if isinstance(stats, dict):
            for stat, val in stats.items():
                draw_text(surface, f"{stat}: {val}", content_rect.x, y, font, colors["text"])
                y += 25
                if y > content_rect.bottom - 20: break
    
    elif UI_STATE["active_tab"] == "Inventory":
        draw_text(surface, "SYSTEM INVENTORY", content_rect.x, content_rect.y, title_font, colors["title"])
        inv = player_data.get("inventory", [])
        if not inv:
             draw_text(surface, "(Empty)", content_rect.x, content_rect.y + 50, font, (100, 100, 100))
        for i, item in enumerate(inv):
            draw_text(surface, f"- {item}", content_rect.x, content_rect.y + 50 + (i * 25), font, colors["text"])

    elif UI_STATE["active_tab"] == "Map":
        draw_text(surface, "WORLD CARTOGRAPHER", content_rect.x, content_rect.y, title_font, colors["title"])
        sidebar_rect = pygame.Rect(content_rect.x, content_rect.y + 60, 150, content_rect.height - 100)
        zoom_levels = ["Global", "Continent", "Region", "Local"]
        for i, level in enumerate(zoom_levels):
            level_rect = pygame.Rect(sidebar_rect.x, sidebar_rect.y + (i * 50), 140, 45)
            is_active = UI_STATE["active_zoom_level"] == level
            pygame.draw.rect(surface, colors["menu_hover"] if is_active else (25, 30, 35), level_rect)
            pygame.draw.rect(surface, colors["menu_border"], level_rect, 1)
            draw_text(surface, level, level_rect.x + 10, level_rect.y + 12, font, (255, 255, 255) if is_active else (150, 150, 150))
            clickable_zones.append({"rect": level_rect, "action": "switch_zoom", "target": level})

        map_display_rect = pygame.Rect(content_rect.x + 170, content_rect.y + 60, content_rect.width - 180, content_rect.height - 100)
        pygame.draw.rect(surface, (15, 18, 20), map_display_rect)
        pygame.draw.rect(surface, colors["menu_border"], map_display_rect, 2)
        
        # Draw placeholder map nodes
        draw_text(surface, f"Current Region: {map_data.get('meta',{}).get('region_id','Unknown')}", map_display_rect.x + 20, map_display_rect.y + 20, font, colors["text"])
        draw_text(surface, "Grid: 100x100 [ACTIVE]", map_display_rect.x + 20, map_display_rect.y + 50, font, (0, 255, 0))

    return clickable_zones

def draw_hover_tooltip(surface: pygame.Surface, entity: Dict[str, Any], pos: Tuple[int, int], font: pygame.font.Font, colors: Dict[str, Tuple[int, int, int]]):
    """Draws a premium dynamic tooltip when hovering over an entity."""
    if not entity: return
    
    mx, my = pos
    lines = [entity.get("name", "Unknown")]
    if "hp" in entity:
        lines.append(f"HP: {entity['hp']}/{entity.get('max_hp', entity['hp'])}")
    
    tags = entity.get("tags", [])
    if tags:
        lines.append(f"[{', '.join(tags[:2])}]")
        
    line_height = 22
    padding = 10
    box_w = max([font.size(l)[0] for l in lines] + [20]) + padding * 2
    box_h = (len(lines) * line_height) + padding
    
    tr = pygame.Rect(mx + 20, my + 20, box_w, box_h)
    if tr.right > surface.get_width(): tr.right = mx - 20
    if tr.bottom > surface.get_height(): tr.bottom = my - 20
    
    tooltip_surf = pygame.Surface((tr.width, tr.height))
    tooltip_surf.set_alpha(220)
    tooltip_surf.fill(colors["menu_bg"])
    surface.blit(tooltip_surf, (tr.x, tr.y))
    pygame.draw.rect(surface, colors["menu_border"], tr, 1)
    
    for i, line in enumerate(lines):
        color = colors["title"] if i == 0 else colors["text"]
        draw_text(surface, line, tr.x + padding, tr.y + 5 + (i * line_height), font, color)
