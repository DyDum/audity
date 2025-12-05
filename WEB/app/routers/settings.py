"""Routes paramètres"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import AuthSettings
from ..dependencies import get_current_admin_user

router = APIRouter(prefix="/api/settings", tags=["Settings"])

@router.get("/auth")
async def get_auth_settings(current_user = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    """Récupérer paramètres auth"""
    settings = db.query(AuthSettings).first()
    if not settings:
        settings = AuthSettings(azure_enabled=False, ldap_enabled=False)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings

@router.put("/auth")
async def update_auth_settings(settings_data: dict, current_user = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    """Mettre à jour paramètres auth"""
    settings = db.query(AuthSettings).first()
    if not settings:
        settings = AuthSettings()
        db.add(settings)

    for key, value in settings_data.items():
        setattr(settings, key, value)

    settings.updated_by = current_user.id
    db.commit()
    return {"message": "Paramètres mis à jour"}
