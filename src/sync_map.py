import sqlite3

DB_PATH = "state/shatterlands.db"

def sync_ai_to_engine():
    print("--- Bridging AI Fractal Map to Engine Bridge ---")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Fetch all data from the high-precision AI table, including Fractal DNA
    cursor.execute("SELECT coord_id, n_biome, faction, location, chaos_level, fractal_dna FROM map_layer4")
    rows = cursor.fetchall()
    
    for rid, biome, faction, location, chaos, dna in rows:
        cursor.execute('''
            INSERT INTO layer4_macro_map (coord_id, biome, faction, location, chaos_level, fractal_dna) 
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(coord_id) DO UPDATE SET 
                biome=excluded.biome, 
                faction=excluded.faction, 
                location=excluded.location, 
                chaos_level=excluded.chaos_level,
                fractal_dna=excluded.fractal_dna
        ''', (rid, biome, faction, location, chaos, dna))
    
    conn.commit()
    conn.close()
    print(f"Success! Bridged {len(rows)} fractal coordinates to Engine Table.")

if __name__ == "__main__":
    sync_ai_to_engine()
