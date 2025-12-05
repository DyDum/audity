"""Routes d'authentification"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from ..database import get_db
from ..schemas import Token, MFAVerifyRequest, MFASetupResponse, MessageResponse
from ..config import settings
from ..dependencies import  get_current_user, create_audit_log, get_current_user_allow_unverified
from ..auth.local import authenticate_user, create_access_token, update_last_login
from ..auth.azure_ad import authenticate_azure_ad
from ..auth.ldap_auth import authenticate_ldap
from ..auth.mfa import enable_mfa, disable_mfa, verify_mfa

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), request: Request = None, db: Session = Depends(get_db)):
    """Connexion utilisateur"""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        user = authenticate_azure_ad(db, form_data.username, form_data.password)
    if not user:
        user = authenticate_ldap(db, form_data.username, form_data.password)

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants incorrects", headers={"WWW-Authenticate": "Bearer"})

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Compte désactivé")

    requires_mfa = user.mfa_enabled
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username, "mfa_verified": not requires_mfa}, expires_delta=access_token_expires)

    if not requires_mfa:
        update_last_login(db, user)
        create_audit_log(db, user.id, "login_success", request=request)

    return {"access_token": access_token, "token_type": "bearer", "requires_mfa": requires_mfa}

@router.post("/mfa/verify", response_model=Token)
async def verify_mfa_token(
    mfa_data: MFAVerifyRequest,
    current_user = Depends(get_current_user_allow_unverified),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """Vérifier le code MFA"""
    if not current_user.mfa_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="MFA non activé")

    if not verify_mfa(current_user, mfa_data.token):
        create_audit_log(db, current_user.id, "mfa_verification_failed", request=request)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Code MFA invalide")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": current_user.username, "mfa_verified": True},
        expires_delta=access_token_expires,
    )
    update_last_login(db, current_user)
    create_audit_log(db, current_user.id, "mfa_verification_success", request=request)

    return {"access_token": access_token, "token_type": "bearer", "requires_mfa": False}

@router.post("/mfa/enable", response_model=MFASetupResponse)
async def enable_user_mfa(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Activer MFA"""
    if current_user.mfa_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="MFA déjà activé")
    secret, qr_code = enable_mfa(db, current_user)
    create_audit_log(db, current_user.id, "mfa_enabled")
    return {"secret": secret, "qr_code_url": qr_code}

@router.post("/mfa/disable", response_model=MessageResponse)
async def disable_user_mfa(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Désactiver MFA"""
    if not current_user.mfa_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="MFA non activé")
    disable_mfa(db, current_user)
    create_audit_log(db, current_user.id, "mfa_disabled")
    return {"message": "MFA désactivé"}

@router.get("/me")
async def get_current_user_info(current_user = Depends(get_current_user)):
    """Obtenir infos utilisateur courant"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_admin": current_user.is_admin,
        "auth_method": current_user.auth_method,
        "mfa_enabled": current_user.mfa_enabled,
        "created_at": current_user.created_at,
        "last_login": current_user.last_login
    }