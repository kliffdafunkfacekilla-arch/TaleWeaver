import requests
import json
import sqlite3
import re
import os
import time

# OSTRAKA WORLD ARCHITECT (STYLIZED & STABLE)
MODEL = "llama3.1:8b-instruct-q3_K_L"
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
DB_PATH = "state/shatterlands.db"
VAULT_PATH = "./Shatterlands"
AI_OPTIONS = {"temperature": 0.4, "num_ctx": 4096}

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
        faction TEXT, sub_faction TEXT, location TEXT, loc_sub_x INTEGER, loc_sub_y INTEGER)''')
    conn.commit()
    conn.close()

def ingest_vault(path):
    print("--- Ingesting Obsidian Vault ---")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for root, _, files in os.walk(path):
        cat = os.path.basename(root)
        for f in files:
            if f.endswith(".md"):
                name = f[:-3]
                with open(os.path.join(root, f), "r", encoding="utf-8") as file:
                    content = file.read()
                cursor.execute("INSERT OR IGNORE INTO entities (name, category, raw_lore) VALUES (?, ?, ?)", (name, cat, content))
    conn.commit()
    conn.close()

def get_chroma_collection():
    try:
        import chromadb
        client = chromadb.PersistentClient(path="./data/lore/.chroma")
        return client.get_or_create_collection(name="ostraka_lore")
    except: return None

def vectorize_all_lore():
    print("--- Verifying Vector Memory ---")
    collection = get_chroma_collection()
    if not collection: return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, category, raw_lore FROM entities")
    rows = cursor.fetchall()
    all_docs, all_metas, all_ids = [], [], []
    for name, cat, lore in rows:
        blocks = [b.strip() for b in lore.split("\n\n") if b.strip()]
        for b in blocks:
            all_docs.append(f"[{cat} - {name}]\n{b}")
            all_metas.append({"title": name, "category": cat})
            all_ids.append(f"{name}_chunk_{len(all_ids)}")
    if all_docs:
        batch_size = 50
        for i in range(0, len(all_docs), batch_size):
            collection.upsert(documents=all_docs[i:i+batch_size], metadatas=all_metas[i:i+batch_size], ids=all_ids[i:i+batch_size])
    conn.close()

def extract_json(text):
    text = re.sub(r'```json\s*', '', text); text = re.sub(r'```', '', text)
    m = re.search(r'\[.*\]', text, re.DOTALL)
    if m: return m.group(0).strip()
    return text.strip()

def process_build_list_via_rag():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, category FROM entities WHERE data_json IS NULL")
    rows = cursor.fetchall()
    collection = get_chroma_collection()
    if not rows or not collection:
        print("--- Lore Completion: 100% ---")
        conn.close(); return
    for name, category in rows:
        try:
            results = collection.query(query_texts=[name], n_results=3)
            context = "\n---\n".join(results['documents'][0])
            payload = {"model": MODEL, "messages": [{"role": "system", "content": "Return raw JSON."}, {"role": "user", "content": f"Context for {name}:\n{context}\nKeys: 'behavior', 'threat_tier', 'preferred_biome'."}], "options": AI_OPTIONS, "stream": False}
            response = requests.post(OLLAMA_URL, json=payload, timeout=30)
            raw_text = extract_json(response.json().get('message', {}).get('content', '{}'))
            cursor.execute("UPDATE entities SET data_json = ? WHERE name = ?", (raw_text, name))
            conn.commit()
            print(f"Syncing: {name}")
        except: pass
    conn.close()

def generate_macro_map():
    print("\n--- Architecting World Grid (Final Healing Run) ---")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM entities WHERE category LIKE '%faction%'"); factions = [r[0] for r in cursor.fetchall()]
    cursor.execute("SELECT name FROM entities WHERE category LIKE '%location%'"); locations = [r[0] for r in cursor.fetchall()]

    def safe_str(val): return str(val) if val else ""
    def safe_int(val, default=0): 
        try: return int(val)
        except: return default

    for y in range(10):
        for x_start in range(0, 10, 2):
            cursor.execute("SELECT count(*) FROM map_layer4 WHERE y = ? AND x IN (?, ?)", (y, x_start, x_start + 1))
            if cursor.fetchone()[0] == 2: continue

            for attempt in range(3):
                print(f"Architecting Row {y}, Cells ({x_start}-{x_start+1})... (Attempt {attempt+1})")
                prompt = (f"Architect 2 cells for Row {y} (x={x_start} and x={x_start+1}).\nFactions: {factions[:5]}...\nLocations: {locations[:5]}...\n"
                          f"Return exactly 2 JSON objects in a list. NO COMMENTARY.")
                try:
                    res = requests.post(OLLAMA_URL, json={"model": MODEL, "messages": [{"role": "system", "content": "Return ONLY a JSON array of 2 objects."}, {"role": "user", "content": prompt}], "options": AI_OPTIONS, "stream": False}, timeout=45)
                    data = json.loads(extract_json(res.json().get('message', {}).get('content', '[]')))
                    for i, cell in enumerate(data):
                        # FORCE COORDINATES TO PREVENT OVERWRITES
                        target_x = x_start + i
                        if target_x > x_start + 1: continue 
                        p = (f"{target_x},{y}", target_x, y, safe_str(cell.get('n_biome')), safe_str(cell.get('s_biome')), safe_str(cell.get('e_biome')), safe_str(cell.get('w_biome')), safe_str(cell.get('river_path')), safe_int(cell.get('river_start_x')), safe_int(cell.get('river_start_y')), safe_int(cell.get('river_end_x')), safe_int(cell.get('river_end_y')), safe_str(cell.get('river_stability')), safe_str(cell.get('height_anchor')), safe_str(cell.get('zoom_seed')), safe_str(cell.get('faction')), safe_str(cell.get('sub_faction')), safe_str(cell.get('location')), safe_int(cell.get('loc_sub_x')), safe_int(cell.get('loc_sub_y')))
                        cursor.execute('''INSERT OR REPLACE INTO map_layer4 (coord_id, x, y, n_biome, s_biome, e_biome, w_biome, river_path, river_start_x, river_start_y, river_end_x, river_end_y, river_stability, height_anchor, zoom_seed, faction, sub_faction, location, loc_sub_x, loc_sub_y) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', p)
                    conn.commit()
                    print(f"Success: Row {y}, Cells ({x_start}-{x_start+1}) saved.")
                    break
                except Exception as e:
                    print(f"Attempt failed: {e}"); time.sleep(2.0)
    conn.close()

if __name__ == "__main__":
    init_db(); generate_macro_map()
    print("\n[COMPLETE] World finalized.")
