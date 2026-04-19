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
    """Simple helper for rendering text to screen."""
    surf = font.render(text, True, color)
    screen.blit(surf, (x, y))

def draw_vitals_bar(screen, x, y, width, height, current, maximum, color, label, font):
    """Draws a premium looking progress bar with a label and value."""
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
    """Renders the persistent character sidebar on the right."""
    player = next((e for e in state["local_map_state"].get("entities", []) if e["type"] == "player"), None)
    if not player: return []

    clickable_zones = []
    bg = pygame.Surface((rect.width, rect.height))
    bg.fill((15, 15, 20)) 
    screen.blit(bg, rect)
    pygame.draw.line(screen, COLORS["menu_border"], (rect.x, rect.y), (rect.x, rect.bottom), 2)

    header_y = rect.y + 20
    screen.blit(title_font.render(player["name"].upper(), True, COLORS["title"]), (rect.x + 25, header_y))
    pygame.draw.line(screen, COLORS["title"], (rect.x + 25, header_y + 35), (rect.right - 25, header_y + 35), 1)

    v_y = header_y + 65
    bar_w = rect.width - 50
    draw_vitals_bar(screen, rect.x + 25, v_y, bar_w, 12, player.get("hp", 0), player.get("max_hp", 20), COLORS["hostile"], "VITALITY (HP)", font)
    
    # Composure Bar (Social HP)
    comp_max = entities.get_max_composure(player)
    draw_vitals_bar(screen, rect.x + 25, v_y + 45, bar_w, 12, player.get("composure", comp_max), comp_max, (200, 100, 255), "COMPOSURE (C)", font)

    stamina_max = entities.get_max_stamina(player)
    focus_max = entities.get_max_focus(player)
    draw_vitals_bar(screen, rect.x + 25, v_y + 90, bar_w, 12, player["resources"].get("stamina", 0), stamina_max, COLORS["player"], "STAMINA (S)", font)
    draw_vitals_bar(screen, rect.x + 25, v_y + 135, bar_w, 12, player["resources"].get("focus", 0), focus_max, COLORS["focus"], "FOCUS (F)", font)

    t_y = v_y + 175
    screen.blit(font.render("STATUS TAGS:", True, (150, 150, 150)), (rect.x + 25, t_y))
    tags = player.get("tags", [])
    tx, ty = rect.x + 25, t_y + 25
    for tag in tags:
        tag_surf = font.render(f"[{tag.upper()}]", True, COLORS["title"] if tag in ["unbreakable", "hostile"] else COLORS["text"])
        if tx + tag_surf.get_width() > rect.right - 25:
            tx = rect.x + 25; ty += 22
        screen.blit(tag_surf, (tx, ty))
        tx += tag_surf.get_width() + 10

    tab_y = ty + 40
    tabs = ["Stats", "Items", "Skills", "Clues"]
    tab_w = (rect.width - 50) // 4
    for i, tab in enumerate(tabs):
        tab_rect = pygame.Rect(rect.x + 25 + (i * tab_w), tab_y, tab_w, 30)
        is_active = (UI_STATE["active_tab"] == tab) or (UI_STATE["active_tab"] == "Character" and tab == "Stats") or (UI_STATE["active_tab"] == "Inventory" and tab == "Items") or (UI_STATE["active_tab"] == "Investigation" and tab == "Clues")
        bg_col = COLORS["menu_hover"] if is_active else (25, 25, 30)
        pygame.draw.rect(screen, bg_col, tab_rect)
        pygame.draw.rect(screen, COLORS["menu_border"], tab_rect, 1)
        txt = font.render(tab, True, COLORS["text"] if is_active else (150, 150, 150))
        screen.blit(txt, txt.get_rect(center=tab_rect.center))
        internal_tab = "Character" if tab == "Stats" else ("Inventory" if tab == "Items" else ("Skills" if tab == "Skills" else "Investigation"))
        clickable_zones.append({"rect": tab_rect, "action": "switch_tab", "target": internal_tab})

    content_rect = pygame.Rect(rect.x + 10, tab_y + 40, rect.width - 20, rect.height - (tab_y - rect.y) - 60)
    if UI_STATE["active_tab"] == "Character":
        _draw_sidebar_stats(screen, player, content_rect, font, COLORS)
    elif UI_STATE["active_tab"] == "Inventory":
        _draw_sidebar_inventory(screen, player, content_rect, font, COLORS, clickable_zones)
    elif UI_STATE["active_tab"] == "Skills":
        _draw_sidebar_skills(screen, player, content_rect, font, COLORS, clickable_zones)
    elif UI_STATE["active_tab"] == "Investigation":
        _draw_sidebar_clues(screen, state, content_rect, font, COLORS)

    return clickable_zones

def _draw_sidebar_stats(screen, player, rect, font, COLORS):
    stats = player.get("stats", {})
    y = rect.y + 10
    screen.blit(font.render("--- THE BODY ---", True, COLORS["title"]), (rect.x + 15, y)); y += 25
    for s in ["Might", "Endurance", "Reflexes", "Finesse", "Vitality", "Fortitude"]:
        val = stats.get(s, 0)
        screen.blit(font.render(f"{s}:", True, (180, 180, 180)), (rect.x + 25, y))
        screen.blit(font.render(str(val), True, COLORS["text"]), (rect.x + 150, y))
        y += 22
    y += 10
    screen.blit(font.render("--- THE MIND ---", True, COLORS["title"]), (rect.x + 15, y)); y += 25
    for s in ["Knowledge", "Logic", "Awareness", "Intuition", "Charm", "Willpower"]:
        val = stats.get(s, 0)
        bonus = entities.get_gear_bonus(player, s)
        total = val + bonus
        screen.blit(font.render(f"{s}:", True, (180, 180, 180)), (rect.x + 25, y))
        c = COLORS["npc"] if bonus > 0 else COLORS["text"]
        screen.blit(font.render(f"{total}" + (f" (+{bonus})" if bonus > 0 else ""), True, c), (rect.x + 150, y))
        y += 22

def _draw_sidebar_inventory(screen, player, rect, font, COLORS, clickable_zones):
    inv = player.get("inventory", [])
    y = rect.y + 10
    screen.blit(font.render("--- BACKPACK ---", True, COLORS["title"]), (rect.x + 15, y)); y += 30
    if not inv:
        screen.blit(font.render("(Empty)", True, (100, 100, 100)), (rect.x + 25, y))
        return
    for item in inv:
        item_rect = pygame.Rect(rect.x + 15, y, rect.width - 30, 25)
        if item_rect.collidepoint(pygame.mouse.get_pos()): pygame.draw.rect(screen, (40, 40, 50), item_rect)
        screen.blit(font.render(f"\u2022 {item}", True, COLORS["text"]), (rect.x + 20, y + 2))
        clickable_zones.append({"rect": item_rect, "action": "inventory_item", "item": item})
        y += 28

def _draw_sidebar_skills(screen, player, rect, font, COLORS, clickable_zones):
    skills = player.get("skills", [])
    y = rect.y + 10
    screen.blit(font.render("--- TACTICS & ANOMALIES ---", True, COLORS["title"]), (rect.x + 15, y)); y += 30
    if not skills:
        screen.blit(font.render("(No skills acquired)", True, (100, 100, 100)), (rect.x + 25, y))
        return
    for skill in skills:
        skill_rect = pygame.Rect(rect.x + 15, y, rect.width - 30, 25)
        if skill_rect.collidepoint(pygame.mouse.get_pos()): pygame.draw.rect(screen, (40, 40, 50), skill_rect)
        screen.blit(font.render(f"\u25b6 {skill}", True, COLORS["player"]), (rect.x + 20, y + 2))
        clickable_zones.append({"rect": skill_rect, "action": "skill_item", "skill": skill})
        y += 28

def _draw_sidebar_clues(screen, state, rect, font, COLORS):
    clues = state["local_map_state"].get("meta", {}).get("clue_tracker", [])
    y = rect.y + 10
    screen.blit(font.render("--- LOGGED EVIDENCE ---", True, COLORS["focus"]), (rect.x + 15, y)); y += 35
    if not clues:
        screen.blit(font.render("(No clues discovered yet)", True, (100, 100, 100)), (rect.x + 25, y))
        return
    for clue in clues:
        words = clue.split(' ')
        wrapped_lines = []
        line = ""
        for w in words:
            if font.size(line + " " + w)[0] < rect.width - 40: line += (" " + w if line else w)
            else: wrapped_lines.append(line); line = w
        wrapped_lines.append(line)
        for l in wrapped_lines:
            screen.blit(font.render(l, True, (200, 255, 200)), (rect.x + 20, y))
            y += 20
        y += 10 

def draw_console(screen, messages, rect, font, COLORS, state=None):
    """Renders the integrated message feed with mode-aware themeing."""
    bg_col = (10, 10, 15)
    border_col = COLORS["menu_border"]
    mode_label = "EXPLORATION"
    if state:
        meta = state["local_map_state"].get("meta", {})
        if meta.get("in_combat"):
            mode = meta.get("encounter_mode", "COMBAT")
            mode_label = mode.upper()
            if mode == "COMBAT": bg_col = (20, 10, 10); border_col = (255, 50, 50)
            elif mode == "SOCIAL_COMBAT": bg_col = (15, 10, 25); border_col = (200, 100, 255)
            elif mode == "PUZZLE": bg_col = (10, 20, 15); border_col = (50, 255, 150)
            elif mode == "MYSTERY": bg_col = (10, 15, 25); border_col = (100, 150, 255)
    bg = pygame.Surface((rect.width, rect.height)); bg.fill(bg_col); screen.blit(bg, rect)
    pygame.draw.line(screen, border_col, (rect.x, rect.y), (rect.right, rect.y), 2)
    header_surf = font.render(f"// {mode_label} FEED", True, border_col)
    screen.blit(header_surf, (rect.right - header_surf.get_width() - 20, rect.y + 10))
    y_cursor = rect.bottom - 10
    line_height = 22
    for msg in reversed(messages):
        if y_cursor < rect.y + 35: break
        msg_color = COLORS["text"]
        if "\u2694\ufe0f" in msg: msg_color = (255, 120, 120)
        elif "\ud83d\udde0\ufe0f" in msg: msg_color = (255, 255, 255)
        elif "\ud83d\uddef\ufe0f" in msg: msg_color = (200, 150, 255) # Social
        elif "\ud83c\udf10" in msg: msg_color = COLORS["focus"]
        elif "\ud83d\udccd" in msg: msg_color = COLORS["title"]
        elif "\ud83d\udcdc" in msg: msg_color = (200, 255, 200)
        elif "\ud83d\udd0d" in msg: msg_color = (100, 200, 255)
        elif "\ud83e\udde9" in msg: msg_color = (100, 255, 150)
        elif "Director:" in msg: msg_color = (150, 150, 150)
        words = msg.split(' ')
        lines = []
        curr = ""
        for w in words:
            if font.size(curr + " " + w)[0] < rect.width - 40: curr += (" " + w if curr else w)
            else: lines.append(curr); curr = w
        lines.append(curr)
        for l in reversed(lines):
            if y_cursor < rect.y + 35: break
            screen.blit(font.render(l, True, msg_color), (rect.x + 20, y_cursor - line_height))
            y_cursor -= line_height

def draw_input_bar(screen, input_text, rect, font, COLORS, cursor_visible):
    pygame.draw.rect(screen, (20, 20, 25), rect)
    pygame.draw.rect(screen, COLORS["menu_border"], rect, 1)
    prompt = "> "; p_surf = font.render(prompt, True, COLORS["title"])
    screen.blit(p_surf, (rect.x + 10, rect.y + (rect.height - p_surf.get_height()) // 2))
    text_x = rect.x + 10 + p_surf.get_width()
    t_surf = font.render(input_text, True, COLORS["text"])
    screen.blit(t_surf, (text_x, rect.y + (rect.height - t_surf.get_height()) // 2))
    if cursor_visible:
        cx = text_x + t_surf.get_width() + 2
        pygame.draw.line(screen, COLORS["title"], (cx, rect.y + 8), (cx, rect.bottom - 8), 2)

def draw_header(screen, state, rect, font, title_font, COLORS):
    pygame.draw.rect(screen, (20, 20, 25), rect)
    pygame.draw.line(screen, COLORS["menu_border"], (rect.x, rect.bottom), (rect.right, rect.bottom), 1)
    meta = state["local_map_state"].get("meta", {})
    region = meta.get("region_id", "The Unknown")
    clock = meta.get("clock", 0)
    screen.blit(font.render(f"REGION: {region.replace('_', ' ').upper()}", True, COLORS["title"]), (rect.x + 20, rect.y + 15))
    screen.blit(font.render(f"CYCLES: {clock}", True, (150, 150, 150)), (rect.x + 300, rect.y + 15))
    tracker = meta.get("campaign_tracker", {})
    quest = tracker.get("active_subplot", tracker.get("main_plot", "Seeking the Iron Caldera..."))
    q_label = font.render("OBJECTIVE: ", True, COLORS["npc"])
    screen.blit(q_label, (rect.x + 500, rect.y + 15))
    screen.blit(font.render(str(quest), True, COLORS["text"]), (rect.x + 500 + q_label.get_width(), rect.y + 15))

def draw_hover_tooltip(screen, entity, mouse_pos, font, COLORS):
    if not entity: return
    lines = [entity.get("name", "Unknown Entity").upper()]
    if "hp" in entity: lines.append(f"VITALITY: {entity['hp']}/{entity.get('max_hp', entity['hp'])}")
    if "composure" in entity:
        comp_max = entities.get_max_composure(entity)
        lines.append(f"COMPOSURE: {entity['composure']}/{comp_max}")
    tags = entity.get("tags", [])
    if tags: lines.append(f"TAGS: {', '.join(tags[:3]).upper()}")
    pd = 12; lh = 22; bw = max([font.size(l)[0] for l in lines]) + (pd * 2); bh = (len(lines) * lh) + pd
    x, y = mouse_pos[0] + 20, mouse_pos[1] + 20
    sw, sh = screen.get_size()
    if x + bw > sw: x = mouse_pos[0] - bw - 10
    if y + bh > sh: y = mouse_pos[1] - bh - 10
    ts = pygame.Surface((bw, bh)); ts.set_alpha(235); ts.fill((15, 15, 25)); screen.blit(ts, (x, y))
    pygame.draw.rect(screen, COLORS["menu_border"], (x, y, bw, bh), 1)
    for i, l in enumerate(lines):
        c = COLORS["title"] if i == 0 else COLORS["text"]
        if i == 1: c = COLORS["hostile"] if "hostile" in tags else COLORS["player"]
        if i == 2 and "composure" in entity: c = (200, 150, 255)
        screen.blit(font.render(l, True, c), (x + pd, y + 8 + (i * lh)))
