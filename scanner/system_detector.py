#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import platform
import subprocess
from typing import Dict, List, Optional

class SystemDetector:
    """Detects operating system and installed packages"""

    def __init__(self, logger=None):
        self.logger = logger
        self.os_info = {}
        self.installed_packages = []

    def detect_os(self) -> Dict[str, str]:
        """Detect operating system information"""
        try:
            system = platform.system()

            if system == "Linux":
                self.os_info = self._detect_linux_distro()
            elif system == "Windows":
                self.os_info = self._detect_windows()
            else:
                self.os_info = {
                    "os": system,
                    "distribution": "Unknown",
                    "version": platform.version(),
                    "kernel": platform.release()
                }

            if self.logger:
                self.logger.info(f"OS detected: {self.os_info.get('distribution')} {self.os_info.get('version')}")

            return self.os_info
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error detecting OS: {e}")
            return {}

    def _detect_linux_distro(self) -> Dict[str, str]:
        """Detect Linux distribution"""
        info = {
            "os": "Linux",
            "distribution": "Unknown",
            "version": "Unknown",
            "kernel": platform.release()
        }

        # Try /etc/os-release (standard method)
        if os.path.exists("/etc/os-release"):
            with open("/etc/os-release", "r") as f:
                for line in f:
                    if line.startswith("NAME="):
                        info["distribution"] = line.split("=")[1].strip().strip('"')
                    elif line.startswith("VERSION_ID="):
                        info["version"] = line.split("=")[1].strip().strip('"')

        # Fallback to /etc/debian_version
        elif os.path.exists("/etc/debian_version"):
            info["distribution"] = "Debian"
            with open("/etc/debian_version", "r") as f:
                info["version"] = f.read().strip()

        return info

    def _detect_windows(self) -> Dict[str, str]:
        """Detect Windows version"""
        return {
            "os": "Windows",
            "distribution": platform.system(),
            "version": platform.release(),
            "kernel": platform.version()
        }

    def detect_packages(self) -> List[str]:
        """Detect installed packages/services"""
        if self.logger:
            self.logger.info("Detecting installed packages...")

        packages = []

        # Apache HTTP
        if self._is_package_installed("apache2") or self._is_package_installed("httpd"):
            packages.append("apache_http")

        # Apache Tomcat
        if self._is_package_installed("tomcat10") or self._find_process("tomcat"):
            packages.append("apache_tomcat_10.1")

        # Nginx
        if self._is_package_installed("nginx"):
            packages.append("nginx")

        # MariaDB
        if self._is_package_installed("mariadb-server"):
            packages.append("mariadb")

        # PostgreSQL
        if self._is_package_installed("postgresql"):
            packages.append("postgresql")

        # MongoDB
        if self._is_package_installed("mongodb") or self._is_package_installed("mongodb-server"):
            packages.append("mongodb")

        # SQL Server (Linux)
        if self._is_package_installed("mssql-server"):
            packages.append("sql_server")

        self.installed_packages = packages

        if self.logger:
            self.logger.info(f"Detected packages: {', '.join(packages) if packages else 'None'}")

        return packages

    def _is_package_installed(self, package_name: str) -> bool:
        """Check if a package is installed"""
        try:
            # Debian/Ubuntu (dpkg)
            if os.path.exists("/usr/bin/dpkg"):
                result = subprocess.run(
                    ["dpkg", "-l", package_name],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return result.returncode == 0 and "ii" in result.stdout

            # Red Hat/CentOS (rpm)
            elif os.path.exists("/usr/bin/rpm"):
                result = subprocess.run(
                    ["rpm", "-q", package_name],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return result.returncode == 0

            return False
        except Exception:
            return False

    def _find_process(self, process_name: str) -> bool:
        """Check if a process is running"""
        try:
            result = subprocess.run(
                ["pgrep", "-f", process_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def get_applicable_rules_dirs(self, rules_base_dir: str) -> List[str]:
        """Get list of applicable rules directories based on OS and packages"""
        applicable_dirs = []

        # Always include OS-specific rules
        os_name = self.os_info.get("distribution", "").lower()
        if "debian" in os_name or "ubuntu" in os_name:
            debian_dir = os.path.join(rules_base_dir, "debian")
            if os.path.exists(debian_dir):
                applicable_dirs.append(debian_dir)

        # Add package-specific rules
        for package in self.installed_packages:
            package_dir = os.path.join(rules_base_dir, package)
            if os.path.exists(package_dir):
                applicable_dirs.append(package_dir)

        if self.logger:
            self.logger.info(f"Applicable rules directories: {len(applicable_dirs)}")
            for dir in applicable_dirs:
                self.logger.debug(f"  - {dir}")

        return applicable_dirs
