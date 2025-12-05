import platform
import subprocess
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed
import socket

def ping_ip(ip, timeout=300):
    system = platform.system().lower()
    if system == "windows":
        result = subprocess.run(["ping", "-n", "1", "-w", str(timeout), ip], stdout=subprocess.DEVNULL)
    else:
        result = subprocess.run(["ping", "-c", "1", "-W", str(timeout//1000), ip], stdout=subprocess.DEVNULL)
    return result.returncode == 0

def is_port_open(ip, port, timeout=0.7):
    try:
        with socket.create_connection((ip, port), timeout):
            return True
    except Exception:
        return False

def detect_services(ip, user_port=None):
    mapping = [
        (22, "ssh"),
        (5985, "winrm"),
        (5986, "winrm_ssl"),
        (3389, "rdp"),
    ]
    tested_ports = set(port for port, _ in mapping)
    if user_port and user_port not in tested_ports:
        mapping.insert(0, (user_port, "custom"))
    for port, proto in mapping:
        if is_port_open(ip, port):
            return proto, port
    return None, None

def get_ssh_banner(ip, port=22, timeout=1.0):
    import socket
    try:
        sock = socket.create_connection((ip, port), timeout)
        banner = sock.recv(1024).decode(errors='ignore')
        sock.close()
        return banner.strip()
    except Exception:
        return None

def auto_detect_os(ip, port=22):
    # Teste SSH
    banner = get_ssh_banner(ip, port)
    if banner:
        if "OpenSSH" in banner:
            return "linux"
        elif "Win32" in banner or "Windows" in banner:
            return "windows"
        else:
            return "unknown"
    # Teste WinRM
    if is_port_open(ip, 5985) or is_port_open(ip, 5986):
        return "windows"
    # Teste RDP
    if is_port_open(ip, 3389):
        return "windows"
    return "unknown"