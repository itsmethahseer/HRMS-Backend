from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, date


# ─── Permission Schemas ────────────────────────────────────────────────────────
class PermissionBase(BaseModel):
    name: str
    resource: str
    action: str
    description: Optional[str] = None


class PermissionCreate(PermissionBase):
    pass


class PermissionOut(PermissionBase):
    id: int

    class Config:
        from_attributes = True


# ─── Role Schemas ──────────────────────────────────────────────────────────────
class RolePermissionOut(BaseModel):
    id: int
    permission_id: int
    permission: Optional[PermissionOut] = None

    class Config:
        from_attributes = True


class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: Optional[bool] = True


class RoleCreate(RoleBase):
    permission_ids: Optional[List[int]] = []


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    permission_ids: Optional[List[int]] = None


class RoleOut(RoleBase):
    id: int
    permissions: List[RolePermissionOut] = []

    class Config:
        from_attributes = True


# ─── Department Schemas ────────────────────────────────────────────────────────
class DepartmentBase(BaseModel):
    name: str
    description: Optional[str] = None
    head_id: Optional[int] = None
    is_active: Optional[bool] = True


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    head_id: Optional[int] = None
    is_active: Optional[bool] = None


class Department(DepartmentBase):
    id: int

    class Config:
        from_attributes = True


# ─── Designation Schemas ───────────────────────────────────────────────────────
class DesignationBase(BaseModel):
    title: str
    description: Optional[str] = None
    department_id: Optional[int] = None
    is_active: Optional[bool] = True


class DesignationCreate(DesignationBase):
    pass


class DesignationUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    department_id: Optional[int] = None
    is_active: Optional[bool] = None


class Designation(DesignationBase):
    id: int

    class Config:
        from_attributes = True


# ─── WorkLocation Schemas ──────────────────────────────────────────────────────
class WorkLocationBase(BaseModel):
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = "India"
    pincode: Optional[str] = None
    is_active: Optional[bool] = True


class WorkLocationCreate(WorkLocationBase):
    pass


class WorkLocationUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    pincode: Optional[str] = None
    is_active: Optional[bool] = None


class WorkLocation(WorkLocationBase):
    id: int

    class Config:
        from_attributes = True


# ─── User / Employee Schemas ───────────────────────────────────────────────────
class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    phone_number: Optional[str] = None
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    job_title: Optional[str] = None
    employee_code: Optional[str] = None
    department_id: Optional[int] = None
    designation_id: Optional[int] = None
    work_location_id: Optional[int] = None
    role_id: Optional[int] = None
    manager_id: Optional[int] = None
    date_of_joining: Optional[date] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    job_title: Optional[str] = None
    employee_code: Optional[str] = None
    department_id: Optional[int] = None
    designation_id: Optional[int] = None
    work_location_id: Optional[int] = None
    role_id: Optional[int] = None
    manager_id: Optional[int] = None
    date_of_joining: Optional[date] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    password: Optional[str] = None


class User(UserBase):
    id: int
    created_at: Optional[datetime] = None
    department: Optional[Department] = None
    designation: Optional[Designation] = None
    work_location: Optional[WorkLocation] = None
    role: Optional[RoleOut] = None

    class Config:
        from_attributes = True


# ─── Employee Directory (lightweight) ─────────────────────────────────────────
class EmployeeDirectoryItem(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    job_title: Optional[str] = None
    phone_number: Optional[str] = None
    department: Optional[Department] = None
    designation: Optional[Designation] = None
    work_location: Optional[WorkLocation] = None

    class Config:
        from_attributes = True


# ─── Exit / Offboarding ───────────────────────────────────────────────────────
class InitiateExitRequest(BaseModel):
    exit_date: date
    exit_reason: str
    exit_type: str  # resignation, termination, retirement


# ─── Org Chart Node ───────────────────────────────────────────────────────────
class OrgChartNode(BaseModel):
    id: int
    name: str
    job_title: Optional[str] = None
    department: Optional[str] = None
    manager_id: Optional[int] = None

    class Config:
        from_attributes = True
