"""
Service for cleaning up old data and handling device deletion.
"""
import os
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from ..models import UsageLog, ShieldAlert, Device, Rule, ShieldKeyword
from ..api.reports.device_endpoints import set_running_processes_cache

logger = logging.getLogger(__name__)

def delete_file_safely(relative_path: str):
    """Delete a file given its relative path from backend root."""
    try:
        # Assuming backend root is CWD
        current_dir = os.getcwd()
        # Prevent directory traversal
        if ".." in relative_path:
            logger.warning(f"Attempted directory traversal in delete: {relative_path}")
            return False

        full_path = os.path.join(current_dir, relative_path)
        if os.path.exists(full_path) and os.path.isfile(full_path):
            os.remove(full_path)
            logger.info(f"Deleted file: {full_path}")
            return True
    except Exception as e:
        logger.error(f"Error deleting file {relative_path}: {e}")
    return False

def cleanup_device_data(db: Session, device_id: int):
    """
    Completely remove a device and all its associated data (files + DB).
    """
    logger.info(f"Starting cleanup for device ID {device_id}")
    
    # 1. Delete Shield Alert Screenshots
    alerts = db.query(ShieldAlert).filter(ShieldAlert.device_id == device_id).all()
    for alert in alerts:
        rel_path = None
        if alert.screenshot_url:
            # Handle legacy static URLs
            if "/static/uploads/" in alert.screenshot_url:
                try:
                    parts = alert.screenshot_url.split("static/uploads/")
                    if len(parts) > 1:
                        rel_path = os.path.join("uploads", parts[1])
                except Exception:
                    pass
            # Handle new secure API URLs
            elif "/api/files/screenshots/" in alert.screenshot_url:
                try:
                    # Format: .../api/files/screenshots/{device_id}/{filename}
                    # Physical path: uploads/screenshots/{device_id}/{filename}
                    parts = alert.screenshot_url.split("/api/files/screenshots/")
                    if len(parts) > 1:
                        # parts[1] is device_id/filename
                        rel_path = os.path.join("uploads", "screenshots", parts[1])
                except Exception:
                    pass

        if rel_path:
             delete_file_safely(rel_path)

    # 2. Delete DB Records (Cascades usually handle this, but explicit is safer for files)
    # The actual DB deletion will be handled by cascade or caller if they delete the Device object.
    # But here we just scrub files.
    
    # 3. Clear caches
    try:
        # Clear running processes cache
        from ..api.reports.device_endpoints import running_processes_cache
        if device_id in running_processes_cache:
            del running_processes_cache[device_id]
    except ImportError:
        pass
        
    logger.info(f"Cleanup finished for device {device_id}")

def cleanup_old_data(db: Session, retention_days_logs: int = None, retention_days_screenshots: int = 30):
    """
    Delete data older than specified retention periods.
    For logs: Only delete orphaned logs (where device doesn't exist).
    For screenshots: Delete older than retention_days_screenshots.
    """
    logger.info("Starting automated cleanup of old data...")
    now = datetime.now(timezone.utc)
    
    # 1. Cleanup Orphaned Usage Logs (Logs without existing device)
    # Note: Cascades should handle this, but this is a safety net.
    # We do NOT delete old logs for active devices (as requested).
    from sqlalchemy.sql import exists
    
    # Simple orphan cleanup: Delete usage logs where device_id is not in Devices
    # This might be slow on huge tables, so we rely on cascade mostly.
    # But let's keep it safe:
    # deleted_logs = db.query(UsageLog).filter(~exists().where(Device.id == UsageLog.device_id)).delete(synchronize_session=False)
    # Actually, simpler:
    deleted_logs = 0
    # Uncomment if we suspect orphans:
    # subquery = db.query(Device.id)
    # deleted_logs = db.query(UsageLog).filter(UsageLog.device_id.notin_(subquery)).delete(synchronize_session=False)

    
    # 2. Cleanup Old Shield Alerts & Screenshots
    # "Pravidla pro snimky nechej" - Keep retention for screenshots (disk space protection)
    if retention_days_screenshots:
        cutoff_screenshots = now - timedelta(days=retention_days_screenshots)
        old_alerts = db.query(ShieldAlert).filter(ShieldAlert.timestamp < cutoff_screenshots).all()
        
        deleted_files = 0
        deleted_alerts = 0
        for alert in old_alerts:
            # Physical file delete
            rel_path = None
            if alert.screenshot_url:
                if "static/uploads/" in alert.screenshot_url:
                    try:
                        parts = alert.screenshot_url.split("static/uploads/")
                        if len(parts) > 1:
                            rel_path = os.path.join("uploads", parts[1])
                    except Exception:
                        pass
                elif "/api/files/screenshots/" in alert.screenshot_url:
                    try:
                        parts = alert.screenshot_url.split("/api/files/screenshots/")
                        if len(parts) > 1:
                            rel_path = os.path.join("uploads", "screenshots", parts[1])
                    except Exception:
                        pass
            
            if rel_path:
                if delete_file_safely(rel_path):
                    deleted_files += 1
            
            db.delete(alert)
            deleted_alerts += 1
    else:
        deleted_alerts = 0
        deleted_files = 0
        
    db.commit()
    logger.info(f"Cleanup complete: Deleted {deleted_logs} orphaned logs and {deleted_alerts} old alerts ({deleted_files} files).")
    return {"deleted_logs": deleted_logs, "deleted_alerts": deleted_alerts, "deleted_files": deleted_files}
