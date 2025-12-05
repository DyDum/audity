from typing import Optional
from cryptography.fernet import Fernet
from app.config import settings

fernet = Fernet(settings.SECRET_ENCRYPTION_KEY.encode())

def encrypt_value(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return fernet.encrypt(value.encode()).decode()

def decrypt_value(token: Optional[str]) -> Optional[str]:
    if not token:
        return None
    return fernet.decrypt(token.encode()).decode()
