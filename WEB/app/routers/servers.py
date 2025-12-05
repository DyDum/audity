"""Routes gestion serveurs"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.security.encryption import decrypt_value, encrypt_value
from ..database import get_db
from ..models import Scan, ScriptExecution, Server
from ..schemas import ScriptExecutionOut, Server as ServerSchema, ServerCreate, CommandExecute, ServerLight, ServerUpdate, DeploySSHKeyRequest, DiscoverRequest, EditSshPortRequest, PrepareAudityRequest, WinRMCredentials
from ..dependencies import get_current_user, create_audit_log
from ..ssh.manager import SSHManager, WindowsManager
from ..ssh.discovery import auto_detect_os, detect_services, ping_ip
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import secrets
import ipaddress
import textwrap

router = APIRouter(prefix="/api/servers", tags=["Servers"])

@router.get("/", response_model=List[ServerSchema])
async def list_servers(skip: int = 0, limit: int = 100, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Lister les serveurs"""
    return db.query(Server).offset(skip).limit(limit).all()

@router.post("/", response_model=ServerSchema, status_code=status.HTTP_201_CREATED)
async def create_server(server_data: ServerCreate, request: Request, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Ajouter un serveur"""
    if current_user.is_admin is False:
        raise HTTPException(403, "Accès refusé")
    existing = db.query(Server).filter((Server.hostname == server_data.hostname) | (Server.ip_address == server_data.ip_address)).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Serveur déjà existant")

    server = Server(**server_data.dict(), created_by=current_user.id)
    db.add(server)
    db.commit()
    db.refresh(server)
    create_audit_log(db, current_user.id, "server_created", "server", server.id, request=request)
    return server

@router.post("/{server_id}/test-connection")
async def test_connection(server_id: int, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Tester connexion SSH"""
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Serveur introuvable")
    if current_user.is_admin is False:
        raise HTTPException(403, "Accès refusé")
    ssh = SSHManager()
    username = decrypt_value(server.ssh_username) or server.ssh_username
    if ssh.connect(server.ip_address, server.ssh_port, username, server.ssh_password, server.ssh_private_key, server.ssh_key_pass):
        server.connection_status = "connected"
        server.last_connection = datetime.today()
        ssh.close()
        db.commit()
        return {"message": "Connexion réussie"}
    else:
        server.connection_status = "error"
        db.commit()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Erreur de connexion")

@router.post("/{server_id}/execute")
async def execute_command(server_id: int, cmd: CommandExecute, request: Request, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Exécuter une commande"""
    if current_user.is_admin is False:
        raise HTTPException(403, "Accès refusé")
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Serveur introuvable")

    ssh = SSHManager()
    username = decrypt_value(server.ssh_username) or server.ssh_username
    if not ssh.connect(server.ip_address, server.ssh_port, username, server.ssh_password, server.ssh_private_key, server.ssh_key_pass):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Erreur de connexion")

    result = ssh.execute_command(cmd.command)
    ssh.close()
    create_audit_log(db, current_user.id, "command_executed", "server", server.id, request=request)
    return result

@router.delete("/{server_id}")
async def delete_server(
    server_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if current_user.is_admin is False:
        raise HTTPException(403, "Accès refusé")
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Serveur introuvable")
    # Supprime d'abord tous les scans liés
    db.query(Scan).filter(Scan.server_id == server_id).delete()
    db.delete(server)
    db.commit()
    return {"message": "Serveur supprimé (et tous les scans associés)"}

# ------- ROUTE DEFINITION ----------
@router.post("/deploy-ssh-key")
async def deploy_ssh_key(body: DeploySSHKeyRequest, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    if current_user.is_admin is False:
        raise HTTPException(403, "Accès refusé")
    generate_ssh_key(body.server_id, db)
    server = db.query(Server).filter(Server.id == body.server_id).first()
    if not server:
        raise HTTPException(404, "Serveur non trouvé")

    server.ssh_username = encrypt_value(body.ssh_username)
    db.commit()

    try:
        ssh = SSHManager()
        ok = ssh.connect(
            server.ip_address,
            server.ssh_port,
            body.ssh_username,
            body.ssh_password,
        )
        if not ok:
            return {"success": False, "error": "Échec de connexion SSH (login/mdp)"}

        cmds = [
            'mkdir -p ~/.ssh && chmod 700 ~/.ssh',
            f'echo "{server.ssh_public_key}" >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys'
        ]
        for cmd in cmds:
            result = ssh.execute_command(cmd)
            err = result['stderr']
            if err and not err.isspace():
                raise Exception(err)
    except Exception as e:
        return {"success": False, "error": f"SSH error: {e}"}
    finally:
        ssh.close()

    return {
        "success": True,
        "message": "Clé SSH générée et déposée sur le serveur."
    }

def generate_ssh_key(server_id: int, db: Session = Depends(get_db)):
    srv = db.query(Server).filter(Server.id == server_id).first()
    if not srv:
        raise HTTPException(status_code=404, detail="Serveur introuvable")

    # Générer un mot de passe fort aléatoire
    private_key_pass = secrets.token_urlsafe(24)

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem_private_key = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.BestAvailableEncryption(private_key_pass.encode())
    )
    pem_public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH
    )

    srv.ssh_private_key = pem_private_key.decode()
    srv.ssh_public_key = pem_public_key.decode()
    srv.ssh_key_pass = private_key_pass
    db.commit()

    return {
        "public_key": srv.ssh_public_key
    }
    
@router.post("/discover-smart")
async def discover_servers(body: DiscoverRequest, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    if current_user.is_admin is False:
        raise HTTPException(403, "Accès refusé")
    ips = [str(ip) for ip in ipaddress.ip_network(body.network_range, strict=False).hosts()]
    ajoutés, déjà = 0, 0
    entries = []

    # 1. Ping sweep rapide en parallèle
    with ThreadPoolExecutor(max_workers=100) as executor:
        ping_futures = {executor.submit(ping_ip, ip): ip for ip in ips}
        online_ips = []
        for fut in as_completed(ping_futures):
            ip = ping_futures[fut]
            if fut.result():
                online_ips.append(ip)
            else:
                entries.append({
                    'ip': ip,
                    'status': 'offline',
                    'added': False,
                    'proto': None,
                    'port': None
                })

    # 2. Détection de services sur les hôtes up
    with ThreadPoolExecutor(max_workers=50) as executor:
        scan_futures = {executor.submit(detect_services, ip): ip for ip in online_ips}
        for fut in as_completed(scan_futures):
            ip = scan_futures[fut]
            proto, found_port = fut.result()
            os_type = auto_detect_os(ip)
            exists = db.query(Server).filter(Server.ip_address == ip).first()
            if exists:
                déjà += 1
                continue
            srv = Server(
                hostname=ip,
                ip_address=ip,
                ssh_port=found_port if proto else None,
                connection_type=proto,
                os_type=os_type,
                ssh_username='',
                is_active=True,
            )
            db.add(srv)
            ajoutés += 1
            entries.append({
                'ip': ip,
                'status': 'online',
                'proto': proto,
                'os_type': os_type,
                'port': found_port,
                'added': True
            })
    db.commit()
    

    return {
        "added": ajoutés,
        "already": déjà,
        "results": entries
    }

@router.put("/{server_id}/update-ssh-port")
async def update_ssh_port(server_id: int, body: EditSshPortRequest, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    if current_user.is_admin is False:
        raise HTTPException(403, "Accès refusé")
    srv = db.query(Server).filter(Server.id == server_id).first()
    if not srv:
        raise HTTPException(status_code=404, detail="Serveur introuvable")
    proto, found_port = detect_services(srv.ip_address, body.ssh_port)
    srv.ssh_port = body.ssh_port
    srv.connection_type = proto if found_port == body.ssh_port else None

    # Vérifie et déduit l'OS si non défini ou "unknown"
    if not srv.os_type or srv.os_type == "unknown":
        detected_os = auto_detect_os(srv.ip_address, srv.ssh_port)
        srv.os_type = detected_os

    db.commit()

    if proto and found_port == body.ssh_port:
        return JSONResponse(status_code=200, content={
            "message": f"Port {body.ssh_port} ouvert, type {proto} détecté. OS: {srv.os_type}"
        })
    else:
        return JSONResponse(status_code=200, content={
            "message": f"Erreur : Port {body.ssh_port} non enregistré, il n'est pas ouvert/un service distant n'a pas été détecté sur {srv.ip_address}. OS: {srv.os_type}"
        })

@router.put("/{server_id}", response_model=ServerSchema)
def update_server(server_id: int, body: ServerUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    if current_user.is_admin is False:
        raise HTTPException(403, "Accès refusé")
    srv = db.query(Server).filter(Server.id==server_id).first()
    if not srv:
        raise HTTPException(404, "Serveur introuvable")
    srv.hostname = body.hostname
    srv.ssh_port = body.ssh_port
    srv.os_type = body.os_type
    srv.group_id = body.group_id
    db.commit(); db.refresh(srv)
    return srv

@router.get("/{server_id}/executions", response_model=list[ScriptExecutionOut])
async def server_script_executions(server_id: int,
                                   current_user = Depends(get_current_user),
                                   db: Session = Depends(get_db)):
    execs = (db.query(ScriptExecution)
               .filter(ScriptExecution.server_id == server_id)
               .order_by(ScriptExecution.started_at.desc())
               .limit(100)
               .all())
    return execs

@router.get("/list", response_model=List[ServerLight])
async def list_servers_light(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    servers = (
        db.query(Server)
        .offset(skip)
        .limit(limit)
        .all()
    )

    result = []
    for s in servers:
        result.append({
            "id": s.id,
            "hostname": s.hostname,
            "ip_address": s.ip_address,
            "ssh_port": s.ssh_port,
            "os_type": s.os_type,
            "connection_status": s.connection_status,
            "connection_type": s.connection_type,
            "group_id": s.group_id,
            "group_name": s.group.name if s.group else None,
            "is_active": s.is_active,
            "last_connection": s.last_connection,
            "created_at": s.created_at,
        })
    return result

@router.post("/prepare-audity")
async def prepare_audity_env(body: PrepareAudityRequest, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    if current_user.is_admin is False:
        raise HTTPException(403, "Accès refusé")
    server = db.query(Server).filter(Server.id == body.server_id).first()
    if server.os_type == "linux":
        return await prepare_audity_linux(body, db)
    elif server.os_type == "windows":
        return await prepare_audity_windows(body, db)
    elif server.os_type == None:
        # tenter de détecter l'OS
        detected_os = auto_detect_os(server.ip_address, server.ssh_port)
        server.os_type = detected_os
        db.commit()
        if detected_os == "linux":
            return await prepare_audity_linux(body, db)
        elif detected_os == "windows":
            return await prepare_audity_windows(body, db)
        else:
            return {"success": False, "error": "OS non détecté, impossible de préparer Audity"}
    else:
        return {"success": False, "error": "OS non supporté pour la préparation Audity"}
    
async def prepare_audity_linux(body: PrepareAudityRequest, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    server = db.query(Server).filter(Server.id == body.server_id).first()
    if not server:
        raise HTTPException(404, "Serveur non trouvé")

    ssh = SSHManager()
    try:
        ok = ssh.connect(
            server.ip_address,
            server.ssh_port,
            body.ssh_username,
            body.ssh_password,
            server.ssh_private_key,
            server.ssh_key_pass,
        )
        if not ok:
            raise HTTPException(503, "Erreur de connexion SSH (login/mdp ou clé)")

        # 1) Créer un script temporaire sur le serveur
        script_content = textwrap.dedent(f"""\
            #!/bin/bash
            set -e
            mkdir -p /home/{body.ssh_username}/audity/rules
            chown root:{body.ssh_username} /home/{body.ssh_username}/audity/rules
            chmod 1770 /home/{body.ssh_username}/audity/rules
            echo "{body.ssh_username} ALL=(root) NOPASSWD: /usr/bin/python3 /home/{body.ssh_username}/audity/script.py" > /etc/sudoers.d/audity
            chmod 440 /etc/sudoers.d/audity
        """)

        # envoyer le script via echo/cat
        tmp_path = "/tmp/audity_setup.sh"
        # on échappe les EOF, pas besoin de sudo pour écrire dans /tmp
        cmd_create = f"cat > {tmp_path} << 'EOF'\n{script_content}\nEOF"
        res = ssh.execute_command(cmd_create)
        if not res["success"]:
            raise Exception(f"Erreur création script: {res['stderr'] or res['stdout']}")

        # rendre exécutable
        res = ssh.execute_command(f"chmod +x {tmp_path}")
        if not res["success"]:
            raise Exception(f"Erreur chmod script: {res['stderr'] or res['stdout']}")

        # 2) Exécuter le script avec sudo -S (tout en une fois)
        res = ssh.execute_command(
            f"sudo -S bash {tmp_path}",
            input_data=body.ssh_password + "\n"
        )
        stdout = (res.get("stdout") or "").strip()
        stderr = (res.get("stderr") or "").strip()
        if not res["success"]:
            raise Exception(stderr or stdout)

        # 3) Optionnel: supprimer le script
        ssh.execute_command(f"rm -f {tmp_path}")

    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": f"Erreur préparation Audity: {e}"}
    finally:
        try:
            ssh.close()
        except Exception:
            pass

    return {
        "success": True,
        "message": "Environnement Audity préparé (dossiers + sudoers)."
    }

async def prepare_audity_windows(body: PrepareAudityRequest, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    server = db.query(Server).filter(Server.id == body.server_id).first()
    if not server:
        raise HTTPException(404, "Serveur non trouvé")

    ssh = SSHManager()
    try:
        ok = ssh.connect(
            server.ip_address,
            server.ssh_port,
            body.ssh_username,
            body.ssh_password,
            server.ssh_private_key,
            server.ssh_key_pass,
        )
        if not ok:
            raise HTTPException(503, "Erreur de connexion SSH (login/mdp ou clé)")

        script_content = textwrap.dedent(f"""\
            New-Item -ItemType Directory -Path "C:\\Users\\{body.ssh_username}\\Audity\\Rules" -Force | Out-Null
            icacls "C:\\Users\\{body.ssh_username}\\Audity\\Rules" /grant "BUILTIN\\Administrators:(OI)(CI)F" /grant "{body.ssh_username}:(OI)(CI)M" /T
        """)

        tmp_path = r"C:\Windows\Temp\audity_setup.ps1"
        cmd_create = (
            f'powershell -Command "@\'\n'
            f'{script_content}\n'
            f'\'@ | Out-File -FilePath \'{tmp_path}\' -Encoding UTF8"'
        )
        res = ssh.execute_command(cmd_create)
        if not res["success"]:
            raise Exception(f"Erreur création script: {res['stderr'] or res['stdout']}")

        res = ssh.execute_command(f'powershell -ExecutionPolicy Bypass -File "{tmp_path}"')
        stdout = (res.get("stdout") or "").strip()
        stderr = (res.get("stderr") or "").strip()
        if not res["success"]:
            raise Exception(stderr or stdout)

        ssh.execute_command(f'del "{tmp_path}"')

    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": f"Erreur préparation Audity: {e}"}
    finally:
        try:
            ssh.close()
        except Exception:
            pass

    return {
        "success": True,
        "message": "Environnement Audity préparé (dossiers Windows)."
    }

@router.post("/{server_id}/winrm-credentials")
async def set_winrm_credentials(
    server_id: int,
    body: WinRMCredentials,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
    ):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé")

    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Serveur introuvable")

    if server.os_type != "windows":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="WinRM uniquement pour les serveurs Windows")

    # Stockage chiffré dans ssh_username / ssh_password
    server.ssh_username = encrypt_value(body.username)
    server.ssh_password = encrypt_value(body.password)

    db.commit()
    create_audit_log(db, current_user.id, "winrm_credentials_set", "server", server.id)

    return {"message": "Identifiants WinRM enregistrés"}

@router.post("/{server_id}/test-winrm")
async def test_winrm_connection(
    server_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Accès refusé")

    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Serveur introuvable")

    if server.os_type != "windows":
        raise HTTPException(status_code=400, detail="WinRM uniquement pour serveurs Windows")

    username = decrypt_value(server.ssh_username)
    password = decrypt_value(server.ssh_password)
    if not username or not password:
        raise HTTPException(status_code=400, detail="Identifiants WinRM non configurés")

    wm = WindowsManager()
    ok = wm.connect(
        host=server.ip_address,
        username=username,
        password=password,
        port=getattr(server, "winrm_port", 5985),
        use_ssl=getattr(server, "winrm_use_ssl", False),
        transport=getattr(server, "winrm_transport", "ntlm"),
    )
    if not ok:
        detail = wm.last_error or "Erreur de connexion WinRM"
        raise HTTPException(status_code=503, detail=detail)

    # petit test
    result = wm.run_cmd("echo", ["ok"])
    if not result.get("success"):
        raise HTTPException(
            status_code=503,
            detail=f"Commande WinRM échouée: code={result.get('exit_code')}, stderr={result.get('stderr')}"
        )


    server.connection_status = "connected"
    server.last_connection = datetime.today()
    db.commit()

    return {"message": "Connexion WinRM réussie"}