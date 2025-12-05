"""Authentification LDAP"""
from typing import Optional
import ldap3
from sqlalchemy.orm import Session
from ..models import User, AuthSettings

def authenticate_ldap(db: Session, username: str, password: str) -> Optional[User]:
    auth_settings = db.query(AuthSettings).first()
    if not auth_settings or not auth_settings.ldap_enabled:
        return None
    if not all([auth_settings.ldap_server, auth_settings.ldap_domain]):
        return None
    try:
        server_uri = f"ldaps://{auth_settings.ldap_server}" if auth_settings.ldap_use_ssl else f"ldap://{auth_settings.ldap_server}"
        server = ldap3.Server(server_uri, port=636 if auth_settings.ldap_use_ssl else auth_settings.ldap_port, get_info=ldap3.ALL)
        user_dn = f"{username}@{auth_settings.ldap_domain}"
        conn = ldap3.Connection(server, user=user_dn, password=password, authentication=ldap3.SIMPLE)
        if not conn.bind():
            return None
        email = username if '@' in username else f"{username}@{auth_settings.ldap_domain}"
        user = db.query(User).filter(User.username == username, User.auth_method == "ldap").first()
        if not user:
            from .local import get_password_hash
            user = User(username=username, email=email, hashed_password=get_password_hash("ldap_user"), auth_method="ldap", is_active=True, is_admin=False)
            db.add(user)
            db.commit()
            db.refresh(user)
        conn.unbind()
        return user
    except Exception as e:
        print(f"Erreur LDAP: {e}")
        return None
