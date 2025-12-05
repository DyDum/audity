"""Authentification Azure AD"""
from typing import Optional
from sqlalchemy.orm import Session
from ..models import User, AuthSettings

def authenticate_azure_ad(db: Session, username: str, password: str) -> Optional[User]:
    auth_settings = db.query(AuthSettings).first()
    if not auth_settings or not auth_settings.azure_enabled:
        return None
    if not all([auth_settings.azure_client_id, auth_settings.azure_client_secret, auth_settings.azure_tenant_id]):
        return None
    try:
        from msal import ConfidentialClientApplication
        client = ConfidentialClientApplication(
            client_id=auth_settings.azure_client_id,
            client_credential=auth_settings.azure_client_secret,
            authority=f"https://login.microsoftonline.com/{auth_settings.azure_tenant_id}"
        )
        result = client.acquire_token_by_username_password(username=username, password=password, scopes=["User.Read"])
        if "access_token" in result:
            user = db.query(User).filter(User.email == username, User.auth_method == "azure_ad").first()
            if not user:
                from .local import get_password_hash
                user = User(username=username.split('@')[0], email=username, hashed_password=get_password_hash("azure_ad_user"), auth_method="azure_ad", is_active=True, is_admin=False)
                db.add(user)
                db.commit()
                db.refresh(user)
            return user
        return None
    except Exception as e:
        print(f"Erreur Azure AD: {e}")
        return None
