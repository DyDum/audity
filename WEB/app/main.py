"""Application FastAPI principale avec support des templates"""
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from requests import Session

from app.dependencies import get_current_user
from app.models import ScriptExecution
from .config import settings
from .database import engine, Base, get_db
from .routers import auth, users, servers, scans, settings as settings_router, groups, scripts

# Créer les tables
Base.metadata.create_all(bind=engine)

# Initialiser FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    description="Serveur de gestion et d'exécution d'audit automatique de sécurité.",
    version="1.0.0",
    debug=settings.DEBUG
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else ["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration des fichiers statiques
static_path = Path(__file__).parent / "static"
static_path.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Configuration des templates
templates_path = Path(__file__).parent / "templates"
templates_path.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=str(templates_path))

# ============= INCLUSION DES ROUTERS =============
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(servers.router)
app.include_router(scans.router)
app.include_router(settings_router.router)
app.include_router(groups.router)
app.include_router(scripts.router)

# ============= ROUTES STATIQUES / PAGES =============

@app.get("/")
async def home():
    """Redirection vers la page de connexion"""
    return RedirectResponse(url="/login")


@app.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    """Page de connexion"""
    return templates.TemplateResponse("login.html", {
        "request": request,
        "app_name": settings.APP_NAME
    })


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Tableau de bord"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "app_name": settings.APP_NAME
    })


@app.get("/servers", response_class=HTMLResponse)
async def servers_page(request: Request):
    """Page de gestion des serveurs"""
    return templates.TemplateResponse("servers.html", {
        "request": request,
        "app_name": settings.APP_NAME
    })


@app.get("/scans", response_class=HTMLResponse)
async def scans_page(request: Request):
    """Page de gestion des scans"""
    return templates.TemplateResponse("scans.html", {
        "request": request,
        "app_name": settings.APP_NAME
    })


@app.get("/users", response_class=HTMLResponse)
async def users_page(request: Request):
    """Page de gestion des utilisateurs (admin seulement)"""
    return templates.TemplateResponse("users.html", {
        "request": request,
        "app_name": settings.APP_NAME
    })


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Page des paramètres (admin seulement)"""
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "app_name": settings.APP_NAME
    })

@app.get("/account", response_class=HTMLResponse)
async def account_page(request: Request):
    return templates.TemplateResponse(
        "account.html",
        {
            "request": request,
            "app_name": settings.APP_NAME
        },
    )

@app.get("/scripts", response_class=HTMLResponse)
async def scripts_page(request: Request):
    return templates.TemplateResponse(
        "scripts.html",
        {
            "request": request,
            "app_name": settings.APP_NAME
        },
    )

@app.get("/script-log/{execution_id}", response_class=HTMLResponse)
async def script_log_page(
    execution_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    exec_obj = db.query(ScriptExecution).filter(ScriptExecution.id == execution_id).first()
    if not exec_obj:
        raise HTTPException(404, "Log d'exécution introuvable")
    script = exec_obj.script
    server = exec_obj.server
    return templates.TemplateResponse(
        "script_log.html",
        {
            "request": request,
            "exec": exec_obj,
            "script": script,
            "server": server,
        }
    )
# ============= HEALTH CHECK =============

@app.get("/health")
async def health_check():
    """Endpoint de vérification de santé"""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": "1.0.0"
    }


@app.get("/docs-custom")
async def custom_docs():
    """Documentation personnalisée"""
    return {
        "endpoints": {
            "auth": "/api/auth/login",
            "servers": "/api/servers/",
            "scans": "/api/scans/",
            "users": "/api/users/",
            "settings": "/api/settings/auth"
        },
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc"
        }
    }
    
@app.get("/test")
async def test(request: Request):
    return templates.TemplateResponse("test.html", {"request": request})

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Gestionnaire 404"""
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=404, content={"detail": "Endpoint non trouvé"})
    return RedirectResponse(url="/dashboard")

# ============= GESTION DES ERREURS =============

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Gestionnaire 404"""
    if request.url.path.startswith("/api/"):
        return {"detail": "Endpoint non trouvé"}
    return RedirectResponse(url="/dashboard")


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Gestionnaire 500"""
    return {
        "detail": "Erreur interne du serveur",
        "error": str(exc) if settings.DEBUG else None
    }

# ============= STARTUP / SHUTDOWN =============

@app.on_event("startup")
async def startup_event():
    """Événement au démarrage"""
    print(f"🚀 {settings.APP_NAME} démarré")
    print(f"📖 Documentation: http://localhost:8000/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Événement à l'arrêt"""
    print(f"🛑 {settings.APP_NAME} arrêté")

# ============= LANCEMENT =============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
