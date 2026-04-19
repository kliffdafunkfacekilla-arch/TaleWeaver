import sqlite3
import requests
import json
import os
import time
import re

DB_PATH = "state/shatterlands.db"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.1:8b-instruct-q3_K_L"

def generate_lore_text(category, biome, count=5):
    """Uses Ollama to generate lore text with manual parsing (no forced JSON)."""
    prompt = f"""
    Generate {count} unique {category} for a fantasy world called Ostraka.
    Each entry must be perfectly suited for the '{biome}' biome.
    
    For each entry, provide:
    NAME: [Evocative Name]
    DESC: [2-sentence description]
    YIELD: [What a settlement gets if they hunt/farm it]
    ---
    """
    
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }
    
    for attempt in range(3):
        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=180)
            response.raise_for_status()
            return response.json()["response"]
        except Exception as e:
            print(f"   [RETRY {attempt+1}] Error: {e}")
            time.sleep(3)
    return ""

def parse_lore_text(text, biome, category):
    """Parses the generated text into structured objects."""
    items = []
    # Split by the separator ---
    blocks = text.split("---")
    for block in blocks:
        name_match = re.search(r"NAME:\s*(.*)", block)
        desc_match = re.search(r"DESC:\s*(.*)", block)
        yield_match = re.search(r"YIELD:\s*(.*)", block)
        
        if name_match:
            title = name_match.group(1).strip()
            desc = desc_match.group(1).strip() if desc_match else ""
            res_yield = yield_match.group(1).strip() if yield_match else "Common Reagent"
            
            content = f"Biome: {biome}. {desc} Harvest Yield: {res_yield}."
            items.append({
                "title": title,
                "category": category,
                "content": content,
                "meta": {"biome": biome, "yield": res_yield}
            })
    return items

def populate_ecology():
    """Populates the lore vault using stable text generation."""
    biomes = ['Oceanic', 'Tropical', 'Forest', 'Terra']
    categories = ['Flora', 'Fauna']
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("Initiating Robust Ecological Synthesis...")
    
    total_added = 0
    for cat in categories:
        for biome in biomes:
            print(f"   -> Manifesting {cat} for {biome}...")
            raw_text = generate_lore_text(cat, biome, count=10)
            parsed_items = parse_lore_text(raw_text, biome, cat)
            
            for item in parsed_items:
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO lore_entries (title, category, content, parameters)
                        VALUES (?, ?, ?, ?)
                    ''', (item['title'], item['category'], item['content'], json.dumps(item['meta'])))
                    total_added += 1
                except Exception as e:
                    print(f"      [FAILURE] {item['title']}: {e}")
            
            conn.commit() # Commit after each biome
            print(f"      [SUCCESS] Manifested {len(parsed_items)} {cat} entries.")
    
    conn.close()
    print(f"Synthesis Complete. {total_added} biological legends added to the Vault.")

if __name__ == "__main__":
    populate_ecology()
