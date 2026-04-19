import sqlite3
import math
import random
import time
import json

class WorldSimulation:
    def __init__(self, db_path="state/shatterlands.db"):
        self.db_path = db_path

    def trigger_world_pulse(self):
        """Advances the world simulation by one global tick."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 0. CELESTIAL CLOCK: Increment time
        cursor.execute("SELECT value FROM global_meta WHERE key='global_clock'")
        row = cursor.fetchone()
        clock = int(row[0]) if row else 0
        new_clock = clock + 1
        cursor.execute("INSERT OR REPLACE INTO global_meta (key, value) VALUES ('global_clock', ?)", (str(new_clock),))
        
        lunar_phase = new_clock % 28
        multiplier = self._get_lunar_multiplier(lunar_phase)
        
        print(f"\n[WORLD PULSE] Day {new_clock} | Lunar Phase: {lunar_phase}/28 | Intensity: {multiplier:.2f}x")

        # 1. MACRO SIMULATION (Clockwork Leylines + Lunar Cycle)
        self._simulate_macro_world(cursor, multiplier)
        
        # 2. ATMOSPHERIC SIMULATION (Drifting Storms)
        self._simulate_weather_fronts(cursor)
        
        # 3. 4X GRAND STRATEGY (Logistics & Expansion)
        self._simulate_trade_and_resources(cursor)
        self._simulate_settlement_decisions(cursor)

        # 4. LORE ECOLOGY (Lore-Aware Flora & Fauna Spawning)
        self._simulate_ecology(cursor, lunar_phase)
        
        # 5. CLEANUP: Purge the "Trade Route Graveyard" and Expired Storms
        self._perform_cleanup(cursor)
        
        conn.commit()
        conn.close()
        print("World Pulse Complete. The Shatterlands have evolved.")

    def _get_lunar_multiplier(self, phase):
        """Calculates chaos intensity based on the moon cycle (28 days)."""
        return 1.0 + 0.5 * math.sin(math.pi * (phase - 7) / 14)

    def _simulate_macro_world(self, cursor, multiplier):
        """Calculates Chaos flowing from the 12 Anchors to the Clockwork Center."""
        print(f"   -> Calculating Leyline Chaos ({multiplier:.2f}x intensity)...")
        cursor.execute("UPDATE layer4_macro_map SET chaos_level = MAX(0, chaos_level - 1)")
        cursor.execute("SELECT coord_id, chaos_level FROM layer4_macro_map")
        all_cells = cursor.fetchall()
        center_x, center_y = 4.5, 4.5
        for coord_id, _ in all_cells:
            try: x, y = map(int, coord_id.split(','))
            except: continue
            dist = math.sqrt((x - center_x)**2 + (y - center_y)**2)
            if dist < 1.0:
                cursor.execute("UPDATE layer4_macro_map SET chaos_level = MIN(100, chaos_level + ?) WHERE coord_id=?", (int(5 * multiplier), coord_id))
                continue
            angle_deg = (math.degrees(math.atan2(y - center_y, x - center_x)) + 360) % 360
            nearest_spoke = round(angle_deg / 30.0) * 30.0
            angle_diff = abs(angle_deg - nearest_spoke)
            if angle_diff > 180: angle_diff = 360 - angle_diff
            if angle_diff <= 10.0:
                injection = (2 if dist > 3 else 1) * multiplier
                cursor.execute("UPDATE layer4_macro_map SET chaos_level = MIN(100, chaos_level + ?) WHERE coord_id=?", (int(injection), coord_id))

    def _simulate_weather_fronts(self, cursor):
        """Drifts, Decays, and spawns Atmospheric Storms."""
        print("   -> Drifting & Decaying Atmospheric Storms...")
        cursor.execute("SELECT id, x, y, lifespan FROM weather_fronts")
        for sid, sx, sy, life in cursor.fetchall():
            # Apply lifespan decay
            new_life = life - 1
            if new_life <= 0:
                cursor.execute("DELETE FROM weather_fronts WHERE id=?", (sid,))
                continue
                
            dx, dy = 4.5 - sx, 4.5 - sy; dist = math.sqrt(dx*dx + dy*dy)
            if dist < 0.5: cursor.execute("DELETE FROM weather_fronts WHERE id=?", (sid,))
            else:
                nx, ny = sx + (dx/dist)*1.5, sy + (dy/dist)*1.5
                cursor.execute("UPDATE weather_fronts SET x=?, y=?, lifespan=? WHERE id=?", (nx, ny, new_life, sid))
                cursor.execute("UPDATE layer4_macro_map SET chaos_level = MIN(100, chaos_level + 5) WHERE coord_id=?", (f"{int(round(nx))},{int(round(ny))}",))
        
        cursor.execute("SELECT coord_id FROM layer4_macro_map WHERE chaos_level > 85")
        for cid in cursor.fetchall():
            if random.random() < 0.15:
                x, y = map(int, cid[0].split(','))
                cursor.execute("INSERT INTO weather_fronts (x, y, storm_type, intensity, lifespan) VALUES (?, ?, 'Chaos Storm', 10, ?)", (float(x), float(y), random.randint(3, 7)))

    def _simulate_trade_and_resources(self, cursor):
        """Processes 4X Depletion and Stochastic Trade Logistics."""
        print("   -> Processing Logistics & Finite Scarcity...")
        
        # A. FINITE RESOURCES: Harvesting Depletion
        cursor.execute("""
            SELECT b.id, b.yield_per_pulse, s.x, s.y, b.building_type, s.name 
            FROM buildings b 
            JOIN settlements s ON b.settlement_id = s.id 
            WHERE b.building_type IN ('Mine', 'Quarry', 'Camp')
        """)
        harvesters = cursor.fetchall()
        for bid, yieldv, sx, sy, bt, sname in harvesters:
            cursor.execute("SELECT id, remaining_supply, resource_type FROM resource_nodes WHERE x=? AND y=?", (sx, sy))
            node = cursor.fetchone()
            if node:
                nid, supply, rtype = node
                new_supply = supply - yieldv
                if new_supply <= 0:
                    cursor.execute("DELETE FROM resource_nodes WHERE id=?", (nid,))
                    print(f"      [DEPLETION] {rtype} at {sname} ({sx},{sy}) has run dry!")
                else:
                    cursor.execute("UPDATE resource_nodes SET remaining_supply=? WHERE id=?", (new_supply, nid))

        # B. CARAVAN TRADE & BANDITS
        cursor.execute("""
            SELECT t.id, s.happiness, s.x, s.y, t.transport_tech, t.goods_type, s.name, s.id as sid
            FROM trade_routes t
            JOIN settlements s ON t.source_settlement_id = s.id
            WHERE t.caravan_status = 'In Transit'
        """)
        active_routes = cursor.fetchall()
        for tid, happiness, sx, sy, tech, goods, sname, sid in active_routes:
            cursor.execute("SELECT chaos_level FROM layer4_macro_map WHERE coord_id=?", (f"{int(sx)},{int(sy)}",))
            chaos_row = cursor.fetchone()
            chaos = chaos_row[0] if chaos_row else 0
            cursor.execute("SELECT SUM(defense_bonus) FROM buildings WHERE settlement_id=?", (sid,))
            def_row = cursor.fetchone()
            defense_bonus = def_row[0] if def_row and def_row[0] else 0
            
            bandit_chance = (chaos * 2) + (100 - happiness) - (defense_bonus * 5)
            if tech == 'Airships': bandit_chance -= 30
            elif tech == 'Sailing': bandit_chance -= 15
            
            roll = random.randint(1, 100)
            threshold = max(5, bandit_chance)
            
            if roll <= threshold:
                cursor.execute("UPDATE trade_routes SET caravan_status='Raided' WHERE id=?", (tid,))
                cursor.execute("UPDATE layer4_macro_map SET chaos_level = MIN(100, chaos_level + 2) WHERE coord_id=?", (f"{int(sx)},{int(sy)}",))
                print(f"      [RAID] {sname} caravan ({goods}) was intercepted!")
            else:
                cursor.execute("UPDATE trade_routes SET caravan_status='Arrived' WHERE id=?", (tid,))
                print(f"      [TRADE] {sname} caravan ({goods}) has safely arrived.")

    def _simulate_settlement_decisions(self, cursor):
        """Autonomous 4X expansion."""
        print("   -> Spurring Autonomous Growth...")
        cursor.execute("SELECT id, name, happiness FROM settlements")
        for sid, name, hap in cursor.fetchall():
            if hap > 80 and random.random() < 0.15:
                bt = random.choice(['Mine', 'Watchtower', 'Market'])
                cursor.execute("INSERT INTO buildings (settlement_id, building_type, defense_bonus, yield_per_pulse) VALUES (?, ?, ?, ?)", (sid, bt, 5 if bt == 'Watchtower' else 0, 2 if bt == 'Mine' else 0))
                print(f"      [GROWTH] {name} has built a new {bt}.")

    def _simulate_ecology(self, cursor, lunar_phase):
        """Autonomous Ecosystem: Spawns Lore-Accurate Flora & Fauna."""
        print("   -> Simulating Lore-Accurate Ecology...")
        cursor.execute("SELECT coord_id, biome, chaos_level, resource_wealth FROM layer4_macro_map")
        all_cells = cursor.fetchall()
        for cid, biome, chaos, wealth in all_cells:
            spawn_chance = 0.05 if (wealth > 60 and chaos < 50) else 0.01
            if random.random() < spawn_chance:
                cursor.execute("SELECT title, category FROM lore_entries WHERE content LIKE ? AND category IN ('Flora', 'Fauna') ORDER BY RANDOM() LIMIT 1", (f"%{biome}%",))
                entry = cursor.fetchone()
                if entry:
                    ltitle, lcat = entry; x, y = map(int, cid.split(','))
                    rtype = f"{ltitle} (Huntable)" if lcat == 'Fauna' else f"{ltitle} (Farmable)"
                    cursor.execute("INSERT INTO resource_nodes (x, y, resource_type, remaining_supply) VALUES (?, ?, ?, 20)", (x, y, rtype))
                    print(f"      [ECOLOGY] {ltitle} has appeared in the {biome} shard.")

    def _perform_cleanup(self, cursor):
        """Cleans up stagnant/finished data to prevent DB bloat."""
        print("   -> Performing Database Cleanup (Trade Routes / Weather)...")
        # Delete finished Trade Routes
        cursor.execute("DELETE FROM trade_routes WHERE caravan_status IN ('Raided', 'Arrived')")
        
        # Delete weather fronts that drifted far or expired
        # (Already handled in weather pulse decay, but let's be double sure)
        cursor.execute("DELETE FROM weather_fronts WHERE lifespan <= 0")

if __name__ == "__main__":
    sim = WorldSimulation()
    sim.trigger_world_pulse()
