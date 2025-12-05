"""Modèles SQLAlchemy"""
from sqlalchemy import Boolean, Column, Integer, String, DateTime, Float, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)

    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    auth_method = Column(String(50), default="local")

    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    scans = relationship("Scan", back_populates="user")


class AuthSettings(Base):
    __tablename__ = "auth_settings"

    id = Column(Integer, primary_key=True, index=True)

    azure_enabled = Column(Boolean, default=False)
    azure_client_id = Column(String(255), nullable=True)
    azure_client_secret = Column(String(255), nullable=True)
    azure_tenant_id = Column(String(255), nullable=True)

    ldap_enabled = Column(Boolean, default=False)
    ldap_server = Column(String(255), nullable=True)
    ldap_port = Column(Integer, default=389)
    ldap_domain = Column(String(255), nullable=True)
    ldap_base_dn = Column(String(255), nullable=True)
    ldap_use_ssl = Column(Boolean, default=False)

    mfa_required_for_admins = Column(Boolean, default=True)
    mfa_required_for_users = Column(Boolean, default=False)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)


class Server(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(String(255), nullable=False)
    ip_address = Column(String(50), nullable=False)
    os_type = Column(String(50), nullable=True)
    connection_type = Column(String, nullable=True)

    ssh_port = Column(Integer, default=22)
    ssh_username = Column(String(100), nullable=False)
    ssh_password = Column(String(255), nullable=True)
    ssh_public_key = Column(String, nullable=True)
    ssh_private_key = Column(String, nullable=True)
    ssh_key_pass = Column(String(255), nullable=True)

    is_active = Column(Boolean, default=True)
    last_connection = Column(DateTime, nullable=True)
    connection_status = Column(String(50), default="unknown")

    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)
    group = relationship("Group")

    os_type = Column(String(50), nullable=True)
    os_version = Column(String(100), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    scans = relationship("Scan", back_populates="server")
    



class Scan(Base):
    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    scan_type = Column(String(50), default="cis_benchmark")
    benchmark_level = Column(Integer, default=1)

    status = Column(String(50), default="pending")
    score = Column(Float, nullable=True)
    passed_checks = Column(Integer, default=0)
    failed_checks = Column(Integer, default=0)
    total_checks = Column(Integer, default=0)

    output = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)

    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    server = relationship("Server", back_populates="scans")
    user = relationship("User", back_populates="scans")


class CommandExecution(Base):
    __tablename__ = "command_executions"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    command = Column(Text, nullable=False)
    status = Column(String(50), default="pending")
    stdout = Column(Text, nullable=True)
    stderr = Column(Text, nullable=True)
    exit_code = Column(Integer, nullable=True)

    executed_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class FileTransfer(Base):
    __tablename__ = "file_transfers"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    local_path = Column(String(500), nullable=False)
    remote_path = Column(String(500), nullable=False)
    direction = Column(String(20), nullable=False)
    file_size = Column(Integer, nullable=True)

    status = Column(String(50), default="pending")
    error_message = Column(Text, nullable=True)

    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(Integer, nullable=True)

    details = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

class Script(Base):
    __tablename__ = "scripts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=False)  # le script bash/powershell
    os_type = Column(String, nullable=False, default="any")
    is_active = Column(Boolean, default=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    created_by = relationship("User", backref="scripts")

class ScriptExecution(Base):
    __tablename__ = "script_executions"

    id = Column(Integer, primary_key=True, index=True)
    script_id = Column(Integer, ForeignKey("scripts.id"), nullable=False)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    run_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String, default="pending")  # pending | running | success | failed
    output = Column(Text, nullable=True)        # stdout/stderr tronqué

    script = relationship("Script", backref="executions")
    server = relationship("Server", backref="script_executions")
    run_by = relationship("User", backref="script_executions")