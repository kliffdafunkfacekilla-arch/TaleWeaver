import sqlite3
import json
import random
from typing import Dict, Any, List

class FactionManager:
    """
    Geopolitical engine for Ostraka.
    Optimized to aggregate global totals rather than pulsing individual settlements.
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path

    def pulse(self):
        """
        Main entry point for strategic logic. 
        Operates on global totals (LOD: Macro).
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            self._process_abstract_gathering(cursor)
            self._process_strategic_decisions(cursor)
            self._apply_tech_progression(cursor)
            conn.commit()
        except sqlite3.Error as e:
            print(f"[Faction Error] Strategic pulse failed: {e}")
        finally:
            conn.close()

    def _process_abstract_gathering(self, cursor: sqlite3.Cursor):
        """
        Calculates global production for each faction based on their combined 
        settlement infrastructure. (LOD Efficiency).
        """
        # 1. Sum up all yields per faction
        # Settlement -> Faction link required.
        query = """
            SELECT s.faction_id, b.resource_generated, SUM(b.yield_per_pulse)
            FROM buildings b
            JOIN settlements s ON b.settlement_id = s.id
            GROUP BY s.faction_id, b.resource_generated
        """
        cursor.execute(query)
        yields = cursor.fetchall()
        
        for f_id, res_type, amount in yields:
            self._update_faction_stockpile(cursor, f_id, res_type, amount)
            
        # 2. Passive Node Regrow (Global/Stochastic)
        cursor.execute("UPDATE resource_nodes SET remaining_supply = remaining_supply + 1 WHERE is_renewable = 1 AND remaining_supply < 100 AND RANDOM() % 100 < 5")

    def _process_strategic_decisions(self, cursor: sqlite3.Cursor):
        """
        Factions upgrade cities globally if material stockpiles allow.
        """
        cursor.execute("SELECT id, faction_id, level, resources_json FROM settlements")
        settlements = cursor.fetchall()
        
        for s_id, f_id, level, res_json in settlements:
            # We check the faction's global stockpile for the materials
            cursor.execute("SELECT resources_json FROM factions WHERE id = ?", (f_id,))
            f_row = cursor.fetchone()
            if not f_row: continue
            
            f_resources = json.loads(f_row[0] or "{}")
            cost = level * 100
            
            if level < 5 and f_resources.get("material", 0) >= cost:
                f_resources["material"] -= cost
                new_level = level + 1
                cursor.execute("UPDATE settlements SET level = ? WHERE id = ?", (new_level, s_id))
                cursor.execute("UPDATE factions SET resources_json = ? WHERE id = ?", (json.dumps(f_resources), f_id))
                print(f"[Strategic] Settlement {s_id} upgraded to Level {new_level} using global supplies.")

    def _update_faction_stockpile(self, cursor: sqlite3.Cursor, faction_id: str, resource: str, amount: int):
        cursor.execute("SELECT resources_json FROM factions WHERE id = ?", (faction_id,))
        row = cursor.fetchone()
        
        res = json.loads(row[0] or "{}") if row else {}
        res[resource] = res.get(resource, 0) + amount
        cursor.execute("UPDATE factions SET resources_json = ? WHERE id = ?",(json.dumps(res), faction_id))

    def _apply_tech_progression(self, cursor: sqlite3.Cursor):
        """Standard high-level tech upgrades."""
        cursor.execute("SELECT id, tech_level, resources_json FROM factions")
        factions = cursor.fetchall()
        
        for f_id, tech, res_json in factions:
            resources = json.loads(res_json or "{}")
            if tech < 4 and resources.get("luxury", 0) > (tech * 1000):
                new_tech = tech + 1
                resources["luxury"] -= (tech * 1000)
                cursor.execute("UPDATE factions SET tech_level = ?, resources_json = ? WHERE id = ?", (new_tech, json.dumps(resources), f_id))
                print(f"[Lore] Faction {f_id} reached Tech Era {new_tech}.")
