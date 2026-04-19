import requests
import json
import sqlite3
import re
import os
import time

# OSTRAKA WORLD ARCHITECT (ROBUST PLANETARY MODE)
MODEL = "llama3.1:8b-instruct-q3_K_L"
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
DB_PATH = "state/shatterlands.db"
AI_OPTIONS = {"temperature": 0.4, "num_ctx": 8192}

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS entities (name TEXT PRIMARY KEY, category TEXT, raw_lore TEXT, data_json TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS map_layer4 (
        coord_id TEXT PRIMARY KEY, x INTEGER, y INTEGER, 
        n_biome TEXT, s_biome TEXT, e_biome TEXT, w_biome TEXT,
        river_path TEXT, river_start_x INTEGER, river_start_y INTEGER, 
        river_end_x INTEGER, river_end_y INTEGER, river_stability TEXT,
        height_anchor TEXT, zoom_seed TEXT, 
        faction TEXT, sub_faction TEXT, location TEXT, loc_sub_x INTEGER, loc_sub_y INTEGER,
        chaos_level INTEGER DEFAULT 0, resource_wealth INTEGER DEFAULT 50,
        fractal_dna TEXT)''')
    conn.commit()
    conn.close()

def extract_json(text):
    text = re.sub(r'```json\s*', '', text); text = re.sub(r'```', '', text)
    m = re.search(r'\[.*\]', text, re.DOTALL)
    if m: return m.group(0).strip()
    return text.strip()

def generate_macro_map():
    print("\n--- Repairing Planetary Genome ---")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM entities WHERE category LIKE '%faction%'"); factions = [r[0] for r in cursor.fetchall()]

    def safe_str(val): return str(val) if val else ""
    def safe_int(val, default=0): 
        try: return int(val)
        except: return default
    def safe_float(val, default=0.5):
        try: return float(val)
        except: return default

    # TARGETED PASS: Prioritize the Hearth [5,5]
    coords_to_process = [(5,5)]
    # Also add a few neighbors for scale testing
    coords_to_process.extend([(0,0), (9,9)]) 

    for tx, ty in coords_to_process:
        print(f"Synthesizing Planetary DNA for {tx},{ty}...")
        prompt = (f"Architect 1 cell at (x={tx}, y={ty}).\n"
                  f"Return EXACTLY 1 JSON object in a list: [{{...}}]. Reply ONLY with JSON.\n"
                  f"FRACTAL_DNA REQUIREMENTS (PLANETARY scale):\n"
                  f"- geo_seed: unique int\n"
                  f"- geo_frequency: float (0.01 to 0.1)\n"
                  f"- moisture_constant: float (0.0 to 1.0)\n"
                  f"- heat_constant: float (0.0 to 1.0)\n"
                  f"- n_biome, faction (labels)\n")
        
        try:
            res = requests.post(OLLAMA_URL, json={"model": MODEL, "messages": [{"role": "system", "content": "You are a Planetary Architect. Reply ONLY with JSON array."}, {"role": "user", "content": prompt}], "options": AI_OPTIONS, "stream": False}, timeout=120)
            json_text = extract_json(res.json().get('message', {}).get('content', '[]'))
            data = json.loads(json_text)
            for cell in data:
                # ROBUST DNA EXTRACTION
                # Check for nested OR flat keys
                dna_src = cell.get('fractal_dna', cell)
                dna = {
                    "geo_seed": safe_int(dna_src.get('geo_seed'), hash(f"{tx},{ty}")),
                    "geo_frequency": safe_float(dna_src.get('geo_frequency'), 0.05),
                    "moisture_constant": safe_float(dna_src.get('moisture_constant'), 0.5),
                    "heat_constant": safe_float(dna_src.get('heat_constant'), 0.5)
                }
                dna_str = json.dumps(dna)
                
                p = (f"{tx},{ty}", tx, ty, safe_str(cell.get('n_biome')), "none", "none", "none", "none", 0, 0, 0, 0, "stable", "sea_level", "0", safe_str(cell.get('faction')), "sub", "none", 0, 0, 0, 50, dna_str)
                cursor.execute('''INSERT OR REPLACE INTO map_layer4 (coord_id, x, y, n_biome, s_biome, e_biome, w_biome, river_path, river_start_x, river_start_y, river_end_x, river_end_y, river_stability, height_anchor, zoom_seed, faction, sub_faction, location, loc_sub_x, loc_sub_y, chaos_level, resource_wealth, fractal_dna) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', p)
            conn.commit()
            print(f"Success: Planetary DNA for {tx},{ty} synthesized and persisted.")
        except Exception as e:
            print(f"Synthesis failed for {tx},{ty}: {e}")
            
    conn.close()

if __name__ == "__main__":
    init_db(); generate_macro_map()
    print("\n[COMPLETE] Planetary Genome Repaired for Hearth.")
