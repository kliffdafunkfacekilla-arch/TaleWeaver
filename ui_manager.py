import pygame
import entities

# Global state for the UI menu
UI_STATE = {
    "active_tab": "Character",
    "context_menu": {"active": False, "x": 0, "y": 0, "item": None, "options": []}
}

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
        screen.blit(title_font.render("Skill System Offline (Phase 4)", True, COLORS["text"]), (sheet_rect.x + 20, sheet_rect.y + 100))

    # Draw Sub-Context Menu (Right Click on items)
    if UI_STATE["context_menu"]["active"]:
        cm = UI_STATE["context_menu"]
        menu_rect = pygame.Rect(cm["x"], cm["y"], 120, len(cm["options"]) * 30)
        pygame.draw.rect(screen, COLORS["menu_bg"], menu_rect)
        pygame.draw.rect(screen, COLORS["menu_border"], menu_rect, 2)
        for i, opt in enumerate(cm["options"]):
            opt_rect = pygame.Rect(cm["x"], cm["y"] + (i * 30), 120, 30)
            
            # Hover effect
            if opt_rect.collidepoint(pygame.mouse.get_pos()):
                pygame.draw.rect(screen, COLORS["menu_hover"], opt_rect)
                
            screen.blit(font.render(opt, True, COLORS["text"]), (opt_rect.x + 10, opt_rect.y + 5))
            clickable_zones.append({"rect": opt_rect, "action": "context_action", "item": cm["item"], "choice": opt})

    # Footer
    screen.blit(font.render("Press 'C' or 'ESC' to close", True, (150, 150, 150)), (sheet_rect.centerx - 100, sheet_rect.bottom - 30))
    return clickable_zones

def _draw_character_tab(screen, player, sheet_rect, font, COLORS, clickable_zones):
    hp_text = f"HP: {player.get('hp',0)}/{player.get('max_hp',0)}"
    comp_text = f"Composure: {player.get('composure',0)}/{player.get('max_composure',0)}"
    screen.blit(font.render(f"{hp_text}  |  {comp_text}", True, COLORS["hostile"]), (sheet_rect.x + 20, sheet_rect.y + 80))
    
    res = player.get("resources", {})
    stam_text = f"Stamina: {res.get('stamina',0)}/{entities.get_max_stamina(player)}"
    foc_text = f"Focus: {res.get('focus',0)}/{entities.get_max_focus(player)}"
    screen.blit(font.render(f"{stam_text}  |  {foc_text}", True, COLORS["player"]), (sheet_rect.x + 20, sheet_rect.y + 100))
    
    # Currency Placeholders
    screen.blit(font.render(f"A-Coin: {player.get('a_coin', 0)}  |  D-Dust: {player.get('d_dust', 0)}", True, COLORS["title"]), (sheet_rect.x + 480, sheet_rect.y + 80))
    
    stats = player.get("stats", {})
    screen.blit(font.render("--- THE BODY ---", True, COLORS["title"]), (sheet_rect.x + 20, sheet_rect.y + 140))
    for i, s in enumerate(["Might", "Endurance", "Reflexes", "Finesse", "Vitality", "Fortitude"]):
        screen.blit(font.render(f"{s}: {stats.get(s, 0)}", True, COLORS["text"]), (sheet_rect.x + 20, sheet_rect.y + 170 + (i * 25)))

    screen.blit(font.render("--- THE MIND ---", True, COLORS["title"]), (sheet_rect.x + 250, sheet_rect.y + 140))
    for i, s in enumerate(["Knowledge", "Logic", "Awareness", "Intuition", "Charm", "Willpower"]):
        # Show Gear Bonuses explicitly: e.g., "Awareness: 4 (+2)"
        base_val = stats.get(s, 0)
        bonus = entities.get_gear_bonus(player, s)
        val_str = f"{base_val + bonus} (+{bonus})" if bonus > 0 else f"{base_val}"
        color = COLORS["npc"] if bonus > 0 else COLORS["text"]
        screen.blit(font.render(f"{s}: {val_str}", True, color), (sheet_rect.x + 250, sheet_rect.y + 170 + (i * 25)))

    derived = entities.get_derived_stats(player)
    screen.blit(font.render("--- ADVANTAGE ---", True, COLORS["title"]), (sheet_rect.x + 480, sheet_rect.y + 140))
    for i, (k, v) in enumerate(derived.items()):
        screen.blit(font.render(f"{k}: {v}", True, COLORS["player"]), (sheet_rect.x + 480, sheet_rect.y + 170 + (i * 25)))

    # Equipment Layout
    pygame.draw.line(screen, COLORS["menu_border"], (sheet_rect.x + 20, sheet_rect.y + 340), (sheet_rect.right - 20, sheet_rect.y + 340))
    screen.blit(font.render("--- ACTIVE LOADOUT (Click to Remove) ---", True, COLORS["title"]), (sheet_rect.x + 20, sheet_rect.y + 360))
    equip = player.get("equipment", {})
    y_off = 390
    for slot in ["weapon", "armor", "accessory"]:
        item = equip.get(slot, 'None')
        text_surf = font.render(f"{slot.capitalize()}: {item}", True, COLORS["hostile"] if item != "None" else COLORS["text"])
        rect = screen.blit(text_surf, (sheet_rect.x + 20, sheet_rect.y + y_off))
        if item != "None": clickable_zones.append({"rect": rect, "action": "unequip", "slot": slot})
        y_off += 25

def _draw_inventory_tab(screen, player, sheet_rect, font, COLORS, clickable_zones):
    screen.blit(font.render("--- INVENTORY (Right-Click Items) ---", True, COLORS["title"]), (sheet_rect.x + 20, sheet_rect.y + 80))
    inv = player.get("inventory", [])
    
    if not inv: 
        screen.blit(font.render("Your bag is empty.", True, COLORS["text"]), (sheet_rect.x + 20, sheet_rect.y + 120))
        return

    # Categorize Items dynamically
    items_db = entities.load_items()
    categories = {"Gear": [], "Consumables": [], "Misc": []}
    
    for item in inv:
        if item in items_db.get("weapons", {}) or item in items_db.get("armor", {}) or item in items_db.get("accessories", {}):
            categories["Gear"].append(item)
        elif item in ["Bandage", "Venom Gland", "Aether-Compass"]:
            categories["Consumables"].append(item)
        else:
            categories["Misc"].append(item)

    # Draw Sorted Lists
    x_off = 20
    for cat, items in categories.items():
        if not items: continue
        screen.blit(font.render(f"[{cat}]", True, COLORS["npc"]), (sheet_rect.x + x_off, sheet_rect.y + 120))
        y_off = 150
        for item in items:
            text_surf = font.render(f"- {item}", True, COLORS["text"])
            rect = screen.blit(text_surf, (sheet_rect.x + x_off, sheet_rect.y + y_off))
            clickable_zones.append({"rect": rect, "action": "inventory_item", "item": item})
            y_off += 25
        x_off += 250 # Space out columns

def draw_hover_tooltip(screen, entity, mouse_pos, font, COLORS):
    """Draws a dynamic tooltip for entities on the tactical map."""
    if not entity: return

    # Build the text lines
    lines = [entity.get("name", "Unknown Entity")]
    
    # Add HP if the entity is biological/destructible
    if "hp" in entity:
        lines.append(f"HP: {entity['hp']}/{entity.get('max_hp', entity['hp'])}")
        
    # Add up to 3 Tags for flavor (e.g., [beast, hostile, cold])
    tags = entity.get("tags", [])
    if tags:
        tag_str = ", ".join(tags[:3])
        lines.append(f"[{tag_str}]")

    # Calculate Box Dimensions dynamically
    padding = 10
    line_height = 20
    box_width = max([font.size(line)[0] for line in lines]) + (padding * 2)
    box_height = (len(lines) * line_height) + padding

    # Offset from the cursor so it doesn't cover the mouse
    x, y = mouse_pos
    x += 15
    y += 15

    # Screen Boundary Check (prevents the tooltip from clipping off-screen)
    screen_w, screen_h = screen.get_size()
    if x + box_width > screen_w: x = mouse_pos[0] - box_width - 10
    if y + box_height > screen_h: y = mouse_pos[1] - box_height - 10

    # Draw the Background Plate
    tooltip_surf = pygame.Surface((box_width, box_height))
    tooltip_surf.set_alpha(230) # Slight transparency
    tooltip_surf.fill(COLORS["menu_bg"])
    screen.blit(tooltip_surf, (x, y))
    pygame.draw.rect(screen, COLORS["menu_border"], (x, y, box_width, box_height), 1)

    # Render the Text
    for i, line in enumerate(lines):
        color = COLORS["title"] if i == 0 else COLORS["text"]
        if "hp" in entity and i == 1:
            color = COLORS["hostile"] if "hostile" in tags else COLORS["player"]
        screen.blit(font.render(line, True, color), (x + padding, y + 5 + (i * line_height)))
