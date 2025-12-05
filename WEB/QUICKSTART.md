# 🚀 QUICK START

## 1. Installer Linux
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 1. Installer WIndows
```bash
python3 -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

## 2. Configurer
```bash
cp .env.example .env
# Éditer .env si besoin
```

## 3. Créer admin
```bash
python scripts/create_admin.py
```

## 4. Généré la clé SECRET_ENCRYPTION_KEY
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## 5. Lancer
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Accès: http://localhost:8000
API: http://localhost:8000/docs
