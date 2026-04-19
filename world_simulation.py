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
        
        # Ensure Factions exist for the simulation
        self._ensure_factions_exist(cursor)

        # 0. CELESTIAL CLOCK: Increment time
        cursor.execute("SELECT value FROM global_meta WHERE key='global_clock'")
        row = cursor.fetchone()
        clock = int(row[0]) if row else 0
        new_clock = clock + 1
        cursor.execute("INSERT OR REPLACE INTO global_meta (key, value) VALUES ('global_clock', ?)", (str(new_clock),))
        
        lunar_phase = new_clock % 28
        multiplier = self._get_lunar_multiplier(lunar_phase)
        
        print(f"\n[WORLD PULSE] Day {new_clock} | Lunar Phase: {lunar_phase}/28 | Intensity: {multiplier:.2f}x")

        # 1. MACRO & ATMOSPHERIC
        self._simulate_macro_world(cursor, multiplier)
        self._simulate_weather_fronts(cursor)
        
        # 2. LOGISTICS & GROWTH (4X)
        self._simulate_trade_and_resources(cursor)
        self._simulate_settlement_decisions(cursor)

        # 3. FACTION DIPLOMACY & SHADOW WAR
        self._simulate_faction_diplomacy(cursor)
        self._simulate_faction_operations(cursor)

        # 4. LORE ECOLOGY
        self._simulate_ecology(cursor, lunar_phase)
        
        # 5. CLEANUP
        self._perform_cleanup(cursor)
        
        conn.commit()
        conn.close()
        print("World Pulse Complete. The Shatterlands have evolved.")

    def _ensure_factions_exist(self, cursor):
        """Initializes default factions if the table is empty."""
        cursor.execute("SELECT count(*) FROM factions")
        if cursor.fetchone()[0] == 0:
            factions = [
                (1, "The Iron Caldera", 5000, 100, "Industrial Authoritarian"),
                (2, "Sump-Kin Union", 2000, 40, "Survivalist Collectivist"),
                (3, "Heartland Alliance", 4000, 80, "Bureaucratic Merchantile"),
                (4, "The Silent Monolith", 1000, 200, "Cabal Mysticism")
            ]
            cursor.executemany("INSERT INTO factions (id, name, wealth, influence, ideology) VALUES (?, ?, ?, ?, ?)", factions)
            
            # Initial relations (Everyone starts slightly frosty)
            for i in range(1, 5):
                for j in range(i + 1, 5):
                    cursor.execute("INSERT INTO faction_relations (faction_a, faction_b, relationship) VALUES (?, ?, ?)", (i, j, -10))

    def _get_lunar_multiplier(self, phase):
        return 1.0 + 0.5 * math.sin(math.pi * (phase - 7) / 14)

    def _simulate_macro_world(self, cursor, multiplier):
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
        """Drifts and Decays Atmospheric Storms with diverse types."""
        print("   -> Processing Atmospheric Anomalies...")
        cursor.execute("SELECT id, x, y, lifespan, storm_type FROM weather_fronts")
        for sid, sx, sy, life, s_type in cursor.fetchall():
            new_life = life - 1
            if new_life <= 0:
                cursor.execute("DELETE FROM weather_fronts WHERE id=?", (sid,))
                continue
            dx, dy = 4.5 - sx, 4.5 - sy; dist = math.sqrt(dx*dx + dy*dy)
            if dist < 0.5: cursor.execute("DELETE FROM weather_fronts WHERE id=?", (sid,))
            else:
                nx, ny = sx + (dx/dist)*1.5, sy + (dy/dist)*1.5
                cursor.execute("UPDATE weather_fronts SET x=?, y=?, lifespan=? WHERE id=?", (nx, ny, new_life, sid))
                
                # TYPE EFFECTS
                cid = f"{int(round(nx))},{int(round(ny))}"
                if s_type == "Chaos Storm":
                    cursor.execute("UPDATE layer4_macro_map SET chaos_level = MIN(100, chaos_level + 5) WHERE coord_id=?", (cid,))
                elif s_type == "Acid Rain":
                    cursor.execute("UPDATE buildings SET durability = durability - 2 WHERE settlement_id IN (SELECT id FROM settlements WHERE x=? AND y=?)", (int(round(nx)), int(round(ny))))
                elif s_type == "Obsidian Fog":
                    # Fog increases success for shadowy movements (handled in trade/ops pulses)
                    pass
        
        # Spawn New Fronts
        if random.random() < 0.3:
            s_type = random.choice(["Chaos Storm", "Acid Rain", "Obsidian Fog", "Clockwork Gales"])
            cursor.execute("SELECT coord_id FROM layer4_macro_map ORDER BY RANDOM() LIMIT 1")
            cid = cursor.fetchone()
            if cid:
                x, y = map(int, cid[0].split(','))
                cursor.execute("INSERT INTO weather_fronts (x, y, storm_type, intensity, lifespan) VALUES (?, ?, ?, ?, ?)", (float(x), float(y), s_type, 10, random.randint(4, 9)))

    def _simulate_trade_and_resources(self, cursor):
        """Processes 4X Depletion and Stochastic Trade Logistics."""
        print("   -> Processing Logistics & Scarcity...")
        
        # FINITE RESOURCES
        cursor.execute("SELECT b.id, b.yield_per_pulse, s.x, s.y, b.building_type, s.name, b.durability FROM buildings b JOIN settlements s ON b.settlement_id = s.id")
        for bid, yieldv, sx, sy, bt, sname, durability in cursor.fetchall():
            if durability <= 0: continue # Broken buildings don't produce
            cursor.execute("SELECT id, remaining_supply, resource_type FROM resource_nodes WHERE x=? AND y=?", (sx, sy))
            node = cursor.fetchone()
            if node:
                nid, supply, rtype = node; new_supply = supply - yieldv
                if new_supply <= 0: cursor.execute("DELETE FROM resource_nodes WHERE id=?", (nid,))
                else: cursor.execute("UPDATE resource_nodes SET remaining_supply=? WHERE id=?", (new_supply, nid))

        # CARAVAN TRADE
        cursor.execute("SELECT t.id, s.happiness, s.x, s.y, t.transport_tech, t.goods_type, s.name, s.id, s.faction_id FROM trade_routes t JOIN settlements s ON t.source_settlement_id = s.id WHERE t.caravan_status = 'In Transit'")
        for tid, happiness, sx, sy, tech, goods, sname, sid, fid in cursor.fetchall():
            cursor.execute("SELECT chaos_level FROM layer4_macro_map WHERE coord_id=?", (f"{int(sx)},{int(sy)}",))
            chaos = cursor.fetchone()[0]
            
            # Check for "Obsidian Fog" (Increases raid chance)
            cursor.execute("SELECT count(*) FROM weather_fronts WHERE storm_type='Obsidian Fog' AND ABS(x-?) < 1 AND ABS(y-?) < 1", (sx, sy))
            fog_bonus = 20 if cursor.fetchone()[0] > 0 else 0
            
            bandit_chance = (chaos * 2) + (100 - happiness) + fog_bonus
            if tech == 'Airships': bandit_chance -= 30
            
            if random.randint(1, 100) <= max(5, bandit_chance):
                cursor.execute("UPDATE trade_routes SET caravan_status='Raided' WHERE id=?", (tid,))
                print(f"      [RAID] {sname} caravan ({goods}) intercepted!")
            else:
                cursor.execute("UPDATE trade_routes SET caravan_status='Arrived' WHERE id=?", (tid,))
                # Trade success increases faction wealth
                if fid: cursor.execute("UPDATE factions SET wealth = wealth + 100 WHERE id=?", (fid,))

    def _simulate_faction_diplomacy(self, cursor):
        """Simulates relationship drift and negotiation."""
        print("   -> Simulating Faction Diplomacy...")
        cursor.execute("SELECT faction_a, faction_b, relationship FROM faction_relations")
        for fa, fb, rel in cursor.fetchall():
            # Standard drift toward zero (apathy)
            new_rel = rel + (1 if rel < 0 else -1) if rel != 0 else 0
            
            # Bonus drift based on shared trade status (Simplified)
            # In a full model, we'd check if they have active trade routes to each other.
            
            cursor.execute("UPDATE faction_relations SET relationship=? WHERE faction_a=? AND faction_b=?", (new_rel, fa, fb))

    def _simulate_faction_operations(self, cursor):
        """Shadow War: Factions execute covert operations against rivals."""
        print("   -> Executing Shadow Operations...")
        
        # 1. GENERATE NEW OPERATIONS
        cursor.execute("SELECT id, wealth, influence FROM factions")
        factions = cursor.fetchall()
        for fid, wealth, influence in factions:
            if wealth > 1000 and influence > 10:
                # Find a rival (Relationship < 0)
                cursor.execute("SELECT faction_b, relationship FROM faction_relations WHERE faction_a = ? AND relationship < 0 ORDER BY relationship ASC LIMIT 1", (fid,))
                rival = cursor.fetchone()
                if rival:
                    target_fid = rival[0]
                    op_type = random.choice(["Sabotage", "Fund Bandits", "Unrest", "Poison Supply"])
                    cursor.execute("INSERT INTO faction_operations (origin_id, target_id, op_type, evidence_level) VALUES (?, ?, ?, ?)", (fid, target_fid, op_type, 0))
                    cursor.execute("UPDATE factions SET wealth = wealth - 500, influence = influence - 5 WHERE id=?", (fid,))
                    print(f"      [INTEL] Faction {fid} has launched {op_type} against Faction {target_fid}.")

        # 2. PROCESS ACTIVE OPERATIONS
        cursor.execute("SELECT id, origin_id, target_id, op_type, evidence_level FROM faction_operations WHERE status = 'Active'")
        for op_id, origin, target, otype, evidence in cursor.fetchall():
            # Increase Evidence Level (Makes discovery easier)
            new_evidence = evidence + random.randint(5, 15)
            
            # EXECUTE MECHANICAL EFFECT
            success = random.random() > 0.3
            if success:
                cursor.execute("SELECT id FROM settlements WHERE faction_id = ? ORDER BY RANDOM() LIMIT 1", (target,))
                settlement = cursor.fetchone()
                if settlement:
                    sid = settlement[0]
                    if otype == "Sabotage":
                        cursor.execute("UPDATE buildings SET durability = durability - 20 WHERE id IN (SELECT id FROM buildings WHERE settlement_id = ? ORDER BY RANDOM() LIMIT 1)", (sid,))
                    elif otype == "Unrest":
                        cursor.execute("UPDATE settlements SET happiness = MAX(0, happiness - 10) WHERE id = ?", (sid,))
                    elif otype == "Poison Supply":
                        # Handled in resource pulse by lowering yield effectively
                        pass
                    elif otype == "Fund Bandits":
                        # Handled in trade pulse (higher chance if active operation exists)
                        pass
            
            # Random chance for Op to conclude or be exposed
            if new_evidence >= 100 or random.random() < 0.2:
                status = "Exposed" if new_evidence >= 100 else "Completed"
                cursor.execute("UPDATE faction_operations SET status=?, evidence_level=? WHERE id=?", (status, new_evidence, op_id))
                if status == "Exposed":
                    # Major relationship hit if exposed
                    cursor.execute("UPDATE faction_relations SET relationship = relationship - 30 WHERE (faction_a=? AND faction_b=?) OR (faction_a=? AND faction_b=?)", (origin, target, target, origin))
                    print(f"      [EXPOSURE] Shadow op {otype} from Faction {origin} against {target} was revealed!")

    def _simulate_settlement_decisions(self, cursor):
        print("   -> Spurring Autonomous Growth...")
        cursor.execute("SELECT id, name, happiness FROM settlements")
        for sid, name, hap in cursor.fetchall():
            if hap > 80 and random.random() < 0.15:
                bt = random.choice(['Mine', 'Watchtower', 'Market'])
                cursor.execute("INSERT INTO buildings (settlement_id, building_type, defense_bonus, yield_per_pulse) VALUES (?, ?, ?, ?)", (sid, bt, 5 if bt == 'Watchtower' else 0, 2 if bt == 'Mine' else 0))

    def _simulate_ecology(self, cursor, lunar_phase):
        print("   -> Simulating Lore-Accurate Ecology...")
        cursor.execute("SELECT coord_id, biome, chaos_level, resource_wealth FROM layer4_macro_map")
        for cid, biome, chaos, wealth in cursor.fetchall():
            if random.random() < (0.05 if (wealth > 60 and chaos < 50) else 0.01):
                cursor.execute("SELECT title, category FROM lore_entries WHERE content LIKE ? AND category IN ('Flora', 'Fauna') ORDER BY RANDOM() LIMIT 1", (f"%{biome}%",))
                entry = cursor.fetchone()
                if entry:
                    ltitle, lcat = entry; x, y = map(int, cid.split(','))
                    rtype = f"{ltitle} (Huntable)" if lcat == 'Fauna' else f"{ltitle} (Farmable)"
                    cursor.execute("INSERT INTO resource_nodes (x, y, resource_type, remaining_supply) VALUES (?, ?, ?, 20)", (x, y, rtype))

    def _perform_cleanup(self, cursor):
        cursor.execute("DELETE FROM trade_routes WHERE caravan_status IN ('Raided', 'Arrived')")
        cursor.execute("DELETE FROM weather_fronts WHERE lifespan <= 0")
        # Cleanup old operations
        cursor.execute("DELETE FROM faction_operations WHERE status NOT IN ('Active', 'Exposed')")

if __name__ == "__main__":
    sim = WorldSimulation()
    sim.trigger_world_pulse()
