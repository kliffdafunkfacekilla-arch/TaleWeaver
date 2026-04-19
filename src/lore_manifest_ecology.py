import sqlite3
import json

DB_PATH = "state/shatterlands.db"

LORE_DATA = [
    # --- FOREST ---
    {"title": "Glint-Fern", "cat": "Flora", "biome": "Forest", "desc": "A bioluminescent fern that mirrors the pattern of the Shattered Moon.", "yield": "Luminous Extract"},
    {"title": "Bark-Runner", "cat": "Fauna", "biome": "Forest", "desc": "Six-legged mammalian predators that blend perfectly into the silver-bark trees.", "yield": "Agile Sinew"},
    {"title": "Mending Moss", "cat": "Flora", "biome": "Forest", "desc": "A soft, spongy moss that accelerates the closing of wounds when applied directly.", "yield": "Healing Salve Base"},
    {"title": "Ghost-Elk", "cat": "Fauna", "biome": "Forest", "desc": "Ethereal herbivores that phase through solid trees when startled.", "yield": "Phase-Pelt"},
    {"title": "Whisper-Vine", "cat": "Flora", "biome": "Forest", "desc": "A parasitic vine that vibrates audibly when leyline chaos levels increase.", "yield": "Sonic Fiber"},

    # --- TROPICAL ---
    {"title": "Sun-Pulse Lily", "cat": "Flora", "biome": "Tropical", "desc": "Massive flowers that store solar chaos and release it in bright bursts at night.", "yield": "Solar Pollen"},
    {"title": "Talon-Fly", "cat": "Fauna", "biome": "Tropical", "desc": "Insects with razor-sharp mandibles that hunt in swarms near the moisture-rich rivers.", "yield": "Chitinous Plate"},
    {"title": "Ember-Root", "cat": "Flora", "biome": "Tropical", "desc": "Roots that remain hot to the touch even days after being harvested.", "yield": "Thermal Resin"},
    {"title": "Verdant Prowler", "cat": "Fauna", "biome": "Tropical", "desc": "Large reptiles that drop from the canopy with incredible stealth.", "yield": "Venom Sac"},
    {"title": "Spice-Orchid", "cat": "Flora", "biome": "Tropical", "desc": "Rare orchids whose scent causes mild hallucinations and increased awareness.", "yield": "Sensory Paste"},

    # --- OCEANIC ---
    {"title": "Abyssal Kelp", "cat": "Flora", "biome": "Oceanic", "desc": "Pressure-resistant kelp that glows with a cold, blue light from the depths.", "yield": "Pressure-Gel"},
    {"title": "Storm-Ray", "cat": "Fauna", "biome": "Oceanic", "desc": "Flying aquatic creatures that generate electrical arcs between their wing-tips.", "yield": "Electric Membrane"},
    {"title": "Siren-Coral", "cat": "Flora", "biome": "Oceanic", "desc": "Coral formations that produce a haunting melody as tides flow through them.", "yield": "Harmonic Shard"},
    {"title": "Tide-Stalker", "cat": "Fauna", "biome": "Oceanic", "desc": "Amphibious hunters that wait in the shallow surf for land-breeding prey.", "yield": "Wet-Scale"},
    {"title": "Ink-Bloom", "cat": "Flora", "biome": "Oceanic", "desc": "Underwater flowers that release clouds of obscuring smoke when touched.", "yield": "Obscuring Tint"},

    # --- TERRA (Mountains/Deserts/Plains) ---
    {"title": "Litho-Rose", "cat": "Flora", "biome": "Terra", "desc": "Flowers that grow slowly out of solid granite, with petals made of thin quartz.", "yield": "Quartz Shard"},
    {"title": "Sand-Slider", "cat": "Fauna", "biome": "Terra", "desc": "Flat, disc-like reptiles that skate across the dunes at high speeds.", "yield": "Low-Friction Hide"},
    {"title": "Iron-Thistle", "cat": "Flora", "biome": "Terra", "desc": "A metallic weed that grows in areas of high heavy-metal concentration.", "yield": "Raw Ore Shavings"},
    {"title": "Wind-Raptor", "cat": "Fauna", "biome": "Terra", "desc": "Avian predators that use the rising heat currents to stay aloft for days.", "yield": "High-Altitude Down"},
    {"title": "Glass-Bloom", "cat": "Flora", "biome": "Terra", "desc": "Resilient plants that bloom only after a chaos-storm has vitreously fused the sand.", "yield": "Vitreous Petal"},
]

def manifest_ecology():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    print("Manifesting the Legendary Ecosystem...")
    
    added = 0
    for item in LORE_DATA:
        content = f"Biome: {item['biome']}. {item['desc']} Harvest Yield: {item['yield']}."
        params = json.dumps({"biome": item['biome'], "yield": item['yield']})
        cursor.execute('''
            INSERT OR REPLACE INTO lore_entries (title, category, content, parameters)
            VALUES (?, ?, ?, ?)
        ''', (item['title'], item['cat'], content, params))
        added += 1
    
    conn.commit()
    conn.close()
    print(f"Success! {added} biological legends added to the Vault.")

if __name__ == "__main__":
    manifest_ecology()
