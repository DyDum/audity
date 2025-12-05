"""MFA avec TOTP"""
import pyotp
import qrcode
import io
import base64
from sqlalchemy.orm import Session
from ..models import User
from ..config import settings

def generate_mfa_secret() -> str:
    return pyotp.random_base32()

def get_totp_uri(user: User, secret: str) -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(name=user.email, issuer_name=settings.MFA_ISSUER)

def generate_qr_code(uri: str) -> str:
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{img_base64}"

def verify_totp(secret: str, token: str) -> bool:
    totp = pyotp.TOTP(secret)
    return totp.verify(token, valid_window=1)

def enable_mfa(db: Session, user: User) -> tuple:
    secret = generate_mfa_secret()
    user.mfa_secret = secret
    user.mfa_enabled = True
    db.commit()
    totp_uri = get_totp_uri(user, secret)
    qr_code = generate_qr_code(totp_uri)
    return secret, qr_code

def disable_mfa(db: Session, user: User):
    user.mfa_enabled = False
    user.mfa_secret = None
    db.commit()

def verify_mfa(user: User, token: str) -> bool:
    if not user.mfa_enabled or not user.mfa_secret:
        return False
    return verify_totp(user.mfa_secret, token)
