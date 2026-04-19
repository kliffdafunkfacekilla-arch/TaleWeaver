import pygame
import entities
import random

# Global state for the UI menu
UI_STATE = {
    "active_tab": "Character",
    "context_menu": {"active": False, "x": 0, "y": 0, "item": None, "options": []},
    "console_history": [],
    "input_text": "",
    "cursor_visible": True,
    "last_cursor_blink": 0
}

def draw_text(screen, text, x, y, font, color):
    surf = font.render(text, True, color)
    screen.blit(surf, (x, y))

def draw_vitals_bar(screen, x, y, width, height, current, maximum, color, label, font):
    pygame.draw.rect(screen, (30, 30, 35), (x, y, width, height), border_radius=4)
    fill_w = int((current / maximum) * width) if maximum > 0 else 0
    if fill_w > 0:
        pygame.draw.rect(screen, color, (x, y, fill_w, height), border_radius=4)
        pygame.draw.rect(screen, [max(0, c - 40) for c in color], (x, y + height // 2, fill_w, height // 2), border_radius=4)
    pygame.draw.rect(screen, (60, 60, 70), (x, y, width, height), 1, border_radius=4)
    l_surf = font.render(label, True, (200, 200, 200))
    v_surf = font.render(f"{current}/{maximum}", True, (255, 255, 255))
    screen.blit(l_surf, (x + 5, y - 20))
    screen.blit(v_surf, (x + width - v_surf.get_width() - 5, y - 20))

def draw_sidebar(screen, state, rect, font, title_font, COLORS):
    active_name = state["local_map_state"].get("meta", {}).get("active_player_name", "Jax")
    player = next((e for e in state["local_map_state"].get("entities", []) if e.get("type") == "player" and e.get("name") == active_name), None)
    if not player: return []
    clickable_zones = []
    bg = pygame.Surface((rect.width, rect.height)); bg.fill((15, 15, 20)); screen.blit(bg, rect)
    pygame.draw.line(screen, COLORS["menu_border"], (rect.x, rect.y), (rect.x, rect.bottom), 2)
    header_y = rect.y + 20
    screen.blit(title_font.render(player["name"].upper(), True, COLORS["title"]), (rect.x + 25, header_y))
    pygame.draw.line(screen, COLORS["title"], (rect.x + 25, header_y + 35), (rect.right - 25, header_y + 35), 1)
    v_y = header_y + 65; bar_w = rect.width - 50
    draw_vitals_bar(screen, rect.x + 25, v_y, bar_w, 12, player.get("hp", 0), player.get("max_hp", 20), COLORS["hostile"], "VITALITY (HP)", font)
    comp_max = entities.get_max_composure(player)
    draw_vitals_bar(screen, rect.x + 25, v_y + 45, bar_w, 12, player.get("composure", comp_max), comp_max, (200, 100, 255), "COMPOSURE (C)", font)
    draw_vitals_bar(screen, rect.x + 25, v_y + 90, bar_w, 12, player["resources"].get("stamina", 0), entities.get_max_stamina(player), COLORS["player"], "STAMINA (S)", font)
    draw_vitals_bar(screen, rect.x + 25, v_y + 135, bar_w, 12, player["resources"].get("focus", 0), entities.get_max_focus(player), COLORS["focus"], "FOCUS (F)", font)
    t_y = v_y + 175; screen.blit(font.render("STATUS TAGS:", True, (150, 150, 150)), (rect.x + 25, t_y))
    tags = player.get("tags", []); tx, ty = rect.x + 25, t_y + 25
    for tag in tags:
        tag_surf = font.render(f"[{tag.upper()}]", True, COLORS["title"])
        if tx + tag_surf.get_width() > rect.right - 25: tx = rect.x + 25; ty += 22
        screen.blit(tag_surf, (tx, ty)); tx += tag_surf.get_width() + 10
    tab_y = ty + 40; tabs = ["Stats", "Items", "Skills", "Clues"]
    tab_w = (rect.width - 50) // 4
    for i, tab in enumerate(tabs):
        tab_rect = pygame.Rect(rect.x + 25 + (i * tab_w), tab_y, tab_w, 30)
        is_active = (UI_STATE["active_tab"] == tab) or (UI_STATE["active_tab"] == "Character" and tab == "Stats") or (UI_STATE["active_tab"] == "Inventory" and tab == "Items") or (UI_STATE["active_tab"] == "Investigation" and tab == "Clues")
        bg_col = COLORS["menu_hover"] if is_active else (25, 25, 30)
        pygame.draw.rect(screen, bg_col, tab_rect); pygame.draw.rect(screen, COLORS["menu_border"], tab_rect, 1)
        txt = font.render(tab, True, COLORS["text"] if is_active else (150, 150, 150))
        screen.blit(txt, txt.get_rect(center=tab_rect.center))
        clickable_zones.append({"rect": tab_rect, "action": "switch_tab", "target": "Character" if tab == "Stats" else ("Inventory" if tab == "Items" else ("Skills" if tab == "Skills" else "Investigation"))})
    content_rect = pygame.Rect(rect.x + 10, tab_y + 40, rect.width - 20, rect.height - (tab_y - rect.y) - 60)
    if UI_STATE["active_tab"] == "Character": _draw_sidebar_stats(screen, state, content_rect, font, COLORS)
    elif UI_STATE["active_tab"] == "Inventory": _draw_sidebar_inventory(screen, player, content_rect, font, COLORS, clickable_zones)
    elif UI_STATE["active_tab"] == "Skills": _draw_sidebar_skills(screen, player, content_rect, font, COLORS, clickable_zones)
    elif UI_STATE["active_tab"] == "Investigation": _draw_sidebar_investigation(screen, state, content_rect, font, COLORS)
    return clickable_zones

def _draw_sidebar_stats(screen, state, rect, font, COLORS):
    active_name = state["local_map_state"].get("meta", {}).get("active_player_name", "Jax")
    player = next((e for e in state["local_map_state"].get("entities", []) if e.get("type") == "player" and e.get("name") == active_name), None)
    stats = player.get("stats", {})
    y = rect.y + 10; screen.blit(font.render("--- THE BODY ---", True, COLORS["title"]), (rect.x + 15, y)); y += 25
    for s in ["Might", "Endurance", "Reflexes", "Finesse", "Vitality", "Fortitude"]:
        screen.blit(font.render(f"{s}:", True, (180, 180, 180)), (rect.x + 25, y))
        screen.blit(font.render(str(stats.get(s, 0)), True, COLORS["text"]), (rect.x + 150, y)); y += 22
    y += 10; screen.blit(font.render("--- FACTION REPUTATION ---", True, COLORS["focus"]), (rect.x + 15, y)); y += 25
    rep_data = state["local_map_state"].get("meta", {}).get("reputation", [])
    if not rep_data: screen.blit(font.render("(No faction standing)", True, (100, 100, 100)), (rect.x + 25, y)); y += 22
    for name, val, tier in rep_data:
        screen.blit(font.render(f"{name}:", True, (180, 180, 180)), (rect.x + 25, y))
        color = COLORS["title"] if val > 10 else (COLORS["hostile"] if val < -10 else COLORS["text"])
        screen.blit(font.render(f"{tier} ({val})", True, color), (rect.x + 160, y)); y += 22

def _draw_sidebar_inventory(screen, player, rect, font, COLORS, clickable_zones):
    inv = player.get("inventory", []); y = rect.y + 10
    screen.blit(font.render("--- BACKPACK ---", True, COLORS["title"]), (rect.x + 15, y)); y += 30
    for item in inv:
        item_rect = pygame.Rect(rect.x + 15, y, rect.width - 30, 25)
        if item_rect.collidepoint(pygame.mouse.get_pos()): pygame.draw.rect(screen, (40, 40, 50), item_rect)
        screen.blit(font.render(f"\u2022 {item}", True, COLORS["text"]), (rect.x + 20, y + 2))
        clickable_zones.append({"rect": item_rect, "action": "inventory_item", "item": item}); y += 28

def _draw_sidebar_skills(screen, player, rect, font, COLORS, clickable_zones):
    skills = player.get("skills", []); y = rect.y + 10
    screen.blit(font.render("--- TACTICS & ANOMALIES ---", True, COLORS["title"]), (rect.x + 15, y)); y += 30
    for skill in skills:
        skill_rect = pygame.Rect(rect.x + 15, y, rect.width - 30, 25)
        if skill_rect.collidepoint(pygame.mouse.get_pos()): pygame.draw.rect(screen, (40, 40, 50), skill_rect)
        screen.blit(font.render(f"\u25b6 {skill}", True, COLORS["player"]), (rect.x + 20, y + 2))
        clickable_zones.append({"rect": skill_rect, "action": "skill_item", "skill": skill}); y += 28


def draw_header(screen, state, rect, font, title_font, COLORS):
    """Renders the top header with active player name and world state."""
    active_name = state["local_map_state"].get("meta", {}).get("active_player_name", "Jax")
    bg = pygame.Surface((rect.width, rect.height)); bg.fill((20, 20, 25)); screen.blit(bg, rect)
    pygame.draw.line(screen, COLORS["menu_border"], (0, rect.bottom), (rect.width, rect.bottom), 2)
    
    # Active Player Name (Bold)
    name_surf = title_font.render(f"ACTIVE: {active_name.upper()}", True, COLORS["title"])
    screen.blit(name_surf, (20, rect.y + 10))
    
    # World Clock / Mode
    meta = state["local_map_state"].get("meta", {})
    mode = meta.get("encounter_mode", "EXPLORATION")
    clock = meta.get("clock", 0)
    info = f"MODE: {mode} | CLOCK: {clock}"
    draw_text(screen, info, rect.width - font.size(info)[0] - 20, rect.y + 15, font, COLORS["text"])

def draw_console(screen, messages, rect, font, COLORS, state=None):
    """Renders the scrolling combat/narrative log."""
    bg = pygame.Surface((rect.width, rect.height)); bg.fill((15, 15, 20)); screen.blit(bg, rect)
    pygame.draw.rect(screen, COLORS["menu_border"], rect, 1)
    
    y_cursor = rect.bottom - 25
    line_height = 20
    
    for msg in reversed(messages):
        if y_cursor < rect.y + 10: break
        
        # Color processing
        color = COLORS["text"]
        if msg.startswith("["): color = COLORS["player"]  # Player Action
        elif "Director:" in msg: color = COLORS["title"]   # DM Narrative
        elif "⚠️" in msg: color = COLORS["hostile"]       # Warning/Combat
        
        # Simple wrap
        words = msg.split(' ')
        lines = []
        curr = ""
        for w in words:
            if font.size(curr + " " + w)[0] < rect.width - 40: curr += (" " + w if curr else w)
            else: lines.append(curr); curr = w
        lines.append(curr)
        
        for line in reversed(lines):
            if y_cursor < rect.y + 10: break
            screen.blit(font.render(line, True, color), (rect.x + 15, y_cursor))
            y_cursor -= line_height

def draw_input_bar(screen, text, rect, font, COLORS, cursor_visible):
    """Renders the player command input terminal."""
    bg = pygame.Surface((rect.width, rect.height)); bg.fill((10, 10, 15)); screen.blit(bg, rect)
    pygame.draw.rect(screen, COLORS["menu_border"], rect, 1)
    
    prompt = "> "
    display_text = prompt + text
    draw_text(screen, display_text, rect.x + 15, rect.y + 15, font, COLORS["text"])
    
    if cursor_visible:
        tw = font.size(display_text)[0]
        pygame.draw.line(screen, COLORS["text"], (rect.x + 15 + tw, rect.y + 15), (rect.x + 15 + tw, rect.y + 35), 2)

def draw_hover_tooltip(screen, entity, mouse_pos, font, COLORS):
    if not entity: return
    lines = [entity.get("name", "Unknown")]
    if "hp" in entity: lines.append(f"HP: {entity['hp']}/{entity.get('max_hp', 20)}")
    tags = entity.get("tags", [])
    if tags: lines.append(f"Tags: {', '.join(tags)}")
    
    bw = max([font.size(l)[0] for l in lines]) + 20
    bh = len(lines) * 20 + 20
    tx, ty = mouse_pos[0] + 15, mouse_pos[1] + 15
    
    t_surf = pygame.Surface((bw, bh)); t_surf.fill((20, 20, 25)); screen.blit(t_surf, (tx, ty))
    pygame.draw.rect(screen, COLORS["menu_border"], (tx, ty, bw, bh), 1)
    for i, l in enumerate(lines):
        draw_text(screen, l, tx + 10, ty + 10 + (i * 20), font, COLORS["text"])

def _draw_sidebar_investigation(screen, state, rect, font, COLORS):
    clues = state["local_map_state"].get("meta", {}).get("clue_tracker", [])
    relations = state["local_map_state"].get("meta", {}).get("faction_relations", [])
    y = rect.y + 10; screen.blit(font.render("--- INTER-FACTION RELATIONS ---", True, COLORS["title"]), (rect.x + 15, y)); y += 30
    if not relations: screen.blit(font.render("(Shadow war is quiet...)", True, (100, 100, 100)), (rect.x + 25, y)); y += 25
    for f1, f2, rel, status in relations:
        text = f"{f1} vs {f2}: {status} ({rel})"
        screen.blit(font.render(text, True, COLORS["hostile"] if rel < -30 else COLORS["text"]), (rect.x + 20, y)); y += 22
    y += 15; screen.blit(font.render("--- LOGGED EVIDENCE ---", True, COLORS["focus"]), (rect.x + 15, y)); y += 35
    for clue in clues:
        words = clue.split(' '); wrapped = []; line = ""
        for w in words:
            if font.size(line + " " + w)[0] < rect.width - 40: line += (" " + w if line else w)
            else: wrapped.append(line); line = w
        wrapped.append(line)
        for l in wrapped: screen.blit(font.render(l, True, (200, 255, 200)), (rect.x + 20, y)); y += 20
        y += 10
