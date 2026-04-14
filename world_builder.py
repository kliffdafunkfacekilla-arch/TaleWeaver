import streamlit as st
import os
import re
import json
import sqlite3

# 1. SETUP
st.set_page_config(page_title="Ostraka Architect", layout="wide")
st.title("⚙️ The World Architect: Ostraka")

# 2. THE HARVESTER LOGIC
def parse_obsidian_vault(vault_path):
    """Recursively walks the vault to extract lore using multi-tiered parsing and keyword heuristics."""
    harvested_data = []
    
    if not os.path.exists(vault_path):
        st.sidebar.error(f"Path not found: {vault_path}")
        return []
        
    for root, dirs, files in os.walk(vault_path):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                title = file[:-3] # Strip .md extension
                
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    # TIER 1: TAG EXTRACTION
                    tag_match_inline = re.search(r"tags:\s*\[(.*?)\]", content)
                    tag_match_multi = re.search(r"tags:\s*\n((?:\s*-\s*\S+\n?)+)", content)
                    
                    tags = []
                    if tag_match_inline:
                        tags_str = tag_match_inline.group(1)
                        tags = [t.strip() for t in tags_str.split(",") if t.strip()]
                    elif tag_match_multi:
                        tags_lines = tag_match_multi.group(1).split("\n")
                        tags = [t.replace("-", "").strip() for t in tags_lines if t.strip()]
                    
                    # TIER 2: KEYWORD HEURISTICS (Smart Fallback)
                    category = "Uncategorized Lore"
                    text_sample = content[:1000].lower()
                    tags_lower = [t.lower() for t in tags]
                    
                    if any(t in tags_lower for t in ["npc", "character", "individual", "person"]):
                        category = "NPCs"
                    elif any(t in tags_lower for t in ["faction", "factions", "empire", "guild", "cult"]):
                        category = "Factions"
                    elif any(t in tags_lower for t in ["fauna", "flora", "beast", "plant", "creature", "monster"]):
                        category = "Fauna & Flora"
                    elif any(t in tags_lower for t in ["location", "city", "region", "dungeon", "landmark"]):
                        category = "Locations"
                    elif any(t in tags_lower for t in ["magic", "tech", "technology", "lore", "history"]):
                        category = "Lore/Tech"

                    if category == "Uncategorized Lore":
                        if any(k in text_sample for k in ["scientific designation", "biology & appearance", "habitat:"]):
                            category = "Fauna & Flora"
                        elif any(k in text_sample for k in ["faction profile", "society", "culture:", "overview: the"]):
                            category = "Factions"
                        elif any(k in text_sample for k in ["region:", "location:", "geography:", "architecture:"]):
                            category = "Locations"
                        elif any(k in text_sample for k in ["school of", "power:", "magic"]):
                            category = "Lore/Tech"
                        elif any(k in text_sample for k in ["he ", "she ", "they ", "born ", "age:"]): 
                            category = "NPCs"
                    
                    harvested_data.append({
                        "title": title,
                        "category": category,
                        "tags": tags,
                        "lore": content
                    })
                except Exception as e:
                    st.error(f"Could not parse {file}: {e}")
                    
    return harvested_data

# DATABASE MODULE
def init_lore_db(db_name="state/shatterlands.db"):
    """Initializes the lore table in the engine's database."""
    os.makedirs(os.path.dirname(db_name), exist_ok=True)
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lore_entries (
            title TEXT PRIMARY KEY,
            category TEXT,
            content TEXT
        )
    ''')
    conn.commit()
    conn.close()

def export_lore_to_db(harvested_data, db_name="state/shatterlands.db"):
    """Saves harvested lore to the database using UPSERT logic."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # Prepping data for executemany (title, category, content)
    data_to_upsert = [(item['title'], item['category'], item['lore']) for item in harvested_data]
    
    cursor.executemany('''
        INSERT INTO lore_entries (title, category, content)
        VALUES (?, ?, ?)
        ON CONFLICT(title) DO UPDATE SET 
            category=excluded.category, 
            content=excluded.content
    ''', data_to_upsert)
    
    conn.commit()
    conn.close()

# 3. THE STREAMLIT UI (Sidebar & Ingestion)
vault_path = st.sidebar.text_input("Obsidian Vault Path", "./Shatterlands")

if st.sidebar.button("Sync with Obsidian"):
    with st.spinner("Harvesting Lore..."):
        data = parse_obsidian_vault(vault_path)
        if data:
            st.session_state['harvested_data'] = data
            st.sidebar.success(f"Vault Ingested! ({len(data)} items)")
        else:
            st.sidebar.warning("No files found or path invalid.")

# Database Export Section
st.sidebar.markdown("---")
st.sidebar.subheader("Export to Engine")
if st.sidebar.button("Generate Lore Database"):
    if 'harvested_data' in st.session_state and st.session_state['harvested_data']:
        try:
            init_lore_db()
            export_lore_to_db(st.session_state['harvested_data'])
            st.sidebar.success("state/shatterlands.db updated successfully! The game engine can now read this lore.")
        except Exception as e:
            st.sidebar.error(f"Database error: {e}")
    else:
        st.sidebar.error("No data to export. Sync with Obsidian first.")

# 4. DISPLAYING THE DATA (Categorized Tabs)
if 'harvested_data' in st.session_state:
    data_list = st.session_state['harvested_data']
    tab_list = ["Factions", "NPCs", "Fauna & Flora", "Locations", "Lore/Tech", "Uncategorized Lore"]
    tabs = st.tabs(tab_list)
    
    categorized_data = {tab_name: [] for tab_name in tab_list}
    for item in data_list:
        cat = item.get("category", "Uncategorized Lore")
        if cat in categorized_data:
            categorized_data[cat].append(item)
        else:
            categorized_data["Uncategorized Lore"].append(item)

    for i, tab_name in enumerate(tab_list):
        with tabs[i]:
            items = categorized_data[tab_name]
            if not items:
                st.info(f"No items discovered in {tab_name}.")
            else:
                for item in items:
                    st.subheader(item['title'])
                    if item['tags']:
                        st.caption(f"🏷️ Tags: {', '.join(item['tags'])}")
                    
                    with st.expander("View Source Lore"):
                        st.markdown(item['lore'])
                    st.divider()
else:
    st.info("👈 Enter your Obsidian Vault path and click 'Sync' to begin.")
