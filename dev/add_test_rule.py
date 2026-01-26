
import sys
import os
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Rule, Device

def add_limit_rule(package_name: str, enabled: Boolean = True):
    db = SessionLocal()
    try:
        device = db.query(Device).first()
        if not device:
            print("No device found")
            return
        
        # Check if exists
        rule = db.query(Rule).filter(Rule.device_id == device.id, Rule.app_name == package_name).first()
        if not rule:
            rule = Rule(
                device_id = device.id,
                rule_type = "app_limit",
                app_name = package_name,
                time_limit = 1, # 1 minute
                enabled = enabled
            )
            db.add(rule)
        else:
            rule.enabled = enabled
            rule.time_limit = 1
            
        db.commit()
        print(f"Rule for {package_name} set to {enabled} (1m limit)")
    finally:
        db.close()

if __name__ == "__main__":
    from app.models import Rule
    # We need Boolean if we use it in signature, but let's just use raw values
    add_limit_rule("com.google.android.youtube")
