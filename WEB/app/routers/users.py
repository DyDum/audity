"""Routes gestion utilisateurs"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import User
from ..schemas import MessageResponse, User as UserSchema, UserCreate,MFAResetRequest, ChangePasswordRequest, ChangeEmailRequest
from ..models import User as UserModel
from ..dependencies import get_current_admin_user, get_current_user, create_audit_log
from ..auth.local import create_user, get_password_hash, verify_password

router = APIRouter(prefix="/api/users", tags=["Users"])

@router.get("/", response_model=List[UserSchema])
async def list_users(skip: int = 0, limit: int = 100, current_user: User = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    """Lister les utilisateurs (admin)"""
    return db.query(User).offset(skip).limit(limit).all()

@router.get("/me", response_model=UserSchema)
async def read_users_me(current_user = Depends(get_current_user)):
    return current_user

@router.get("/{user_id}", response_model=UserSchema)
async def get_user(user_id: int, current_user: User = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    """Récupérer un utilisateur"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")
    return user

@router.post("/", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def create_new_user(user_data: UserCreate, request: Request, current_user: User = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    """Créer un utilisateur (admin)"""
    existing = db.query(User).filter((User.username == user_data.username) | (User.email == user_data.email)).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Utilisateur ou email déjà utilisé")

    new_user = create_user(db, user_data.username, user_data.email, user_data.password, user_data.is_admin, user_data.full_name)
    create_audit_log(db, current_user.id, "user_created", "user", new_user.id, request=request)
    return new_user

@router.delete("/{user_id}")
async def delete_user(user_id: int, request: Request, current_user: User = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    """Supprimer un utilisateur (admin)"""
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Impossible de supprimer votre compte")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")

    db.delete(user)
    db.commit()
    create_audit_log(db, current_user.id, "user_deleted", "user", user_id, request=request)
    return {"message": "Utilisateur supprimé"}

@router.put("/{user_id}/toggle-status")
async def toggle_user_status(user_id: int, current_user = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    """Activer/Désactiver un utilisateur"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")
    
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Impossible de désactiver votre compte")
    
    user.is_active = not user.is_active
    db.commit()
    create_audit_log(db, current_user.id, f"user_{'activated' if user.is_active else 'deactivated'}", "user", user.id)
    return {"message": f"Utilisateur {'activé' if user.is_active else 'désactivé'}"}

@router.post("/mfa/admin/reset", response_model=MessageResponse)
async def admin_reset_mfa(
    body: MFAResetRequest,
    admin = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    user = db.query(UserModel).filter(UserModel.id == body.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    user.mfa_enabled = False
    user.mfa_secret = None
    db.commit()
    create_audit_log(db, admin.id, "mfa_admin_reset", "user", user.id)
    return {"message": "MFA réinitialisé pour cet utilisateur"}

@router.post("/me/change-password", response_model=MessageResponse)
async def change_password(
    body: ChangePasswordRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    # Vérifier ancien mot de passe (pour les comptes locaux uniquement)
    if current_user.auth_method != "local":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Changement de mot de passe local non autorisé pour ce type de compte",
        )

    if not verify_password(body.old_password, current_user.hashed_password):
        create_audit_log(db, current_user.id, "password_change_failed", request=request)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ancien mot de passe incorrect",
        )

    current_user.hashed_password = get_password_hash(body.new_password)
    db.commit()
    create_audit_log(db, current_user.id, "password_changed", request=request)
    return {"message": "Mot de passe modifié avec succès"}

@router.post("/me/change-email", response_model=MessageResponse)
async def change_email(
    body: ChangeEmailRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    existing = (
        db.query(UserModel)
        .filter(UserModel.email == body.new_email, UserModel.id != current_user.id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cet email est déjà utilisé par un autre compte",
        )

    current_user.email = body.new_email
    db.commit()
    create_audit_log(db, current_user.id, "email_changed", request=request)
    return {"message": "Adresse email mise à jour."}