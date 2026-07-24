from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# --- Department Schemas ---
class DepartmentBase(BaseModel):
    name: str
    description: Optional[str] = None

class DepartmentCreate(DepartmentBase):
    pass

class Department(DepartmentBase):
    id: int

    class Config:
        from_attributes = True

# --- User/Employee Schemas ---
class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    job_title: Optional[str] = None
    department_id: Optional[int] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    job_title: Optional[str] = None
    department_id: Optional[int] = None

class User(UserBase):
    id: int
    created_at: datetime
    department: Optional[Department] = None

    class Config:
        from_attributes = True
