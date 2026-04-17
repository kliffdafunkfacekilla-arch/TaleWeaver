import streamlit as st
import os
import re
import json
import sqlite3
import pandas as pd
import streamlit.components.v1 as components
import chromadb
import subprocess

# 1. SETUP
st.set_page_config(page_title="Ostraka Architect", layout="wide")
st.title("⚙️ The World Architect: Ostraka")

# DATABASE & VECTOR STORE SETUP
DB_PATH = "state/shatterlands.db"
CHROMA_PATH = "./data/lore/.chroma"

def init_lore_db(db_name=DB_PATH):
    """Initializes the lore table in the engine's database with parameter support."""
    os.makedirs(os.path.dirname(db_name), exist_ok=True)
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lore_entries'")
    if not cursor.fetchone():
        cursor.execute('''
            CREATE TABLE lore_entries (
                title TEXT PRIMARY KEY,
                category TEXT,
                content TEXT,
                parameters TEXT
            )
        ''')
    else:
        # Migration: Check if parameters column exists
        cursor.execute("PRAGMA table_info(lore_entries)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'parameters' not in columns:
            cursor.execute("ALTER TABLE lore_entries ADD COLUMN parameters TEXT")

    # Table 2: Layer 4 Macro Map
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='layer4_macro_map'")
    if not cursor.fetchone():
        cursor.execute('''
            CREATE TABLE layer4_macro_map (
                coord_id TEXT PRIMARY KEY,
                biome TEXT,
                faction TEXT,
                location TEXT,
                chaos_level INTEGER,
                elevation INTEGER DEFAULT 0
            )
        ''')
    else:
        # Migration: Check if elevation column exists
        cursor.execute("PRAGMA table_info(layer4_macro_map)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'elevation' not in columns:
            cursor.execute("ALTER TABLE layer4_macro_map ADD COLUMN elevation INTEGER DEFAULT 0")
            
    conn.commit()
    conn.close()

# Initialize ChromaDB Client
os.makedirs(os.path.dirname(CHROMA_PATH), exist_ok=True)
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = chroma_client.get_or_create_collection(name="ostraka_lore")

def load_all_lore_parameters(db_name=DB_PATH):
    """Reloads existing parameters from DB to preserve manual tuning during sync."""
    if not os.path.exists(db_name): return {}
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT title, parameters, category FROM lore_entries")
        data = {row[0]: {"params": json.loads(row[1]) if row[1] else {}, "category": row[2]} for row in cursor.fetchall()}
        conn.close()
        return data
    except:
        return {}

def save_single_entry(title, category, content, parameters, db_name=DB_PATH):
    """Saves or updates a single lore entry with its mechanical parameters."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    params_json = json.dumps(parameters)
    cursor.execute('''
        INSERT INTO lore_entries (title, category, content, parameters)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(title) DO UPDATE SET 
            category=excluded.category, 
            content=excluded.content,
            parameters=excluded.parameters
    ''', (title, category, content, params_json))
    conn.commit()
    conn.close()

def save_macro_map(grid_data, db_name=DB_PATH):
    """Saves the entire Layer 4 macro grid into the database."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    for coord_id, data in grid_data.items():
        # Safeguard: ensure data has all keys
        biome = data.get('Biome', 'Ocean')
        faction = data.get('Faction', 'None')
        location = data.get('Location', 'None')
        elevation = data.get('Elevation', 0)
        chaos = data.get('Chaos', 0)
        
        cursor.execute('''
            INSERT INTO layer4_macro_map (coord_id, biome, faction, location, chaos_level, elevation)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(coord_id) DO UPDATE SET 
                biome=excluded.biome, 
                faction=excluded.faction,
                location=excluded.location,
                chaos_level=excluded.chaos_level,
                elevation=excluded.elevation
        ''', (coord_id, biome, faction, location, chaos, elevation))
        
    conn.commit()
    conn.close()

def load_macro_map(db_name=DB_PATH):
    """Reloads the entire Layer 4 macro grid from the database."""
    if not os.path.exists(db_name): return {}
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT coord_id, biome, faction, location, chaos_level, elevation FROM layer4_macro_map")
        rows = cursor.fetchall()
        conn.close()
        
        mapping = {}
        for r in rows:
            mapping[r[0]] = {
                "Biome": r[1], 
                "Faction": r[2], 
                "Location": r[3], 
                "Chaos": r[4],
                "Elevation": r[5] if r[5] is not None else 0
            }
        return mapping
    except:
        return {}

# 2. THE HARVESTER LOGIC
def parse_obsidian_vault(vault_path):
    """Recursively walks the vault and merges existing DB parameters with fresh Obsidian content."""
    harvested_data = []
    if not os.path.exists(vault_path):
        st.sidebar.error(f"Path not found: {vault_path}")
        return []
        
    db_data = load_all_lore_parameters()
    for root, dirs, files in os.walk(vault_path):
        folder_name = os.path.basename(root).lower()
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                title = file[:-3]
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        raw_lore = f.read()
                    category = "Uncategorized"
                    if "faction" in folder_name: category = "Factions (Empires)"
                    elif "culture" in folder_name: category = "Cultures (NPCs & Enemies)"
                    elif "resource" in folder_name: category = "Resources (Economy)"
                    elif "fauna" in folder_name or "flora" in folder_name: category = "Ecosystem (Flora & Fauna)"
                    elif "location" in folder_name: category = "Locations"
                    elif "tech" in folder_name: category = "Tech & Items"
                    elif "organization" in folder_name or "organisation" in folder_name: category = "Organizations (Guilds & Cults)"
                    elif any(kw in folder_name for kw in ["magic", "chaos", "people", "history"]): category = "Lore & Cosmology"
                    harvested_data.append({
                        "title": title,
                        "category": category,
                        "lore": raw_lore,
                        "parameters": db_data.get(title, {}).get("params", {})
                    })
                except Exception as e:
                    st.error(f"Could not parse {file}: {e}")
    return harvested_data

# 3. AI KNOWLEDGE COMPILER (RAG)
def chunk_markdown_text(text, title, category):
    """Splits markdown into semantic chunks based on headers."""
    header_pattern = r'(?m)^#+\s+(.*)$'
    header_matches = list(re.finditer(header_pattern, text))
    
    chunks = []
    if not header_matches:
        # Fallback: split by double newline
        blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
        for b in blocks:
            chunks.append({
                "text": f"[{category} - {title}]\n{b}",
                "metadata": {"title": title, "category": category}
            })
    else:
        if header_matches[0].start() > 0:
            initial_text = text[:header_matches[0].start()].strip()
            if initial_text:
                chunks.append({
                    "text": f"[{category} - {title}]\n{initial_text}",
                    "metadata": {"title": title, "category": category}
                })
        
        for i, match in enumerate(header_matches):
            header_text = match.group(1).strip()
            start_pos = match.end()
            end_pos = header_matches[i+1].start() if i+1 < len(header_matches) else len(text)
            content = text[start_pos:end_pos].strip()
            
            if content:
                chunks.append({
                    "text": f"[{category} - {title} - {header_text}]\n{content}",
                    "metadata": {"title": title, "category": category, "header": header_text}
                })
    return chunks

def vectorize_lore_to_chroma(harvested_data):
    """Chunks and upserts data into the local ChromaDB vector store."""
    all_texts, all_metadatas, all_ids = [], [], []
    
    for item in harvested_data:
        chunks = chunk_markdown_text(item['lore'], item['title'], item['category'])
        for i, chunk in enumerate(chunks):
            all_texts.append(chunk['text'])
            all_metadatas.append(chunk['metadata'])
            all_ids.append(f"{item['title']}_chunk_{i}")
    
    if all_texts:
        collection.upsert(documents=all_texts, metadatas=all_metadatas, ids=all_ids)
    return len(all_texts)

# 4. THE CARTOGRAPHER JS COMPONENT
HTML_GRID_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: 'Inter', sans-serif; background: transparent; margin: 0; padding: 0; }
        .grid-container { display: flex; flex-direction: column; align-items: center; gap: 15px; }
        .grid { 
            display: grid; 
            grid-template-columns: repeat(10, 1fr); 
            gap: 2px; 
            background: #2b2d31; 
            padding: 5px;
            border-radius: 8px;
            width: 500px; 
            height: 500px; 
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
        }
        .cell { 
            background: #111; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            cursor: crosshair; 
            font-size: 11px; 
            color: rgba(255,255,255,0.8); 
            border-radius: 2px;
            transition: all 0.1s ease;
            user-select: none;
        }
        .cell:hover { transform: scale(1.05); z-index: 10; outline: 2px solid white; box-shadow: 0 0 10px rgba(255,255,255,0.5); }
        .commit-btn { 
            padding: 12px 24px; 
            background: #4a7a4a; 
            color: white; 
            border: none; 
            cursor: pointer; 
            font-weight: bold; 
            border-radius: 6px; 
            transition: background 0.2s;
            width: 100%;
        }
        .commit-btn:hover { background: #5a8a5a; }
        .legend { font-size: 12px; color: #aaa; margin-bottom: 5px; }
    </style>
</head>
<body>
    <div class="grid-container">
        <div class="legend">AI World Seed View. Click cells to edit.</div>
        <div id="grid" class="grid"></div>
        <button id="commit" class="commit-btn">💾 COMMIT SEED TO STATE</button>
    </div>
    <script>
        const BIOME_COLORS = {
            "Ocean": "#1a2a4a", "Shallow Water": "#3a5a8a", "Plains": "#4a7a4a", 
            "Forest": "#1a4a1a", "Desert": "#a68a4a", "Mountain": "#4a4a4a", 
            "Grind-Canyons": "#7a4a2a", "Swamp-Mire": "#2a3a2a", "Verdant Tangle": "#1a6a2a", 
            "High Peaks": "#d0d0d0", "Chaos Zone": "#4a004a", "Crystal Canyons": "#004a4a", "Fungal Forests": "#4a4a00",
            "Canyons": "#7a4a2a", "Pine Forest": "#1a4a1a", "Swamp": "#2a3a2a"
        };

        const gridEl = document.getElementById('grid');
        const commitBtn = document.getElementById('commit');
        let gridData = {};
        let currentBrush = {};

        function sendMessage(data) {
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                value: data,
            }, '*');
        }

        window.addEventListener('message', (event) => {
            if (event.data.type === 'streamlit:render') {
                const {brush, initial_data} = event.data.args;
                currentBrush = brush;
                if (Object.keys(gridData).length === 0 && initial_data) {
                    initGrid(initial_data);
                }
            }
        });

        function initGrid(data) {
            gridData = data;
            gridEl.innerHTML = '';
            for (let y = 0; y < 10; y++) {
                for (let x = 0; x < 10; x++) {
                    const key = `${x},${y}`;
                    const cell = document.createElement('div');
                    cell.className = 'cell';
                    updateCellUI(cell, gridData[key]);
                    cell.onclick = () => {
                        gridData[key] = { ...currentBrush };
                        updateCellUI(cell, gridData[key]);
                    };
                    gridEl.appendChild(cell);
                }
            }
        }

        function updateCellUI(el, info) {
            el.style.backgroundColor = BIOME_COLORS[info.Biome] || '#111';
            el.title = `${info.Biome} | Elev: ${info.Elevation} | Faction: ${info.Faction} | Loc: ${info.Location}`;
            let icon = info.Elevation > 0 ? '▲' : (info.Elevation < 0 ? '▼' : '—');
            if (info.Elevation === 5) icon = '🏔️';
            if (info.Elevation === -5) icon = '🕳️';
            el.innerHTML = `<span>${icon}<br>${info.Elevation}</span>`;
            el.style.textAlign = 'center';
        }

        commitBtn.onclick = () => sendMessage(gridData);
    </script>
</body>
</html>
"""

def cartographer_grid(brush, initial_data):
    comp_dir = "cartographer_component"
    if not os.path.exists(comp_dir): os.makedirs(comp_dir)
    with open(os.path.join(comp_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(HTML_GRID_TEMPLATE)
    _component_func = components.declare_component("cartographer_grid", path=comp_dir)
    return _component_func(brush=brush, initial_data=initial_data, default=None)

# 5. THE STREAMLIT UI
init_lore_db()

if 'macro_map' not in st.session_state:
    existing_map = load_macro_map()
    st.session_state['macro_map'] = {
        f"{x},{y}": {"Biome": "Ocean", "Faction": "None", "Location": "None", "Chaos": 0, "Elevation": 0} 
        for x in range(10) for y in range(10)
    }
    if existing_map:
        st.session_state['macro_map'].update(existing_map)

vault_path = st.sidebar.text_input("Obsidian Vault Path", "./Shatterlands")

if st.sidebar.button("Sync with Obsidian"):
    with st.spinner("Harvesting Lore..."):
        data = parse_obsidian_vault(vault_path)
        if data:
            st.session_state['harvested_data'] = data
            st.sidebar.success(f"Vault Ingested!")
        else:
            st.sidebar.warning("No files found or path invalid.")

st.sidebar.markdown("---")
st.sidebar.subheader("Global Control")
if st.sidebar.button("Full Database Rebuild"):
    if 'harvested_data' in st.session_state:
        for item in st.session_state['harvested_data']:
            save_single_entry(item['title'], item['category'], item['lore'], item.get('parameters', {}))
        st.sidebar.success("Global database rebuild complete!")

st.sidebar.markdown("---")
st.sidebar.subheader("Coordinate Engine")
if st.sidebar.button("🌟 LOAD AI GENERATED WORLD SEED"):
    with st.spinner("Importing AI Seed from Precision Database..."):
        subprocess.run(["python", "sync_map.py"])
        st.session_state['macro_map'] = load_macro_map()
        st.sidebar.success("AI Seed successfully bridged to engine!")
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("Export to Engine")
if st.sidebar.button("🧠 Build AI Vector Database (ChromaDB)"):
    if 'harvested_data' in st.session_state:
        with st.spinner("Chunking and embedding lore for the AI..."):
            count = vectorize_lore_to_chroma(st.session_state['harvested_data'])
            st.sidebar.success(f"Vectorized {count} chunks into ChromaDB!")
    else:
        st.sidebar.error("Please 'Sync with Obsidian' first to load the raw lore content.")

# 6. DISPLAYING DATA
if 'harvested_data' in st.session_state:
    data_list = st.session_state['harvested_data']
    tab_list = ["Factions (Empires)", "Cultures (NPCs & Enemies)", "Organizations (Guilds & Cults)", "Resources (Economy)", "Ecosystem (Flora & Fauna)", "Locations", "Tech & Items", "Lore & Cosmology", "The Cartographer", "Uncategorized"]
    tabs = st.tabs(tab_list)
    
    categorized_data = {tab_name: [] for tab_name in tab_list}
    for item in data_list:
        cat = item['category']
        if cat in categorized_data: categorized_data[cat].append(item)
        else: categorized_data["Uncategorized"].append(item)

    for i, tab_name in enumerate(tab_list):
        with tabs[i]:
            if tab_name == "The Cartographer":
                col1, col2 = st.columns([1, 2.5])
                with col1:
                    st.subheader("🖌️ Brush Parameters")
                    paint_biome = st.selectbox("Select Biome", ["Ocean", "Shallow Water", "Plains", "Forest", "Desert", "Mountain", "Grind-Canyons", "Swamp-Mire", "Verdant Tangle", "High Peaks", "Chaos Zone", "Crystal Canyons", "Fungal Forests"])
                    paint_elevation = st.selectbox("Paint Elevation", list(range(-5, 6)), index=5)
                    paint_faction = st.selectbox("Assign Faction", ["None"] + [item['title'] for item in data_list if item['category'] == "Factions (Empires)"])
                    paint_location = st.selectbox("Place Location", ["None"] + [item['title'] for item in data_list if item['category'] == "Locations"])
                    st.info("💡 Adjust brush then click on cells in the grid to paint.")
                    st.divider()
                    if st.button("💾 Force DB Save"):
                        save_macro_map(st.session_state['macro_map'])
                        st.success("Session map committed to DB.")
                with col2:
                    st.subheader("🗺️ 10x10 Overworld AI Grid")
                    brush_state = {"Biome": paint_biome, "Elevation": paint_elevation, "Faction": paint_faction, "Location": paint_location, "Chaos": 0}
                    captured_grid = cartographer_grid(brush=brush_state, initial_data=st.session_state['macro_map'])
                    if captured_grid:
                        st.session_state['macro_map'] = captured_grid
                        save_macro_map(captured_grid)
                        st.toast("✅ Map state updated.")
            else:
                items = categorized_data[tab_name]
                if not items:
                    st.info(f"No files discovered in folder: {tab_name}")
                else:
                    for item in items:
                        st.subheader(item['title'])
                        with st.expander("📖 View Source Data"):
                            st.write(item['lore'])
                        with st.expander("View/Edit Data", expanded=False):
                            game_stats = item.get("parameters", {})
                            if tab_name == "Factions (Empires)":
                                trade_opts = ["Never", "Friends Only (If friendly needs it)", "Excess (Will sell extras)", "Priority (Trade anything to anyone)"]
                                agg_opts = ["Passive (Defend/Negotiate only)", "Defensive (Defend/Counter-attack/Negotiate)", "Need (Negotiate first, War if needed)", "Bully (Force over talks, take what it wants)", "Bloodthirsty (Immediate force against anyone)"]
                                game_stats['trade_policy'] = st.selectbox("Trade Policy", trade_opts, index=trade_opts.index(game_stats.get('trade_policy', trade_opts[0])) if game_stats.get('trade_policy') in trade_opts else 0, key=f"{item['title']}_trade")
                                game_stats['aggression_policy'] = st.selectbox("Aggression Policy", agg_opts, index=agg_opts.index(game_stats.get('aggression_policy', agg_opts[1])) if game_stats.get('aggression_policy') in agg_opts else 1, key=f"{item['title']}_agg")
                                c1, c2, c3 = st.columns(3)
                                game_stats['wealth'] = c1.slider("Starting Wealth", 1, 100, game_stats.get('wealth', 50), key=f"{item['title']}_wealth")
                                game_stats['drive'] = c2.slider("Starting Drive", 1, 100, game_stats.get('drive', 50), key=f"{item['title']}_drive")
                                game_stats['tech_level'] = c3.slider("Starting Tech Level", 1, 100, game_stats.get('tech_level', 10), key=f"{item['title']}_tech")
                            elif tab_name == "Cultures (NPCs & Enemies)":
                                disp_opts = ["Friendly NPC", "Hostile Enemy"]
                                var_opts = ["Body-Variant (Physical Focus)", "Mind-Variant (Mental Focus)"]
                                c1, c2 = st.columns(2)
                                game_stats['disposition'] = c1.selectbox("Entity Disposition", disp_opts, index=disp_opts.index(game_stats.get('disposition', disp_opts[0])) if game_stats.get('disposition') in disp_opts else 0, key=f"{item['title']}_disp")
                                game_stats['variant'] = c2.selectbox("Biological Variant", var_opts, index=var_opts.index(game_stats.get('variant', var_opts[0])) if game_stats.get('variant') in var_opts else 0, key=f"{item['title']}_var")
                                c1, c2 = st.columns(2)
                                game_stats['threat'] = c1.number_input("Threat Level / Tier", 1, 5, game_stats.get('threat', 1), key=f"{item['title']}_threat")
                                game_stats['skill'] = c2.text_input("Signature Skill / Tactic", game_stats.get('skill', "Basic Strike"), key=f"{item['title']}_skill")
                                game_stats['tags'] = st.text_input("Mechanic Tags (Comma separated)", game_stats.get('tags', "flesh, organic"), key=f"{item['title']}_tags")
                                c1, c2, c3, c4 = st.columns(4)
                                game_stats['hp'] = c1.number_input("Base HP", 0, 500, game_stats.get('hp', 20), key=f"{item['title']}_hp")
                                game_stats['composure'] = c2.number_input("Base Composure", 0, 500, game_stats.get('composure', 15), key=f"{item['title']}_comp")
                                game_stats['stamina'] = c3.number_input("S-Die (Stamina)", 1, 20, game_stats.get('stamina', 10), key=f"{item['title']}_stam")
                                game_stats['focus'] = c4.number_input("F-Die (Focus)", 1, 20, game_stats.get('focus', 10), key=f"{item['title']}_focus")
                            elif tab_name == "Organizations (Guilds & Cults)":
                                motive_opts = ["Helpful", "Profit", "Power", "Destruction", "Beneficial", "Religion", "Social"]
                                tactic_opts = ["Violence", "Manipulation", "Negotiation/Protest", "Long Game", "Financial", "Magic", "Chaos"]
                                db_data_org = load_all_lore_parameters()
                                factions = [f_title for f_title, f_data in db_data_org.items() if f_data['category'] == "Factions (Empires)"]
                                base_factions = ["None (Global / Unlocked)", "Avian Empire", "Iron Caldera", "Heartland Alliance", "Sump-Kin Wetlands", "Scute Confederacy", "Free Sky-Baronies"]
                                affiliation_opts = list(set(base_factions + factions))
                                game_stats['is_secret'] = st.checkbox("Is Secret Society / Hidden?", game_stats.get('is_secret', False), key=f"{item['title']}_secret")
                                game_stats['affiliation_lock'] = st.selectbox("Affiliation Lock (Where do they operate?)", affiliation_opts, index=affiliation_opts.index(game_stats.get('affiliation_lock')) if game_stats.get('affiliation_lock') in affiliation_opts else 0, key=f"{item['title']}_affil")
                                c1, c2 = st.columns(2)
                                game_stats['motive'] = c1.selectbox("Primary Behavior / Motive", motive_opts, index=motive_opts.index(game_stats.get('motive')) if game_stats.get('motive') in motive_opts else 0, key=f"{item['title']}_motive")
                                game_stats['tactic'] = c2.selectbox("Primary Tactic", tactic_opts, index=tactic_opts.index(game_stats.get('tactic')) if game_stats.get('tactic') in tactic_opts else 0, key=f"{item['title']}_tactic")
                                c1, c2 = st.columns(2)
                                game_stats['member_threat'] = c1.number_input("Average Member Threat Tier", 1, 5, game_stats.get('member_threat', 1), key=f"{item['title']}_mthreat")
                                game_stats['unit_type'] = c2.text_input("Signature Unit Type (e.g., Assassin, Banker, Cultist)", game_stats.get('unit_type', ""), key=f"{item['title']}_unit")
                            elif tab_name == "Ecosystem (Flora & Fauna)":
                                repr_opts = ["Very Slow", "Slow", "Moderate", "Fast", "Invasive"]
                                biome_opts = ["Dust Bowl", "Tangle/Jungle", "High Peaks", "Swamp/Mire", "Deep Subterranean", "Coastal/Oceanic"]
                                harv_opts = ["Requires Killing (e.g., Hide/Meat)", "Harvested Alive (e.g., Milk/Shed/Fruit)", "Not Harvestable"]
                                game_stats['reproduction'] = st.select_slider("Reproduction / Multiplication Rate", options=repr_opts, value=game_stats.get('reproduction', "Moderate"), key=f"{item['title']}_repr")
                                game_stats['biomes'] = st.multiselect("Preferred Biomes/Climate", biome_opts, default=game_stats.get('biomes', []), key=f"{item['title']}_biomes")
                                c1, c2 = st.columns(2)
                                game_stats['is_hostile'] = c1.checkbox("Is Hostile / Dangerous?", game_stats.get('is_hostile', False), key=f"{item['title']}_hostile")
                                game_stats['is_tameable'] = c2.checkbox("Is Tameable / Farmable?", game_stats.get('is_tameable', False), key=f"{item['title']}_tame")
                                game_stats['aggression'] = st.slider("Spread Aggression (How fast it overtakes new locales)", 1, 10, game_stats.get('aggression', 3), key=f"{item['title']}_spread")
                                game_stats['harvest'] = st.selectbox("Harvest Method", harv_opts, index=harv_opts.index(game_stats.get('harvest', harv_opts[2])) if game_stats.get('harvest') in harv_opts else 2, key=f"{item['title']}_harv")
                                game_stats['skill'] = st.text_input("Beast Skill / Tactic", game_stats.get('skill', "Bite"), key=f"{item['title']}_bskill")
                                game_stats['statblock'] = st.text_area("Base Statblock (JSON or Text)", game_stats.get('statblock', ""), key=f"{item['title']}_stats")
                            elif tab_name == "Resources (Economy)":
                                mat_opts = ["Material", "Bonus"]
                                rare_opts = ["Common", "Uncommon", "Rare", "Epic", "Legendary"]
                                biome_opts = ["Dust Bowl", "Tangle/Jungle", "High Peaks", "Swamp/Mire", "Deep Subterranean", "Coastal/Oceanic"]
                                game_stats['resource_type'] = st.selectbox("Material/Bonus Type", mat_opts, index=mat_opts.index(game_stats.get('resource_type', "Material")) if game_stats.get('resource_type') in mat_opts else 0, key=f"{item['title']}_restype")
                                game_stats['rarity'] = st.select_slider("Rarity", options=rare_opts, value=game_stats.get('rarity', "Common"), key=f"{item['title']}_rarity")
                                game_stats['spawn_biomes'] = st.multiselect("Spawn Biomes", biome_opts, default=game_stats.get('spawn_biomes', []), key=f"{item['title']}_spawn")
                                game_stats['proximity_factors'] = st.text_input("Required Factors (Proximity, etc.)", game_stats.get('proximity_factors', ""), key=f"{item['title']}_prox")
                                c1, c2 = st.columns(2)
                                game_stats['is_infinite'] = c1.checkbox("Infinite Source?", game_stats.get('is_infinite', False), key=f"{item['title']}_inf")
                                game_stats['gather_rate'] = c2.slider("Gather Rate", 1, 10, game_stats.get('gather_rate', 5), key=f"{item['title']}_gather")
                                c1, c2 = st.columns(2)
                                game_stats['harvest_difficulty'] = c1.number_input("Harvest Difficulty", 1, 20, game_stats.get('harvest_difficulty', 10), key=f"{item['title']}_hdiff")
                                game_stats['danger_level'] = c2.slider("Danger Level", 1, 10, game_stats.get('danger_level', 1), key=f"{item['title']}_danger")
                            elif tab_name == "Locations":
                                loc_opts = ["Town", "Building", "Feature", "Outpost", "Ruins"]
                                db_data_loc = load_all_lore_parameters()
                                factions = [f_title for f_title, f_data in db_data_loc.items() if f_data['category'] == "Factions (Empires)"]
                                factions = ["Neutral / None"] + factions
                                game_stats['faction_owner'] = st.selectbox("Faction Owner", factions, index=factions.index(game_stats.get('faction_owner')) if game_stats.get('faction_owner') in factions else 0, key=f"{item['title']}_owner")
                                game_stats['location_type'] = st.selectbox("Location Type", loc_opts, index=loc_opts.index(game_stats.get('location_type', "Town")) if game_stats.get('location_type') in loc_opts else 0, key=f"{item['title']}_loctype")
                                st.info("Additional location specifics should be embedded in the Lore markdown.")
                            elif tab_name == "Tech & Items":
                                tag_opts = ["Weapon", "Armor", "Consumable", "Quest/Misc"]
                                game_stats['item_tag'] = st.selectbox("Item Tag", tag_opts, index=tag_opts.index(game_stats.get('item_tag', tag_opts[0])) if game_stats.get('item_tag') in tag_opts else 0, key=f"{item['title']}_itag")
                                game_stats['base_item'] = st.text_input("Tied Base Item (e.g., Heavy Sword, Plate Mail)", game_stats.get('base_item', ""), key=f"{item['title']}_base")
                                c1, c2 = st.columns(2)
                                game_stats['effect_val'] = c1.number_input("Effect Value (Damage or Armor rating)", 0, 50, game_stats.get('effect_val', 0), key=f"{item['title']}_eval")
                                game_stats['loadout'] = c2.number_input("Loadout Number (Capacity Tax)", 0, 5, game_stats.get('loadout', 1), key=f"{item['title']}_load")
                                game_stats['effects'] = st.text_area("Other Mechanical Effects (e.g., Applies [Burn], Restores 2 S-Die)", game_stats.get('effects', ""), key=f"{item['title']}_effects")
                            else:
                                game_stats['custom_params'] = st.text_area("Dynamic Parameters (JSON/Text)", game_stats.get('custom_params', ""), key=f"{item['title']}_custom")
                            if st.button(f"Save '{item['title']}' Parameters", key=f"{item['title']}_save"):
                                save_single_entry(item['title'], item['category'], item['lore'], game_stats)
                                st.success(f"Parameters for {item['title']} written to DB!")
                                item['parameters'] = game_stats
                        st.divider()
else:
    st.info("👈 Sync with Obsidian to see your folder-organized lore.")
