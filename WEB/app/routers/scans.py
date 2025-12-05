"""Routes scans CIS"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from ..database import SessionLocal, get_db
from ..models import Scan, Server
from ..ssh.manager import SSHManager
from ..schemas import ScanCreate, ScanResponse, DashboardStats
from ..dependencies import get_current_user, create_audit_log
from sqlalchemy import func

router = APIRouter(prefix="/api/scans", tags=["Scans"])

@router.post("/", response_model=List[ScanResponse], status_code=status.HTTP_201_CREATED)
async def create_scan(
    scan_data: ScanCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lancer un scan (non bloquant, 1 tâche background par serveur)."""
    scans = []
    for server_id in scan_data.server_ids:
        scan = Scan(
            server_id=server_id,
            user_id=current_user.id,
            benchmark_level=scan_data.benchmark_level,
            status="queued",
        )
        db.add(scan)
        db.commit()
        db.refresh(scan)
        scans.append(scan)

        create_audit_log(db, current_user.id, "scan_started", "scan", scan.id, request=request)

        # Tâche background, non bloquante pour l'utilisateur
        background_tasks.add_task(run_scan_for_scan_row, scan.id, SessionLocal)

    return scans

@router.get("/", response_model=List[ScanResponse])
async def list_scans(skip: int = 0, limit: int = 100, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Lister les scans"""
    return db.query(Scan).order_by(Scan.started_at.desc()).offset(skip).limit(limit).all()

@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_stats(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Statistiques dashboard"""
    from ..models import Server
    total_servers = db.query(Server).count()
    active_servers = db.query(Server).filter(Server.is_active == True).count()
    total_scans = db.query(Scan).count()
    avg_score = db.query(func.avg(Scan.score)).filter(Scan.status == "completed", Scan.score.isnot(None)).scalar()
    servers_at_risk = 0
    return {
        "total_servers": total_servers,
        "active_servers": active_servers,
        "total_scans": total_scans,
        "scans_last_24h": 0,
        "average_score": round(avg_score, 2) if avg_score else None,
        "servers_at_risk": servers_at_risk
    }

def run_scan_for_scan_row(scan_id: int, db_session_factory):
    # IMPORTANT : recréer une session dans le thread background
    db: Session = db_session_factory()
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            return

        server = db.query(Server).filter(Server.id == scan.server_id).first()
        if not server:
            scan.status = "error"
            scan.error_message = "Serveur introuvable"
            db.commit()
            return

        scan.status = "running"
        scan.started_at = datetime.utcnow()
        db.commit()

        ssh = SSHManager()
        connected = ssh.connect(
            server.ip_address,
            server.ssh_port,
            server.ssh_username,
            server.ssh_password,
            server.ssh_private_key,
            server.ssh_key_pass,
        )
        if not connected:
            scan.status = "error"
            scan.error_message = "Erreur de connexion SSH"
            db.commit()
            return

        commands = [
            "whoami",
            "uname -a",
            "cat /etc/os-release || type lsb_release",
        ]
        results = {}
        for cmd in commands:
            res = ssh.execute_command(cmd)
            results[cmd] = {
                "stdout": res.get("stdout"),
                "stderr": res.get("stderr"),
                "exit_code": res.get("exit_code"),
            }

        ssh.close()

        # Score fictif, à améliorer
        scan.score = 100.0
        scan.results = str(results)
        scan.status = "completed"
        scan.completed_at = datetime.utcnow()

        server.connection_status = "scanned"
        server.last_connection = datetime.utcnow()

        db.commit()
    except Exception as e:
        try:
            scan = db.query(Scan).filter(Scan.id == scan_id).first()
            if scan:
                scan.status = "error"
                scan.error_message = str(e)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()