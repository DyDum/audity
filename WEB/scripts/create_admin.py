#!/usr/bin/env python3
"""Créer le premier admin"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal, engine, Base
from app.models import User
from app.auth.local import get_password_hash

def create_admin():
    print("=== Création du premier administrateur ===\n")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        existing = db.query(User).filter(User.is_admin == True).first()
        if existing:
            print(f"⚠️ Admin existe déjà: {existing.username}")
            return

        username = input("Nom d'utilisateur: ").strip()
        email = input("Email: ").strip()
        import getpass
        password = getpass.getpass("Mot de passe: ")

        admin = User(
            username=username,
            email=email,
            hashed_password=get_password_hash(password),
            is_admin=True,
            is_active=True,
            auth_method="local"
        )

        db.add(admin)
        db.commit()
        print(f"\n✅ Admin '{username}' créé!")

    except Exception as e:
        print(f"❌ Erreur: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()
