import sqlite3
import random
import time
import json
from typing import Dict, List, Any

# Internal relative-friendly imports
import db_manager

class WorldSimulation:
    """
    The World Simulation Engine: Manages macro-level autonomous logic, 
    trade route logistics, resource node decay, and building yields.
    Operates on a 'pulse' system where time shifts global state.
    """
    def __init__(self):
        """Initializes the simulation with a reference to the SQLite database."""
        self.db_path = db_manager.DB_NAME

    def execute_simulation_pulse(self):
        """
        Calculates one 'tick' of global world time.
        Updates trade routes, resource production, and random world disruptions.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            self._simulate_building_yields(cursor)
            self._simulate_trade_and_resources(cursor)
            self._cleanup_stale_trade_routes(cursor)
            conn.commit()
        except sqlite3.Error as e:
            print(f"[Sim Error] Database failure during pulse: {e}")
        finally:
            conn.close()

    def _simulate_building_yields(self, cursor: sqlite3.Cursor):
        """Processes production for all player/faction buildings in settlements."""
        cursor.execute("SELECT settlement_id, resource_generated, yield_per_pulse FROM buildings")
        buildings = cursor.fetchall()
        for b in buildings:
            # logic to add resources to settlement pools would trigger here
            pass

    def _simulate_trade_and_resources(self, cursor: sqlite3.Cursor):
        """
        Handles move/transit status of caravans and resource node depletion.
        Random chance for bandit raids based on 'caravan_status'.
        """
        # Caravan Logic
        cursor.execute("SELECT id, source_settlement_id, target_settlement_id, goods_type FROM trade_routes WHERE caravan_status = 'In Transit'")
        active_routes = cursor.fetchall()
        for route in active_routes:
            if random.random() < 0.05:  # 5% Bandit Raid chance
                cursor.execute("UPDATE trade_routes SET caravan_status = 'Raided' WHERE id = ?", (route[0],))
                print(f"[WorldSim] Trade route {route[0]} was raided by bandits!")
            elif random.random() < 0.2:  # 20% Success chance per pulse
                cursor.execute("UPDATE trade_routes SET caravan_status = 'Delivered' WHERE id = ?", (route[0],))
        
        # Resource Node Decay
        cursor.execute("UPDATE resource_nodes SET remaining_supply = remaining_supply - 1 WHERE remaining_supply > 0")
        cursor.execute("DELETE FROM resource_nodes WHERE remaining_supply <= 0")

    def _cleanup_stale_trade_routes(self, cursor: sqlite3.Cursor):
        """Purges delivered or permanently raided routes to keep the DB lean."""
        cursor.execute("DELETE FROM trade_routes WHERE caravan_status IN ('Delivered', 'Stalled')")
        # Logic to purge trade routes older than X pulses could be added here
