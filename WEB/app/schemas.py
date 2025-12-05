"""Schémas Pydantic"""
from pydantic import BaseModel, EmailStr, Field, StringConstraints, constr
from typing import Annotated, Optional, List
from datetime import datetime

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    is_admin: bool = False

class User(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    auth_method: str
    mfa_enabled: bool
    created_at: datetime
    last_login: Optional[datetime]
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    requires_mfa: bool = False

class LoginRequest(BaseModel):
    username: str
    password: str

class MFAVerifyRequest(BaseModel):
    token: str

class MFASetupResponse(BaseModel):
    secret: str
    qr_code_url: str

class MFAResetRequest(BaseModel):
    user_id: int

class ServerCreate(BaseModel):
    hostname: str
    ip_address: str
    description: Optional[str] = None
    ssh_port: int = 22
    ssh_username: str
    ssh_password: Optional[str] = None
    ssh_private_key: Optional[str] = None
    ssh_public_key: Optional[str] = None
    ssh_key_pass: Optional[str] = None
    connection_type: Optional[str] = None
    group_name: Optional[str] = None
    tags: Optional[str] = None
    os_type: Optional[str] = None

class ServerUpdate(BaseModel):
    hostname: str
    ssh_port: Optional[int]
    os_type: Optional[str]
    group_id: Optional[int] = None

class GroupCreate(BaseModel):
    name: str

class GroupOut(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

class Server(ServerCreate):
    id: int
    is_active: bool
    connection_status: str
    last_connection: Optional[datetime]
    created_at: datetime
    class Config:
        from_attributes = True

class ServerLight(BaseModel):
    id: int
    hostname: str
    ip_address: str
    ssh_port: Optional[int] = None
    os_type: Optional[str] = None
    connection_status: Optional[str] = None
    connection_type: Optional[str] = None
    group_id: Optional[int] = None
    group_name: Optional[str] = None
    is_active: Optional[bool] = None
    last_connection: Optional[datetime] = None
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class ScanCreate(BaseModel):
    server_ids: List[int]
    benchmark_level: int = Field(1, ge=1, le=2)

class ScanResponse(BaseModel):
    id: int
    server_id: int
    status: str
    score: Optional[float]
    passed_checks: int
    failed_checks: int
    started_at: datetime
    completed_at: Optional[datetime]
    class Config:
        from_attributes = True

class CommandExecute(BaseModel):
    server_id: int
    command: str

class FileTransferCreate(BaseModel):
    server_id: int
    local_path: str
    remote_path: str
    direction: str

class DashboardStats(BaseModel):
    total_servers: int
    active_servers: int
    total_scans: int
    average_score: Optional[float]
    servers_at_risk: int

class MessageResponse(BaseModel):
    message: str
    success: bool = True

class DeploySSHKeyRequest(BaseModel):
    server_id: int
    ssh_username: str
    ssh_password: str

class DiscoverRequest(BaseModel):
    network_range: Annotated[str, StringConstraints(min_length=9, max_length=18)]

class EditSshPortRequest(BaseModel):
    ssh_port: int

class PrepareAudityRequest(BaseModel):
    server_id: int
    ssh_username: str
    ssh_password: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str
    
class ChangeEmailRequest(BaseModel):
    new_email: EmailStr

class ScriptBase(BaseModel):
    name: str
    description: Optional[str] = None
    content: str
    os_type: str = "any"

class ScriptCreate(ScriptBase):
    pass

class ScriptUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    os_type: Optional[str] = None
    is_active: Optional[bool] = None

class ScriptOut(ScriptBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True

class RunScriptRequest(BaseModel):
    server_ids: List[int]

class ScriptExecutionOut(BaseModel):
    id: int
    script_id: int
    server_id: int
    status: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    output: Optional[str] = None

    class Config:
        from_attributes = True

class ScriptExecStats(BaseModel):
    script_id: int
    total: int
    success: int
    failed: int
    running: int
    pending: int

class ScriptExecutionDetail(BaseModel):
    id: int
    status: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    output: Optional[str] = None
    script_name: str
    server_hostname: str
    server_ip: str
    run_by: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None

    class Config:
        from_attributes = True
    
from pydantic import BaseModel

class WinRMCredentials(BaseModel):
    username: str
    password: str