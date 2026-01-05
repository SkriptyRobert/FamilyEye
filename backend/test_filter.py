
import sys
from pathlib import Path

# Add backend/app to path
sys.path.append(str(Path(__file__).parent / "app"))

from services.app_filter import app_filter

# Force configure reload to pick up changes
app_filter.reload_config()

def test_app(exe_name):
    print(f"Testing: {exe_name}")
    is_trackable = app_filter.is_trackable(exe_name)
    print(f"  Trackable: {is_trackable}")
    
    if is_trackable:
        friendly = app_filter.get_friendly_name(exe_name)
        category = app_filter.get_category(exe_name)
        icon = app_filter.get_icon_type(exe_name)
        print(f"  Friendly:  {friendly}")
        print(f"  Category:  {category}")
        print(f"  Icon:      {icon}")
    else:
        print(f"  Result:    HIDDEN (Correct)")

print("=== STARTING FILTER TEST (ROUND 2) ===\n")

# 1. New Blacklisted Apps from Screenshot
test_app("mmc.exe")
test_app("LockApp.exe")
test_app("FileCoAuth.exe")
test_app("explorer.exe")
test_app("Microsoft.Photos.exe")
test_app("ctfmon.exe")
test_app("SearchApp.exe")

print("\n=== ICON CHECK ===")
test_app("msedge.exe") # Should have Globe icon
test_app("javaw.exe")  # Should have Game icon

print("\n=== TEST COMPLETE ===")
