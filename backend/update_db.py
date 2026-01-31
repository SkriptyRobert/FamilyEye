from app.database import engine
from sqlalchemy import text

def add_columns():
    print("Migrating database...")
    with engine.connect() as conn:
        # Migration for devices
        for column in [
            ("devices", "current_processes", "TEXT"),
            ("devices", "screenshot_requested", "BOOLEAN DEFAULT 0"),
            ("devices", "last_screenshot", "TEXT"),
            ("usage_logs", "window_title", "TEXT"),
            ("usage_logs", "exe_path", "TEXT")
        ]:
            table, col_name, col_type = column
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}"))
                conn.commit()
                print(f"Successfully added {col_name} column to {table}")
            except Exception as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    print(f"Column {col_name} in {table} already exists")
                else:
                    print(f"Error adding {col_name} to {table}: {e}")

if __name__ == "__main__":
    add_columns()
