import sqlite3
import os

DB_NAME = "state/shatterlands.db"

def migrate():
    if not os.path.exists(DB_NAME):
        print("Database not found. Initializing...")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Check for columns
    cursor.execute("PRAGMA table_info(layer4_macro_map)")
    cols = [col[1] for col in cursor.fetchall()]
    
    if 'resource_wealth' not in cols:
        print("Adding 'resource_wealth' to layer4_macro_map...")
        cursor.execute("ALTER TABLE layer4_macro_map ADD COLUMN resource_wealth INTEGER DEFAULT 50")
    
    if 'chaos_level' not in cols:
        print("Adding 'chaos_level' to layer4_macro_map...")
        cursor.execute("ALTER TABLE layer4_macro_map ADD COLUMN chaos_level INTEGER DEFAULT 0")

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
