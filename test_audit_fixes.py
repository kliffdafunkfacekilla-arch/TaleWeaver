import engine
import map_generator
import db_manager
import world_simulation
import os
import json
import sqlite3

def test_interior_stacking():
    print("--- TESTING INTERIOR DEPTH ---")
    state = engine.start_new_game()
    
    # Enter level 1
    engine.enter_interior(state, "Alchemist_Lab")
    print(f"Depth 1: {state['local_map_state']['meta']['region_id']}")
    assert len(state["map_stack"]) == 1
    
    # Enter level 2 (Basement)
    engine.enter_interior(state, "Secret_Vault")
    print(f"Depth 2: {state['local_map_state']['meta']['region_id']}")
    assert len(state["map_stack"]) == 2
    
    # Verify Content (Should have walls)
    walls = [e for e in state["local_map_state"]["entities"] if "wall" in e.get("tags", [])]
    print(f"Walls found in Depth 2: {len(walls)}")
    assert len(walls) > 0
    
    # Exit level 2
    engine.exit_interior(state)
    print(f"Returned to: {state['local_map_state']['meta']['region_id']}")
    assert len(state["map_stack"]) == 1
    assert "Alchemist_Lab" in state['local_map_state']['meta']['region_id']

def test_db_cleanup():
    print("--- TESTING DATABASE CLEANUP ---")
    db_path = "state/shatterlands.db"
    db_manager.init_db()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Insert a fake "Arrived" route
    cursor.execute("INSERT OR REPLACE INTO settlements (id, name, x, y) VALUES (99, 'TestCity', 0, 0)")
    cursor.execute("INSERT INTO trade_routes (source_settlement_id, target_settlement_id, caravan_status) VALUES (99, 99, 'Arrived')")
    
    # Insert an expired storm
    cursor.execute("INSERT INTO weather_fronts (x, y, lifespan) VALUES (0.0, 0.0, 0)")
    conn.commit()
    
    sim = world_simulation.WorldSimulation()
    sim.trigger_world_pulse()
    
    # Check if cleaned
    cursor.execute("SELECT count(*) FROM trade_routes WHERE caravan_status='Arrived'")
    count_routes = cursor.fetchone()[0]
    cursor.execute("SELECT count(*) FROM weather_fronts WHERE lifespan <= 0")
    count_storms = cursor.fetchone()[0]
    
    print(f"Active 'Arrived' Routes: {count_routes} (Expected 0)")
    print(f"Expired Storms: {count_storms} (Expected 0)")
    
    assert count_routes == 0
    assert count_storms == 0
    
    conn.close()

if __name__ == "__main__":
    test_interior_stacking()
    test_db_cleanup()
