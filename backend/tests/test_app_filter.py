import pytest
import os
import sys

# Add backend directory to sys.path to allow imports
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.services.app_filter import app_filter

def test_is_trackable():
    # Test known system processes (should be hidden)
    assert app_filter.is_trackable("idle") is False
    assert app_filter.is_trackable("svchost") is False
    assert app_filter.is_trackable("dwm") is False
    
    # Test common apps (should be trackable)
    assert app_filter.is_trackable("chrome") is True
    assert app_filter.is_trackable("msedge") is True
    assert app_filter.is_trackable("Minecraft") is True

def test_get_friendly_name():
    # Test mapping from msedge to Microsoft Edge
    assert app_filter.get_friendly_name("msedge") == "Microsoft Edge"
    assert app_filter.get_friendly_name("msedge.exe") == "Microsoft Edge"
    
    # Test unknown app (returns raw name)
    assert app_filter.get_friendly_name("UnknownApp") == "UnknownApp"

def test_get_category():
    # Test browsers
    assert app_filter.get_category("chrome") == "browsers"
    assert app_filter.get_category("msedge") == "browsers"
    
    # Test games (based on default config patterns)
    assert app_filter.get_category("minecraft") == "games"
    
    # Test unknown
    assert app_filter.get_category("SystemProcessThatIsActuallyTrackable") is None

def test_get_icon_type():
    assert app_filter.get_icon_type("chrome") == "globe"
    assert app_filter.get_icon_type("minecraft") == "game"
    assert app_filter.get_icon_type("unknown") == "app"
