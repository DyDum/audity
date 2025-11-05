#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import platform

def is_admin():
    """Check if the script is running with administrator/root privileges"""
    try:
        if platform.system() == "Windows":
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        else:
            # Unix-like systems (Linux, macOS)
            return os.geteuid() == 0
    except Exception:
        return False

def require_admin():
    """Require administrator/root privileges or exit"""
    if not is_admin():
        print("❌ This script must be run with administrator/root privileges.")
        print("   Linux/macOS: sudo python3 main.py")
        print("   Windows: Run as Administrator")
        sys.exit(1)

def get_current_user():
    """Get the current username"""
    try:
        if platform.system() == "Windows":
            return os.environ.get("USERNAME", "Unknown")
        else:
            import pwd
            return pwd.getpwuid(os.getuid()).pw_name
    except Exception:
        return "Unknown"
