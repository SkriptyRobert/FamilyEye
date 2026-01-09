import sqlite3
import os

DB_PATH = "parental_control.db"

def migrate_db():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(devices)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "daily_usage_seconds" not in columns:
            print("Adding daily_usage_seconds to devices table...")
            cursor.execute("ALTER TABLE devices ADD COLUMN daily_usage_seconds INTEGER DEFAULT 0")
            conn.commit()
            print("Migration successful.")
        else:
            print("Column daily_usage_seconds already exists.")
            
    except Exception as e:
        print(f"Error migrating database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_db()
