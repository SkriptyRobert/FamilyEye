"""SQLAlchemy database models."""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Float, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import uuid


class User(Base):
    """User model for parents and children."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # 'parent' or 'child'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    parent_devices = relationship("Device", foreign_keys="Device.parent_id", back_populates="parent")
    child_devices = relationship("Device", foreign_keys="Device.child_id", back_populates="child")


class Device(Base):
    """Device model for managed devices."""
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    device_type = Column(String, nullable=False)  # 'windows', 'android'
    mac_address = Column(String, index=True, nullable=False)  # Not unique - allows multiple 'auto-detected'
    device_id = Column(String, unique=True, index=True, nullable=False)  # Unique device identifier
    parent_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    child_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Null for multi-device mode
    api_key = Column(String, unique=True, index=True, nullable=False)  # For agent authentication
    paired_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    current_processes = Column(Text, nullable=True)  # JSON list of running processes
    screenshot_requested = Column(Boolean, default=False)
    last_screenshot = Column(String, nullable=True) # Path or Base64 of last screenshot
    timezone_offset = Column(Integer, default=0) # Client offset from Server in seconds (Client - Server)
    first_report_today_utc = Column(DateTime(timezone=True), nullable=True)  # First report of current day (for elapsed time calc)
    daily_usage_seconds = Column(Integer, default=0) # Total active time today (from Agent)
    
    # Settings protection for Android devices
    settings_protection = Column(String, default="full")  # 'full', 'partial', or 'off'
    settings_exceptions = Column(String, nullable=True)   # Reserved for future use
    
    # Device Owner status
    is_device_owner = Column(Boolean, default=False)
    device_owner_activated_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    parent = relationship("User", foreign_keys=[parent_id], back_populates="parent_devices")
    child = relationship("User", foreign_keys=[child_id], back_populates="child_devices")
    rules = relationship("Rule", back_populates="device", cascade="all, delete-orphan")
    usage_logs = relationship("UsageLog", back_populates="device", cascade="all, delete-orphan")
    shield_keywords = relationship("ShieldKeyword", back_populates="device", cascade="all, delete-orphan")
    shield_alerts = relationship("ShieldAlert", back_populates="device", cascade="all, delete-orphan")
    
    @property
    def is_online(self) -> bool:
        """Check if device is online (seen in last 5 minutes)."""
        if not self.last_seen:
            return False
            
        from datetime import datetime, timezone, timedelta
        
        # Current time in UTC
        now = datetime.now(timezone.utc)
        
        # Process last_seen
        last_seen = self.last_seen
        
        # SQLite often stores naive datetimes. If naive, assume it implies UTC.
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)
        else:
            # If already aware, convert to UTC to be safe
            last_seen = last_seen.astimezone(timezone.utc)

        # Threshold check (2 minutes)
        # Using abs() to handle potential slight clock skews
        return (now - last_seen) < timedelta(minutes=2)

    @property
    def has_lock_rule(self) -> bool:
        """Check if device has an active lock rule."""
        if not self.rules:
            return False
        return any(r.rule_type == "lock_device" and r.enabled for r in self.rules)
    
    @property
    def has_network_block(self) -> bool:
        """Check if device has an active network block rule."""
        if not self.rules:
            return False
        return any(r.rule_type == "network_block" and r.enabled for r in self.rules)



class Rule(Base):
    """Rule model for device restrictions."""
    __tablename__ = "rules"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    rule_type = Column(String, nullable=False)  # 'app_block', 'time_limit', 'daily_limit', 'website_block', 'schedule'
    name = Column(String, nullable=True)  # Optional user-defined name
    app_name = Column(String, nullable=True)  # Null for daily limits
    website_url = Column(String, nullable=True)  # For website blocks
    time_limit = Column(Integer, nullable=True)  # Minutes per day
    enabled = Column(Boolean, default=True)
    
    # Schedule fields
    schedule_start_time = Column(String, nullable=True)  # HH:MM format
    schedule_end_time = Column(String, nullable=True)  # HH:MM format
    schedule_days = Column(String, nullable=True)  # Comma-separated: "0,1,2,3,4,5,6" (Mon-Sun)
    
    # Network control
    block_network = Column(Boolean, default=False)  # Block network access for app
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    device = relationship("Device", back_populates="rules")


class UsageLog(Base):
    """Usage log for tracking device activity."""
    __tablename__ = "usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    app_name = Column(String, nullable=False)
    window_title = Column(String, nullable=True)
    exe_path = Column(String, nullable=True)
    duration = Column(Integer, nullable=False)  # Seconds
    is_focused = Column(Boolean, default=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    device = relationship("Device", back_populates="usage_logs")
    
    # Optimized indexes for statistics queries
    __table_args__ = (
        Index('idx_usage_device_timestamp', 'device_id', 'timestamp'),
        Index('idx_usage_device_app', 'device_id', 'app_name'),
    )


class PairingToken(Base):
    """Temporary pairing tokens for device registration."""
    __tablename__ = "pairing_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    parent_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)  # Set after pairing
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    parent = relationship("User")
    device = relationship("Device")


class ShieldKeyword(Base):
    """Keywords for Smart Shield content scanner."""
    __tablename__ = "shield_keywords"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    keyword = Column(String, nullable=False)
    category = Column(String, default="custom") # custom, drugs, violence, etc.
    severity = Column(String, default="medium") # low, medium, high
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    device = relationship("Device", back_populates="shield_keywords")


class ShieldAlert(Base):
    """Alerts triggered by Smart Shield."""
    __tablename__ = "shield_alerts"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    keyword = Column(String, nullable=False) # The keyword that triggered it
    app_name = Column(String, nullable=True) # App where it was seen
    detected_text = Column(String, nullable=True) # Context (snippet)
    screenshot_url = Column(String, nullable=True)
    severity = Column(String, nullable=False)
    is_read = Column(Boolean, default=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    device = relationship("Device", back_populates="shield_alerts")


class DeviceOwnerSettings(Base):
    """
    Device Owner restriction settings for Android devices.
    
    This model stores the configuration for Device Owner mode restrictions,
    allowing parents to customize which protections are enabled.
    """
    __tablename__ = "device_owner_settings"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), unique=True, nullable=False)
    
    # Balanced preset (default restrictions)
    disallow_safe_boot = Column(Boolean, default=True)
    disallow_factory_reset = Column(Boolean, default=True)
    disallow_uninstall_apps = Column(Boolean, default=True)
    disallow_apps_control = Column(Boolean, default=True)  # Hides Force Stop
    disallow_debugging = Column(Boolean, default=True)
    disallow_usb_transfer = Column(Boolean, default=True)
    disallow_install_unknown_sources = Column(Boolean, default=True)
    disallow_add_user = Column(Boolean, default=True)
    disallow_remove_user = Column(Boolean, default=True)
    disallow_modify_accounts = Column(Boolean, default=True)
    
    # Paranoid options (disabled by default, for future configuration)
    disallow_wifi_config = Column(Boolean, default=False)
    disallow_bluetooth_config = Column(Boolean, default=False)
    disallow_sms = Column(Boolean, default=False)
    disallow_outgoing_calls = Column(Boolean, default=False)
    disallow_share_location = Column(Boolean, default=False)
    disallow_screenshots = Column(Boolean, default=False)
    
    # Kiosk mode settings (for future implementation)
    kiosk_mode_enabled = Column(Boolean, default=False)
    kiosk_allowed_packages = Column(Text, nullable=True)  # JSON array of package names
    
    # Auto-grant permissions (for silent permission granting)
    auto_grant_location = Column(Boolean, default=True)
    auto_grant_camera = Column(Boolean, default=True)
    auto_grant_contacts = Column(Boolean, default=False)
    auto_grant_call_log = Column(Boolean, default=False)
    auto_grant_sms = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    device = relationship("Device", backref="device_owner_settings")


