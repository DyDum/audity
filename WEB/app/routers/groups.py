"""Routes gestion des groupes de serveurs"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user

from ..database import get_db
from ..models import Group
from pydantic import BaseModel

# Schémas Pydantic
class GroupCreate(BaseModel):
    name: str

class GroupOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


router = APIRouter(
    prefix="/api/groups",
    tags=["Groups"],
)


@router.get("/", response_model=List[GroupOut])
def list_groups(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Lister tous les groupes"""
    groups = db.query(Group).order_by(Group.name).all()
    return groups


@router.post("/", response_model=GroupOut, status_code=status.HTTP_201_CREATED)
def create_group(body: GroupCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Créer un nouveau groupe"""
    if current_user.is_admin is False:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Droits administrateur requis")
    existing = db.query(Group).filter(Group.name == body.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un groupe avec ce nom existe déjà",
        )

    g = Group(name=body.name)
    db.add(g)
    db.commit()
    db.refresh(g)
    return g


@router.get("/{group_id}", response_model=GroupOut)
def get_group(group_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Récupérer un groupe par ID"""
    g = db.query(Group).filter(Group.id == group_id).first()
    if not g:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Groupe introuvable")
    return g


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(group_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Supprimer un groupe (sans gérer ici le reassignment des serveurs)"""
    if current_user.is_admin is False:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Droits administrateur requis")
    g = db.query(Group).filter(Group.id == group_id).first()
    if not g:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Groupe introuvable")

    db.delete(g)
    db.commit()
    return None
