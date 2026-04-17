import sqlite3
import json

DB_PATH = "state/shatterlands.db"

BIOME_CLEAN = {
    "Verdant Tangle": "Pine Forest",
    "Swamp-Mire": "Swamp",
    "High Peaks": "Mountain",
    "Dust Bowl": "Desert",
    "Grind-Canyons": "Canyons"
}

def sync():
    print("--- Bridging AI Map to Engine Table ---")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if target exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='layer4_macro_map'")
    if not cursor.fetchone():
        print("Error: Engine map table not found. Run Architect app first to init.")
        return

    # Fetch all AI data
    cursor.execute("SELECT x, y, n_biome, faction, location, height_anchor FROM map_layer4")
    rows = cursor.fetchall()
    
    count = 0
    for x, y, biome, faction, location, height in rows:
        coord_id = f"{x},{y}"
        
        # Mapping Logic
        clean_biome = BIOME_CLEAN.get(biome, biome)
        # Convert text elevation to simple integer
        elevation = 0
        h_lower = str(height).lower()
        if "mountain" in h_lower or "peak" in h_lower or "high" in h_lower: elevation = 5
        elif "low" in h_lower or "pit" in h_lower: elevation = -2
        elif "hill" in h_lower: elevation = 2

        cursor.execute('''
            INSERT INTO layer4_macro_map (coord_id, biome, faction, location, chaos_level, elevation)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(coord_id) DO UPDATE SET 
                biome=excluded.biome, 
                faction=excluded.faction,
                location=excluded.location,
                elevation=excluded.elevation
        ''', (coord_id, clean_biome, faction, location, 0, elevation))
        count += 1
    
    conn.commit()
    conn.close()
    print(f"Success! Sync'd {count} coordinates to Engine Bridge.")

if __name__ == "__main__":
    sync()
