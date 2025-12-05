"""Configuration de l'application"""
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Base de données
    DATABASE_URL: str = "sqlite:///./cis_benchmarks.db"

    # Sécurité
    SECRET_KEY: str = "changez-moi-en-production-clé-très-longue-et-aléatoire"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Application
    APP_NAME: str = "CIS Benchmarks Management"
    DEBUG: bool = True

    # Azure AD (optionnel)
    AZURE_CLIENT_ID: Optional[str] = None
    AZURE_CLIENT_SECRET: Optional[str] = None
    AZURE_TENANT_ID: Optional[str] = None
    AZURE_ENABLED: bool = False

    # Windows AD / LDAP (optionnel)
    LDAP_SERVER: Optional[str] = None
    LDAP_DOMAIN: Optional[str] = None
    LDAP_BASE_DN: Optional[str] = None
    LDAP_ENABLED: bool = False

    # MFA
    MFA_ISSUER: str = "Audity Server"
    
    SECRET_ENCRYPTION_KEY: str

    class Config:
        env_file = ".env"

settings = Settings()
