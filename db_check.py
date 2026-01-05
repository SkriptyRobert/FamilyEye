import sqlite3
from datetime import datetime

conn = sqlite3.connect('parental_control.db')
cur = conn.cursor()

print("=" * 60)
print("DATABASE ANALYSIS FOR SMART INSIGHTS VERIFICATION")
print("=" * 60)

# Check today's data grouped by app
print("\n1. TOP APPS TODAY (2026-01-02):")
cur.execute('''
    SELECT app_name, count(id) as cnt, sum(duration) as total_sec 
    FROM usage_logs 
    WHERE timestamp LIKE "2026-01-02%"
    GROUP BY app_name 
    ORDER BY total_sec DESC 
    LIMIT 15
''')
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]} logs, {r[2]}s ({r[2]//60}m)")

# Total time today
cur.execute('SELECT sum(duration) FROM usage_logs WHERE timestamp LIKE "2026-01-02%"')
total = cur.fetchone()[0] or 0
print(f"\n  TOTAL: {total}s = {total//60}m = {total//3600}h {(total%3600)//60}m")

# Check for duplicate minutes (same minute multiple logs)
print("\n2. MINUTES WITH MANY LOGS (possible agent overlap):")
cur.execute('''
    SELECT strftime("%H:%M", timestamp) as min, count(id) as cnt
    FROM usage_logs 
    WHERE timestamp LIKE "2026-01-02%"
    GROUP BY min 
    ORDER BY cnt DESC 
    LIMIT 10
''')
for r in cur.fetchall():
    print(f"  {r[0]} -> {r[1]} log entries")

# Check unique minutes count (for Screen Time calculation)
cur.execute('''
    SELECT count(DISTINCT strftime("%Y-%m-%d %H:%M", timestamp)) 
    FROM usage_logs 
    WHERE timestamp LIKE "2026-01-02%"
''')
unique_mins = cur.fetchone()[0] or 0
screen_time = unique_mins * 60
print(f"\n3. UNIQUE MINUTES (Screen Time base): {unique_mins} => {screen_time}s = {screen_time//60}m")

# Check for is_focused distribution
print("\n4. FOCUS DISTRIBUTION:")
cur.execute('''
    SELECT is_focused, count(id) as cnt, sum(duration) as total_sec 
    FROM usage_logs 
    WHERE timestamp LIKE "2026-01-02%"
    GROUP BY is_focused
''')
for r in cur.fetchall():
    focus_label = "FOCUSED" if r[0] else "BACKGROUND"
    print(f"  {focus_label}: {r[1]} logs, {r[2]}s ({r[2]//60}m)")

# Check device_id distribution
print("\n5. DEVICE ID DISTRIBUTION:")
cur.execute('''
    SELECT device_id, count(id) as cnt, sum(duration) as total_sec 
    FROM usage_logs 
    WHERE timestamp LIKE "2026-01-02%"
    GROUP BY device_id
''')
for r in cur.fetchall():
    print(f"  Device {r[0]}: {r[1]} logs, {r[2]}s ({r[2]//60}m)")

# Get device names
print("\n6. REGISTERED DEVICES:")
cur.execute('SELECT id, name, created_at FROM devices')
for r in cur.fetchall():
    print(f"  ID {r[0]}: {r[1]} (created: {r[2]})")

conn.close()
print("\nDone.")
