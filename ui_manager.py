import pygame
import entities

# Global state for the UI menu
UI_STATE = {
    "active_tab": "Character",
    "context_menu": {"active": False, "x": 0, "y": 0, "item": None, "options": []}
}

def draw_text(screen, text, x, y, font, color):
    """Simple helper for rendering text to screen."""
    surf = font.render(text, True, color)
    screen.blit(surf, (x, y))

def draw_multi_tab_menu(screen, map_data, font, title_font, COLORS, WINDOW_WIDTH, WINDOW_HEIGHT):
    player = next((e for e in map_data.get("entities", []) if e["type"] == "player"), None)
    if not player: return []
    
    clickable_zones = []
    
    # Dark Overlay
    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    overlay.set_alpha(240); overlay.fill((10, 10, 15))
    screen.blit(overlay, (0, 0))
    
    # Main UI Window
    sheet_rect = pygame.Rect(50, 50, WINDOW_WIDTH - 100, WINDOW_HEIGHT - 100)
    pygame.draw.rect(screen, COLORS["menu_bg"], sheet_rect)
    pygame.draw.rect(screen, COLORS["title"], sheet_rect, 2)
    
    # Header
    screen.blit(title_font.render(player["name"], True, COLORS["title"]), (sheet_rect.x + 20, sheet_rect.y + 20))
    
    # Tab Buttons
    tabs = ["Character", "Inventory", "Skills"]
    tab_w = 140; tab_h = 30
    for i, tab in enumerate(tabs):
        tab_rect = pygame.Rect(sheet_rect.x + 300 + (i * (tab_w + 10)), sheet_rect.y + 25, tab_w, tab_h)
        bg_color = COLORS["menu_hover"] if UI_STATE["active_tab"] == tab else COLORS["ui_bg"]
        pygame.draw.rect(screen, bg_color, tab_rect)
        pygame.draw.rect(screen, COLORS["menu_border"], tab_rect, 1)
        text_surf = font.render(tab, True, COLORS["text"])
        screen.blit(text_surf, text_surf.get_rect(center=tab_rect.center))
        clickable_zones.append({"rect": tab_rect, "action": "switch_tab", "target": tab})

    pygame.draw.line(screen, COLORS["menu_border"], (sheet_rect.x + 20, sheet_rect.y + 60), (sheet_rect.right - 20, sheet_rect.y + 60))

    # Render Content Based on Active Tab
    if UI_STATE["active_tab"] == "Character":
        _draw_character_tab(screen, player, sheet_rect, font, COLORS, clickable_zones)
    elif UI_STATE["active_tab"] == "Inventory":
        _draw_inventory_tab(screen, player, sheet_rect, font, COLORS, clickable_zones)
    elif UI_STATE["active_tab"] == "Skills":
        _draw_skills_tab(screen, player, sheet_rect, font, COLORS, clickable_zones)

    # Sub-Context Menu
    if UI_STATE["context_menu"]["active"]:
        cm = UI_STATE["context_menu"]
        menu_rect = pygame.Rect(cm["x"], cm["y"], 120, len(cm["options"]) * 30)
        pygame.draw.rect(screen, COLORS["menu_bg"], menu_rect)
        pygame.draw.rect(screen, COLORS["menu_border"], menu_rect, 2)
        for i, opt in enumerate(cm["options"]):
            opt_rect = pygame.Rect(cm["x"], cm["y"] + (i * 30), 120, 30)
            if opt_rect.collidepoint(pygame.mouse.get_pos()): pygame.draw.rect(screen, COLORS["menu_hover"], opt_rect)
            screen.blit(font.render(opt, True, COLORS["text"]), (opt_rect.x + 10, opt_rect.y + 5))
            clickable_zones.append({"rect": opt_rect, "action": "context_action", "item": cm["item"], "choice": opt})

    screen.blit(font.render("Press 'C' or 'ESC' to close", True, (150, 150, 150)), (sheet_rect.centerx - 100, sheet_rect.bottom - 30))
    return clickable_zones

def draw_combat_log(screen, state, rect, font, title_font, COLORS):
    """Renders the scrolling combat log on the right sidebar."""
    # Semi-transparent background
    bg = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    bg.fill((25, 25, 30, 210))
    screen.blit(bg, rect)
    pygame.draw.rect(screen, COLORS["menu_border"], rect, 1)

    # Title
    title_y = rect.y + 10
    screen.blit(font.render("--- COMBAT & EVENT LOG ---", True, COLORS["title"]), (rect.x + 15, title_y))
    pygame.draw.line(screen, (80, 80, 80), (rect.x + 10, title_y + 25), (rect.right - 10, title_y + 25), 1)

    # Messages
    messages = state.get("combat_log", [])
    if not messages: return

    y_cursor = rect.bottom - 25
    line_height = 22
    
    # Render from newest (last) to oldest (upwards)
    for msg in reversed(messages):
        if y_cursor < rect.y + 45: break # Panel full
        
        # Color coding based on prefix/content
        msg_color = COLORS["text"]
        if "⚔️" in msg: msg_color = (255, 100, 100) # Combat red
        elif "🌀" in msg: msg_color = COLORS["focus"] # Anomaly purple
        elif "↳" in msg: msg_color = (180, 180, 180) # Indented result
        elif "📍" in msg: msg_color = COLORS["title"] # World gold
        
        # Word wrapping
        words = msg.split(' ')
        lines = []
        current_line = ""
        for word in words:
            test_line = current_line + " " + word if current_line else word
            if font.size(test_line)[0] < rect.width - 30:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        lines.append(current_line)
        
        # Draw wrapped lines from bottom to top
        for line in reversed(lines):
            if y_cursor < rect.y + 45: break
            screen.blit(font.render(line, True, msg_color), (rect.x + 15, y_cursor))
            y_cursor -= line_height

def _draw_skills_tab(screen, player, sheet_rect, font, COLORS, clickable_zones):
    screen.blit(font.render("--- ACQUIRED SKILLS (Tactics & Anomalies) ---", True, COLORS["title"]), (sheet_rect.x + 20, sheet_rect.y + 80))
    player_skills = player.get("skills", [])
    if not player_skills:
        screen.blit(font.render("No skills acquired. Seek a Magistar.", True, COLORS["text"]), (sheet_rect.x + 20, sheet_rect.y + 120))
        return
    skills_db = entities.load_skills()
    y_off = 120
    for skill_name in player_skills:
        skill_data = None; category = ""
        for stat, data in skills_db.get("tactics", {}).items():
            for tier, t_data in data.get("tiers", {}).items():
                if t_data.get("name") == skill_name: skill_data = t_data; category = f"Tactic ({stat})"; break
            if skill_data: break
        if not skill_data:
            for school, data in skills_db.get("anomalies", {}).items():
                for tier, a_data in data.get("tiers", {}).items():
                    if a_data.get("name") == skill_name: skill_data = a_data; category = f"Anomaly ({school})"; break
                if skill_data: break
        if skill_data:
            skill_rect = pygame.Rect(sheet_rect.x + 20, sheet_rect.y + y_off, sheet_rect.width - 40, 30)
            if skill_rect.collidepoint(pygame.mouse.get_pos()): pygame.draw.rect(screen, COLORS["menu_hover"], skill_rect)
            screen.blit(font.render(f"{skill_name}", True, COLORS["text"]), (skill_rect.x + 5, skill_rect.y + 5))
            screen.blit(font.render(f"[{category}]", True, (150, 150, 150)), (skill_rect.x + 250, skill_rect.y + 5))
            cost = skill_data.get("cost", {})
            pv = cost.get("primary", cost.get("stamina", 0)); sv = cost.get("secondary", cost.get("focus", 0))
            xc = skill_rect.x + 500
            if pv > 0: screen.blit(font.render(f"S:{pv}", True, COLORS["stamina"]), (xc, skill_rect.y + 5)); xc += 60
            if sv > 0: screen.blit(font.render(f"F:{sv}", True, COLORS["focus"]), (xc, skill_rect.y + 5))
            clickable_zones.append({"rect": skill_rect, "action": "skill_item", "skill": skill_name}); y_off += 35

def _draw_character_tab(screen, player, sheet_rect, font, COLORS, clickable_zones):
    hp_text = f"HP: {player.get('hp',0)}/{player.get('max_hp',0)}"; comp_text = f"Composure: {player.get('composure',0)}/{player.get('max_composure',0)}"
    screen.blit(font.render(f"{hp_text}  |  {comp_text}", True, COLORS["hostile"]), (sheet_rect.x + 20, sheet_rect.y + 80))
    res = player.get("resources", {}); stam_text = f"Stamina: {res.get('stamina',0)}/{entities.get_max_stamina(player)}"; foc_text = f"Focus: {res.get('focus',0)}/{entities.get_max_focus(player)}"
    screen.blit(font.render(f"{stam_text}  |  {foc_text}", True, COLORS["player"]), (sheet_rect.x + 20, sheet_rect.y + 100))
    screen.blit(font.render(f"A-Coin: {player.get('a_coin', 0)}  |  D-Dust: {player.get('d_dust', 0)}", True, COLORS["title"]), (sheet_rect.x + 480, sheet_rect.y + 80))
    stats = player.get("stats", {})
    screen.blit(font.render("--- THE BODY ---", True, COLORS["title"]), (sheet_rect.x + 20, sheet_rect.y + 140))
    for i, s in enumerate(["Might", "Endurance", "Reflexes", "Finesse", "Vitality", "Fortitude"]):
        screen.blit(font.render(f"{s}: {stats.get(s, 0)}", True, COLORS["text"]), (sheet_rect.x + 20, sheet_rect.y + 170 + (i * 25)))
    screen.blit(font.render("--- THE MIND ---", True, COLORS["title"]), (sheet_rect.x + 250, sheet_rect.y + 140))
    for i, s in enumerate(["Knowledge", "Logic", "Awareness", "Intuition", "Charm", "Willpower"]):
        bv = stats.get(s, 0); b = entities.get_gear_bonus(player, s); vs = f"{bv + b} (+{b})" if b > 0 else f"{bv}"; c = COLORS["npc"] if b > 0 else COLORS["text"]
        screen.blit(font.render(f"{s}: {vs}", True, c), (sheet_rect.x + 250, sheet_rect.y + 170 + (i * 25)))
    dv = entities.get_derived_stats(player)
    screen.blit(font.render("--- ADVANTAGE ---", True, COLORS["title"]), (sheet_rect.x + 480, sheet_rect.y + 140))
    for i, (k, v) in enumerate(dv.items()): screen.blit(font.render(f"{k}: {v}", True, COLORS["player"]), (sheet_rect.x + 480, sheet_rect.y + 170 + (i * 25)))
    pygame.draw.line(screen, COLORS["menu_border"], (sheet_rect.x + 20, sheet_rect.y + 340), (sheet_rect.right - 20, sheet_rect.y + 340))
    screen.blit(font.render("--- ACTIVE LOADOUT (Click to Remove) ---", True, COLORS["title"]), (sheet_rect.x + 20, sheet_rect.y + 360))
    eq = player.get("equipment", {}); y_off = 390
    for slot in ["weapon", "armor", "accessory"]:
        item = eq.get(slot, 'None'); text_surf = font.render(f"{slot.capitalize()}: {item}", True, COLORS["hostile"] if item != "None" else COLORS["text"])
        rect = screen.blit(text_surf, (sheet_rect.x + 20, sheet_rect.y + y_off))
        if item != "None": clickable_zones.append({"rect": rect, "action": "unequip", "slot": slot})
        y_off += 25

def _draw_inventory_tab(screen, player, sheet_rect, font, COLORS, clickable_zones):
    screen.blit(font.render("--- INVENTORY (Right-Click Items) ---", True, COLORS["title"]), (sheet_rect.x + 20, sheet_rect.y + 80))
    inv = player.get("inventory", [])
    if not inv: screen.blit(font.render("Your bag is empty.", True, COLORS["text"]), (sheet_rect.x + 20, sheet_rect.y + 120)); return
    db = entities.load_items(); cat_lists = {"Gear": [], "Consumables": [], "Misc": []}
    for item in inv:
        if item in db.get("weapons", {}) or item in db.get("armor", {}) or item in db.get("accessories", {}): cat_lists["Gear"].append(item)
        elif item in ["Bandage", "Venom Gland", "Aether-Compass"]: cat_lists["Consumables"].append(item)
        else: cat_lists["Misc"].append(item)
    x_off = 20
    for cat, its in cat_lists.items():
        if not its: continue
        screen.blit(font.render(f"[{cat}]", True, COLORS["npc"]), (sheet_rect.x + x_off, sheet_rect.y + 120)); y_off = 150
        for it in its:
            text_surf = font.render(f"- {it}", True, COLORS["text"]); rect = screen.blit(text_surf, (sheet_rect.x + x_off, sheet_rect.y + y_off))
            clickable_zones.append({"rect": rect, "action": "inventory_item", "item": it}); y_off += 25
        x_off += 250

def draw_hover_tooltip(screen, entity, mouse_pos, font, COLORS):
    if not entity: return
    lines = [entity.get("name", "Unknown Entity")]
    if "hp" in entity: lines.append(f"HP: {entity['hp']}/{entity.get('max_hp', entity['hp'])}")
    tags = entity.get("tags", [])
    if tags: lines.append(f"[{', '.join(tags[:3])}]")
    pd = 10; lh = 20; bw = max([font.size(l)[0] for l in lines]) + (pd * 2); bh = (len(lines) * lh) + pd
    x, y = mouse_pos[0] + 15, mouse_pos[1] + 15; sw, sh = screen.get_size()
    if x + bw > sw: x = mouse_pos[0] - bw - 10
    if y + bh > sh: y = mouse_pos[1] - bh - 10
    ts = pygame.Surface((bw, bh)); ts.set_alpha(230); ts.fill(COLORS["menu_bg"]); screen.blit(ts, (x, y))
    pygame.draw.rect(screen, COLORS["menu_border"], (x, y, bw, bh), 1)
    for i, l in enumerate(lines):
        c = COLORS["title"] if i == 0 else COLORS["text"]
        if "hp" in entity and i == 1: c = COLORS["hostile"] if "hostile" in tags else COLORS["player"]
        screen.blit(font.render(l, True, c), (x + pd, y + 5 + (i * lh)))
