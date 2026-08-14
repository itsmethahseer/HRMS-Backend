from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# --- Department Schemas ---
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


# --- Designation Schemas ---
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


# --- WorkLocation Schemas ---
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


# --- User/Employee Schemas ---
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
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    password: Optional[str] = None


class User(UserBase):
    id: int
    created_at: Optional[datetime] = None
    department: Optional[Department] = None
    designation: Optional[Designation] = None
    work_location: Optional[WorkLocation] = None

    class Config:
        from_attributes = True
