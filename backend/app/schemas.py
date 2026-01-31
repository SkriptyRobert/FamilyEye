"""Pydantic schemas for request/response validation."""
from pydantic import BaseModel, EmailStr, validator
from datetime import datetime
from typing import Optional, List, Dict
from .config import settings


# User schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str  # 'parent' or 'child'


class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


# Auth schemas
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Device schemas
class DeviceCreate(BaseModel):
    name: str
    device_type: str
    mac_address: str
    device_id: str


class DeviceUpdate(BaseModel):
    name: Optional[str] = None


class DeviceSettingsProtectionUpdate(BaseModel):
    """Schema for updating device settings protection level."""
    settings_protection: str  # 'full' or 'off'
    settings_exceptions: Optional[str] = None  # Reserved for future use


class DeviceResponse(BaseModel):
    id: int
    name: str
    device_type: str
    mac_address: str
    device_id: str
    parent_id: int
    child_id: Optional[int]
    api_key: str
    paired_at: datetime
    last_seen: Optional[datetime]
    is_active: bool
    is_online: bool
    # State flags for UI
    has_lock_rule: bool = False
    has_network_block: bool = False
    current_processes: Optional[str] = None  # JSON string of running processes
    # Screenshot support
    screenshot_requested: bool = False
    last_screenshot: Optional[str] = None  # Base64 data URI
    # Settings protection (Android)
    settings_protection: str = "full"  # 'full' or 'off'
    settings_exceptions: Optional[str] = None  # Reserved for future use
    # Device Owner status
    is_device_owner: bool = False
    device_owner_activated_at: Optional[datetime] = None

    @validator("last_screenshot", pre=True)
    def ensure_full_url(cls, v):
        if v and v.startswith("data:"):
            return v
        if v and not v.startswith("http"):
            return f"{settings.BACKEND_URL}/api/files/{v}"
        return v

    class Config:
        from_attributes = True


# Rule schemas
class RuleCreate(BaseModel):
    device_id: int
    rule_type: str
    name: Optional[str] = None
    app_name: Optional[str] = None
    website_url: Optional[str] = None
    time_limit: Optional[int] = None
    enabled: bool = True
    schedule_start_time: Optional[str] = None
    schedule_end_time: Optional[str] = None
    schedule_days: Optional[str] = None
    block_network: bool = False


class RuleResponse(BaseModel):
    id: int
    device_id: int
    rule_type: str
    name: Optional[str]
    app_name: Optional[str]
    website_url: Optional[str]
    time_limit: Optional[int]
    enabled: bool
    schedule_start_time: Optional[str]
    schedule_end_time: Optional[str]
    schedule_days: Optional[str]
    block_network: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# Usage log schemas
class UsageLogCreate(BaseModel):
    device_id: int
    app_name: str
    duration: int  # Seconds


class UsageLogResponse(BaseModel):
    id: int
    device_id: int
    app_name: str
    window_title: Optional[str] = None
    exe_path: Optional[str] = None
    duration: int
    timestamp: datetime
    # Enhanced Metadata (populated by app_filter)
    friendly_name: Optional[str] = None
    category: Optional[str] = None
    icon_type: Optional[str] = "app"

    class Config:
        from_attributes = True


# Pairing schemas
class PairingTokenResponse(BaseModel):
    token: str
    expires_at: datetime
    pairing_url: str


class PairingRequest(BaseModel):
    token: str
    device_name: str
    device_type: str
    mac_address: str
    device_id: str


class PairingResponse(BaseModel):
    device_id: str  # String device_id from database (not database ID)
    api_key: str
    backend_url: str


class PairingStatusResponse(BaseModel):
    used: bool
    device: Optional[DeviceResponse] = None


# Agent schemas
class AgentRulesRequest(BaseModel):
    device_id: str
    api_key: str


class AgentRulesResponse(BaseModel):
    rules: List[RuleResponse]
    daily_usage: int  # Total seconds used today
    usage_by_app: Dict[str, int] = {}  # App name -> duration seconds
    server_time: Optional[datetime] = None  # Server UTC time
    settings_protection: str = "full"  # Settings protection level for Android
    settings_exceptions: Optional[str] = None


class AgentUsageLogCreate(BaseModel):
    app_name: str
    window_title: Optional[str] = None
    exe_path: Optional[str] = None
    duration: int  # Seconds
    is_focused: bool = False
    timestamp: Optional[datetime] = None  # Optional client timestamp


class AgentReportRequest(BaseModel):
    device_id: str
    api_key: str
    usage_logs: List[AgentUsageLogCreate]
    client_timestamp: Optional[datetime] = None  # Optional client timestamp (system time)
    timezone_offset_seconds: Optional[int] = None  # Device offset from UTC (e.g. +3600 for UTC+1)
    running_processes: Optional[List[str]] = None  # NEW: list of currently running apps
    device_uptime_seconds: Optional[int] = None    # NEW: Total system uptime
    device_usage_today_seconds: Optional[int] = None # NEW: Agent-tracked daily active time


# Critical Event schemas (for immediate reporting)
class CriticalEventRequest(BaseModel):
    device_id: str
    api_key: str
    event_type: str  # 'limit_exceeded', 'app_blocked', 'daily_limit_exceeded'
    app_name: Optional[str] = None
    used_seconds: Optional[int] = None
    limit_seconds: Optional[int] = None
    message: Optional[str] = None
    timestamp: Optional[datetime] = None


# Shield Schemas
class ShieldKeywordCreate(BaseModel):
    device_id: int
    keyword: str
    category: str = "custom"
    severity: str = "medium"


class ShieldKeywordResponse(BaseModel):
    id: int
    device_id: int
    keyword: str
    category: str
    severity: str
    enabled: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ShieldAlertCreate(BaseModel):
    device_id: str # String GUID
    keyword: str
    app_name: Optional[str] = None
    detected_text: Optional[str] = None
    screenshot_url: Optional[str] = None
    severity: str


class ShieldAlertResponse(BaseModel):
    id: int
    device_id: int
    keyword: str
    app_name: Optional[str]
    detected_text: Optional[str]
    screenshot_url: Optional[str]
    severity: str
    is_read: bool
    timestamp: datetime

    @validator("screenshot_url", pre=True)
    def ensure_full_url(cls, v):
        if v and not v.startswith("http"):
             return f"{settings.BACKEND_URL}/api/files/{v}"
        return v

    class Config:
        from_attributes = True


# Device Owner Settings schemas
class DeviceOwnerSettingsCreate(BaseModel):
    """Schema for creating Device Owner settings for a device."""
    device_id: int
    # Balanced preset (defaults)
    disallow_safe_boot: bool = True
    disallow_factory_reset: bool = True
    disallow_uninstall_apps: bool = True
    disallow_apps_control: bool = True
    disallow_debugging: bool = True
    disallow_usb_transfer: bool = True
    disallow_install_unknown_sources: bool = True
    disallow_add_user: bool = True
    disallow_remove_user: bool = True
    disallow_modify_accounts: bool = True
    # Paranoid options (disabled by default)
    disallow_wifi_config: bool = False
    disallow_bluetooth_config: bool = False
    disallow_sms: bool = False
    disallow_outgoing_calls: bool = False
    disallow_share_location: bool = False
    disallow_screenshots: bool = False
    # Kiosk mode
    kiosk_mode_enabled: bool = False
    kiosk_allowed_packages: Optional[str] = None
    # Auto-grant permissions
    auto_grant_location: bool = True
    auto_grant_camera: bool = True
    auto_grant_contacts: bool = False
    auto_grant_call_log: bool = False
    auto_grant_sms: bool = False


class DeviceOwnerSettingsUpdate(BaseModel):
    """Schema for updating Device Owner settings."""
    # All fields are optional for partial updates
    disallow_safe_boot: Optional[bool] = None
    disallow_factory_reset: Optional[bool] = None
    disallow_uninstall_apps: Optional[bool] = None
    disallow_apps_control: Optional[bool] = None
    disallow_debugging: Optional[bool] = None
    disallow_usb_transfer: Optional[bool] = None
    disallow_install_unknown_sources: Optional[bool] = None
    disallow_add_user: Optional[bool] = None
    disallow_remove_user: Optional[bool] = None
    disallow_modify_accounts: Optional[bool] = None
    disallow_wifi_config: Optional[bool] = None
    disallow_bluetooth_config: Optional[bool] = None
    disallow_sms: Optional[bool] = None
    disallow_outgoing_calls: Optional[bool] = None
    disallow_share_location: Optional[bool] = None
    disallow_screenshots: Optional[bool] = None
    kiosk_mode_enabled: Optional[bool] = None
    kiosk_allowed_packages: Optional[str] = None
    auto_grant_location: Optional[bool] = None
    auto_grant_camera: Optional[bool] = None
    auto_grant_contacts: Optional[bool] = None
    auto_grant_call_log: Optional[bool] = None
    auto_grant_sms: Optional[bool] = None


class DeviceOwnerSettingsResponse(BaseModel):
    """Schema for returning Device Owner settings."""
    id: int
    device_id: int
    # Balanced preset
    disallow_safe_boot: bool
    disallow_factory_reset: bool
    disallow_uninstall_apps: bool
    disallow_apps_control: bool
    disallow_debugging: bool
    disallow_usb_transfer: bool
    disallow_install_unknown_sources: bool
    disallow_add_user: bool
    disallow_remove_user: bool
    disallow_modify_accounts: bool
    # Paranoid options
    disallow_wifi_config: bool
    disallow_bluetooth_config: bool
    disallow_sms: bool
    disallow_outgoing_calls: bool
    disallow_share_location: bool
    disallow_screenshots: bool
    # Kiosk mode
    kiosk_mode_enabled: bool
    kiosk_allowed_packages: Optional[str]
    # Auto-grant permissions
    auto_grant_location: bool
    auto_grant_camera: bool
    auto_grant_contacts: bool
    auto_grant_call_log: bool
    auto_grant_sms: bool
    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
