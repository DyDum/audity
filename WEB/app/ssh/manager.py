from cryptography.hazmat.primitives.serialization import load_pem_private_key, Encoding, PrivateFormat, NoEncryption
import paramiko
import winrm
from typing import List, Optional, Dict, Any
from pathlib import Path
from io import StringIO

class SSHManager:
    def __init__(self):
        self.client: Optional[paramiko.SSHClient] = None

    def connect(self, hostname: str, port: int = 22, username: str = None,
                password: str = None,
                private_key: str = None, private_key_pass: str = None,
                timeout: int = 30) -> bool:
        """Établit une connexion SSH via Paramiko"""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            connect_kwargs = {'hostname': hostname, 'port': port, 'username': username, 'timeout': timeout}

            if private_key:
                # Charge la clé PEM en RAM (StringIO) et déchiffre avec le password
                key = load_pem_private_key(
                        private_key.encode(),
                        password=private_key_pass.encode() if private_key_pass else None,
                    )
                rsa_pem = key.private_bytes(
                    encoding=Encoding.PEM,
                    format=PrivateFormat.TraditionalOpenSSL,  # PKCS1 !
                    encryption_algorithm=NoEncryption()
                )
                connect_kwargs['pkey'] = paramiko.RSAKey.from_private_key(StringIO(rsa_pem.decode()))
            elif password:
                connect_kwargs['password'] = password
            else:
                raise ValueError("Mot de passe ou clé SSH requis pour se connecter")

            self.client.connect(**connect_kwargs)
            return True
        except Exception as e:
            print(f"Erreur SSH: {e}")
            if self.client:
                self.client.close()
                self.client = None
            return False


    def execute_command(self, command: str, timeout: int = 300, input_data: Optional[str] = None) -> Dict[str, Any]:
        """Exécuter une commande, avec possibilité d'envoyer des données sur stdin (ex: mot de passe sudo)."""
        if not self.client:
            return {
                'success': False,
                'error': 'Pas de connexion active',
                'stdout': '',
                'stderr': '',
                'exit_code': -1
            }
        try:
            stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)

            if input_data:
                stdin.write(input_data)
                stdin.flush()

            stdout_text = stdout.read().decode('utf-8', errors='replace')
            stderr_text = stderr.read().decode('utf-8', errors='replace')
            exit_code = stdout.channel.recv_exit_status()

            return {
                'success': exit_code == 0,
                'stdout': stdout_text,
                'stderr': stderr_text,
                'exit_code': exit_code,
                'error': None
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'stdout': '',
                'stderr': '',
                'exit_code': -1
            }

    def upload_file(self, local_path: str, remote_path: str) -> Dict[str, Any]:
        """Upload un fichier"""
        if not self.client:
            return {'success': False, 'error': 'Pas de connexion active'}
        try:
            sftp = self.client.open_sftp()
            local_file = Path(local_path)
            if not local_file.exists():
                return {'success': False, 'error': f'Fichier local introuvable: {local_path}'}
            sftp.put(str(local_file), remote_path)
            file_size = local_file.stat().st_size
            sftp.close()
            return {'success': True, 'message': f'Fichier uploadé: {remote_path}', 'file_size': file_size}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def download_file(self, remote_path: str, local_path: str) -> Dict[str, Any]:
        """Download un fichier"""
        if not self.client:
            return {'success': False, 'error': 'Pas de connexion active'}
        try:
            sftp = self.client.open_sftp()
            local_file = Path(local_path)
            local_file.parent.mkdir(parents=True, exist_ok=True)
            sftp.get(remote_path, str(local_file))
            file_size = local_file.stat().st_size
            sftp.close()
            return {'success': True, 'message': f'Fichier téléchargé: {local_path}', 'file_size': file_size}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def close(self):
        """Fermer la connexion"""
        if self.client:
            self.client.close()
            self.client = None

class WindowsManager:
    def __init__(self):
        self.session = None
        self.last_error = None

    def connect(self, host: str, username: str, password: str,
                port: int = 5985, use_ssl: bool = False, transport: str = "ntlm"):
        scheme = "https" if use_ssl else "http"
        endpoint = f"{scheme}://{host}:{port}/wsman"
        try:
            self.session = winrm.Session(
                endpoint,
                auth=(username, password),
                transport=transport,
            )
            # petit test
            r = self.session.run_cmd('echo', ['ok'])
            if r.status_code == 0:
                self.last_error = None
                return True
            else:
                self.last_error = f"status_code={r.status_code}, stderr={r.std_err.decode(errors='ignore')}"
                return False
        except Exception as e:
            self.session = None
            self.last_error = str(e)
            return False

    def run_cmd(self, command: str, args=None):
        if not self.session:
            return {"success": False, "stdout": "", "stderr": "No WinRM session", "exit_code": -1}
        try:
            r = self.session.run_cmd(command, args or [])
            return {
                "success": r.status_code == 0,
                "stdout": r.std_out.decode(errors="ignore"),
                "stderr": r.std_err.decode(errors="ignore"),
                "exit_code": r.status_code,
            }
        except Exception as e:
            return {"success": False, "stdout": "", "stderr": str(e), "exit_code": -1}

    def run_ps(self, script: str):
        if not self.session:
            return {"success": False, "stdout": "", "stderr": "No WinRM session", "exit_code": -1}
        try:
            r = self.session.run_ps(script)
            return {
                "success": r.status_code == 0,
                "stdout": r.std_out.decode(errors="ignore"),
                "stderr": r.std_err.decode(errors="ignore"),
                "exit_code": r.status_code,
            }
        except Exception as e:
            return {"success": False, "stdout": "", "stderr": str(e), "exit_code": -1}