import sys
import os
from pathlib import Path

# Přidání cesty k backendu do sys.path
backend_path = Path(__file__).parent.absolute()
sys.path.append(str(backend_path))

from app.database import SessionLocal, engine
from app.models import Base, User
from app.api.auth import get_password_hash

def init_admin(email, password):
    # Vytvoření tabulek pokud neexistují
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Kontrola zda admin již existuje
        admin = db.query(User).filter(User.email == email).first()
        if admin:
            print(f"Admin account {email} already exists.")
            return

        # Vytvoření nového admina
        hashed_password = get_password_hash(password)
        new_admin = User(
            email=email,
            password_hash=hashed_password,
            role="parent"
        )
        db.add(new_admin)
        db.commit()
        print(f"Admin account {email} created successfully.")
    except Exception as e:
        print(f"Error creating admin: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python init_admin.py <email> <password>")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    init_admin(email, password)
