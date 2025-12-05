import json
from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, case
from sqlalchemy.orm import Session
from datetime import datetime

from app.security.encryption import decrypt_value
from ..database import get_db
from ..models import Script, ScriptExecution, Server
from ..schemas import ScriptCreate, ScriptExecStats, ScriptExecutionDetail, ScriptUpdate, ScriptOut, RunScriptRequest, ScriptExecutionOut, MessageResponse
from ..dependencies import get_current_user, get_current_admin_user, create_audit_log
from ..ssh.manager import SSHManager, WindowsManager

router = APIRouter(prefix="/api/scripts", tags=["Scripts"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_model=list[ScriptOut])
async def list_scripts(current_user = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    if current_user.is_admin:
        scripts = db.query(Script).all()
        return scripts
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Action non autorisée")

@router.post("/", response_model=ScriptOut)
async def create_script(body: ScriptCreate,
                        current_user = Depends(get_current_admin_user),
                        db: Session = Depends(get_db)):
    if current_user.is_admin:
        pass
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Action non autorisée")
    script = Script(
            name=body.name,
            description=body.description,
            content=body.content,
            os_type=body.os_type,
            created_by_id=current_user.id,
        )
    db.add(script)
    db.commit()
    db.refresh(script)
    create_audit_log(db, current_user.id, "script_created", "script", script.id)
    return script

@router.put("/{script_id}", response_model=ScriptOut)
async def update_script(script_id: int,
                        body: ScriptUpdate,
                        current_user = Depends(get_current_admin_user),
                        db: Session = Depends(get_db)):
    if current_user.is_admin:
        pass
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Action non autorisée")
    script = db.query(Script).filter(Script.id == script_id).first()
    if not script:
        raise HTTPException(404, "Script introuvable")

    for field, value in body.dict(exclude_unset=True).items():
        setattr(script, field, value)
    script.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(script)
    create_audit_log(db, current_user.id, "script_updated", "script", script.id)
    return script

@router.delete("/{script_id}", response_model=MessageResponse)
async def delete_script(script_id: int,
                        current_user = Depends(get_current_admin_user),
                        db: Session = Depends(get_db)):
    if current_user.is_admin:
        pass
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Action non autorisée")
    script = db.query(Script).filter(Script.id == script_id).first()
    if not script:
        raise HTTPException(404, "Script introuvable")
    script.is_active = False
    db.commit()
    create_audit_log(db, current_user.id, "script_deleted", "script", script.id)
    return {"message": "Script désactivé"}

# Exécution
async def execute_script_on_server(exec_id: int, db_session_factory):
    db = next(db_session_factory())
    try:
        exec_obj = db.query(ScriptExecution).filter(ScriptExecution.id == exec_id).first()
        if not exec_obj:
            return
        script = exec_obj.script
        server = exec_obj.server

        exec_obj.status = "running"
        exec_obj.started_at = datetime.utcnow()
        db.commit()

        try:
            # Linux → SSH
            if server.os_type == "linux":
                ssh = SSHManager()
                username = decrypt_value(server.ssh_username) or server.ssh_username
                ok = ssh.connect(
                    server.ip_address,
                    server.ssh_port,
                    username,
                    None,  # pas de mot de passe stocké
                    server.ssh_private_key,
                    server.ssh_key_pass,
                )
                if not ok:
                    exec_obj.status = "failed"
                    exec_obj.output = "Erreur de connexion SSH"
                else:
                    result = ssh.execute_command(script.content)
                    exec_obj.output = json.dumps(result)[:10000]
                    stderr = (result.get("stderr") or "") if isinstance(result, dict) else ""
                    exec_obj.status = "failed" if stderr.strip() else "success"
                try:
                    ssh.close()
                except Exception:
                    pass

            # Windows → WinRM
            elif server.os_type == "windows":
                win_user = decrypt_value(server.ssh_username)
                win_pass = decrypt_value(server.ssh_password)
                if not win_user or not win_pass:
                    exec_obj.status = "failed"
                    exec_obj.output = "Identifiants WinRM non configurés"
                else:
                    wm = WindowsManager()
                    ok = wm.connect(
                        host=server.ip_address,
                        username=win_user,
                        password=win_pass,
                        port=getattr(server, "winrm_port", 5985),
                        use_ssl=getattr(server, "winrm_use_ssl", False),
                        transport=getattr(server, "winrm_transport", "ntlm"),
                    )
                    if not ok:
                        exec_obj.status = "failed"
                        exec_obj.output = f"Erreur de connexion WinRM: {wm.last_error or ''}"
                    else:
                        # Si ton script est PowerShell, utilise run_ps, sinon run_cmd
                        result = wm.run_ps(script.content)
                        exec_obj.output = json.dumps(result)[:10000]
                        stderr = (result.get("stderr") or "") if isinstance(result, dict) else ""
                        exec_obj.status = "failed" if stderr.strip() else "success"

            # OS inconnu / non supporté
            else:
                exec_obj.status = "failed"
                exec_obj.output = f"OS non supporté pour l'exécution de script: {server.os_type}"

        except Exception as e:
            exec_obj.status = "failed"
            exec_obj.output = f"Exception: {e}"
        finally:
            exec_obj.finished_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()

@router.post("/{script_id}/run", response_model=MessageResponse)
async def run_script_on_servers(
    script_id: int,
    body: RunScriptRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.is_admin:
        pass
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Action non autorisée")
    script = db.query(Script).filter(Script.id == script_id, Script.is_active == True).first()
    if not script:
        raise HTTPException(404, "Script introuvable")

    servers = db.query(Server).filter(Server.id.in_(body.server_ids)).all()
    if not servers:
        raise HTTPException(400, "Aucun serveur trouvé")

    count = 0
    for s in servers:
        exec_obj = ScriptExecution(
            script_id=script.id,
            server_id=s.id,
            run_by_id=current_user.id,
            status="pending",
        )
        db.add(exec_obj)
        db.commit()
        db.refresh(exec_obj)
        background_tasks.add_task(execute_script_on_server, exec_obj.id, get_db)
        count += 1

    create_audit_log(db, current_user.id, "script_run", "script", script.id)
    return {"message": f"Exécution lancée sur {count} serveurs"}

@router.get("/{script_id}/executions", response_model=list[ScriptExecutionOut])
async def list_script_executions(script_id: int,
                                current_user = Depends(get_current_user),
                                db: Session = Depends(get_db)):
    if current_user.is_admin:
        pass
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Action non autorisée")
    execs = (db.query(ScriptExecution)
            .filter(ScriptExecution.script_id == script_id)
            .order_by(ScriptExecution.started_at.desc())
            .limit(100)
            .all())
    return execs

@router.get("/{script_id}/stats", response_model=ScriptExecStats)
async def script_stats(script_id: int,
                       current_user = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    if current_user.is_admin:
        pass
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Action non autorisée")
    q = (
    db.query(
        func.count(ScriptExecution.id).label("total"),
        func.sum(case((ScriptExecution.status == "success", 1), else_=0)).label("success"),
        func.sum(case((ScriptExecution.status == "failed", 1), else_=0)).label("failed"),
        func.sum(case((ScriptExecution.status == "running", 1), else_=0)).label("running"),
        func.sum(case((ScriptExecution.status == "pending", 1), else_=0)).label("pending"),
    )
    .filter(ScriptExecution.script_id == script_id)
    )
    row = q.one()
    total = row.total or 0
    success = row.success or 0
    failed = row.failed or 0
    running = row.running or 0
    pending = row.pending or 0

    return ScriptExecStats(
        script_id=script_id,
        total=total,
        success=success,
        failed=failed,
        running=running,
        pending=pending,
    )

@router.get("/executions/{exec_id}", response_model=ScriptExecutionOut)
async def get_execution(exec_id: int,
                        current_user = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    if current_user.is_admin:
        pass
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Action non autorisée")
    exec_obj = db.query(ScriptExecution).filter(ScriptExecution.id == exec_id).first()
    if not exec_obj:
        raise HTTPException(404, "Exécution introuvable")
    return exec_obj
    
@router.get("/executions/{exec_id}/detail", response_model=ScriptExecutionDetail)
async def get_execution_detail(exec_id: int,
                            current_user = Depends(get_current_user),
                            db: Session = Depends(get_db)):
    if current_user.is_admin:
        pass
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Action non autorisée")
    exec_obj = db.query(ScriptExecution).filter(ScriptExecution.id == exec_id).first()
    if not exec_obj:
        raise HTTPException(404, "Exécution introuvable")
    try:
        obj = json.loads(exec_obj.output)
        stdout = obj.get("stdout")
        stderr = obj.get("stderr")
    except Exception:
        stderr = None
        stdout = None
    script = exec_obj.script
    server = exec_obj.server
    run_by = exec_obj.run_by
    return ScriptExecutionDetail(
        id=exec_obj.id,
        status=exec_obj.status,
        started_at=exec_obj.started_at,
        finished_at=exec_obj.finished_at,
        output=exec_obj.output,
        script_name=script.name if script else f"#{exec_obj.script_id}",
        server_hostname=server.hostname if server else str(exec_obj.server_id),
        server_ip=server.ip_address if server else "",
        run_by=run_by.username if run_by else None,
        stdout=stdout,
        stderr=stderr,
    )