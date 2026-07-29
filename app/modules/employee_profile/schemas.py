from pydantic import BaseModel, EmailStr, HttpUrl
from typing import Optional, List
from datetime import date, datetime
from app.modules.employee_profile.models import (
    GenderEnum, EmploymentTypeEnum, EmploymentStatusEnum, MaritalStatusEnum
)


# ─────────────────────────────────────────────
# Emergency Contact Schemas
# ─────────────────────────────────────────────

class EmergencyContactBase(BaseModel):
    name: str
    relation_type: str
    phone_number: str
    alternate_phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None


class EmergencyContactCreate(EmergencyContactBase):
    pass


class EmergencyContactUpdate(BaseModel):
    name: Optional[str] = None
    relation_type: Optional[str] = None
    phone_number: Optional[str] = None
    alternate_phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None


class EmergencyContactOut(EmergencyContactBase):
    id: int
    profile_id: int

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# Employee Document Schemas
# ─────────────────────────────────────────────

class EmployeeDocumentBase(BaseModel):
    document_type: str
    document_number: Optional[str] = None
    file_url: Optional[str] = None
    expiry_date: Optional[date] = None


class EmployeeDocumentCreate(EmployeeDocumentBase):
    pass


class EmployeeDocumentUpdate(BaseModel):
    document_type: Optional[str] = None
    document_number: Optional[str] = None
    file_url: Optional[str] = None
    expiry_date: Optional[date] = None
    is_verified: Optional[bool] = None


class EmployeeDocumentOut(EmployeeDocumentBase):
    id: int
    profile_id: int
    is_verified: bool
    uploaded_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# Education Record Schemas
# ─────────────────────────────────────────────

class EducationRecordBase(BaseModel):
    degree: str
    field_of_study: Optional[str] = None
    institution: str
    university: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    grade_or_percentage: Optional[str] = None
    is_highest: Optional[bool] = False


class EducationRecordCreate(EducationRecordBase):
    pass


class EducationRecordUpdate(BaseModel):
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    institution: Optional[str] = None
    university: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    grade_or_percentage: Optional[str] = None
    is_highest: Optional[bool] = None


class EducationRecordOut(EducationRecordBase):
    id: int
    profile_id: int

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# Experience Record Schemas
# ─────────────────────────────────────────────

class ExperienceRecordBase(BaseModel):
    company_name: str
    job_title: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: Optional[bool] = False
    description: Optional[str] = None
    location: Optional[str] = None


class ExperienceRecordCreate(ExperienceRecordBase):
    pass


class ExperienceRecordUpdate(BaseModel):
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: Optional[bool] = None
    description: Optional[str] = None
    location: Optional[str] = None


class ExperienceRecordOut(ExperienceRecordBase):
    id: int
    profile_id: int

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# Employee Profile Schemas
# ─────────────────────────────────────────────

class EmployeeProfileBase(BaseModel):
    employee_id: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[GenderEnum] = None
    marital_status: Optional[MaritalStatusEnum] = None
    nationality: Optional[str] = None
    blood_group: Optional[str] = None
    profile_photo_url: Optional[str] = None

    # Contact
    phone_number: Optional[str] = None
    alternate_phone: Optional[str] = None
    personal_email: Optional[str] = None

    # Address
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    pincode: Optional[str] = None

    # Employment
    employment_type: Optional[EmploymentTypeEnum] = None
    employment_status: Optional[EmploymentStatusEnum] = None
    date_of_joining: Optional[date] = None
    date_of_leaving: Optional[date] = None
    probation_end_date: Optional[date] = None
    notice_period_days: Optional[int] = 30

    # Org
    manager_id: Optional[int] = None
    work_location: Optional[str] = None
    shift: Optional[str] = None

    # Additional
    bio: Optional[str] = None
    linkedin_url: Optional[str] = None
    skills: Optional[str] = None


class EmployeeProfileCreate(EmployeeProfileBase):
    user_id: int


class EmployeeProfileUpdate(EmployeeProfileBase):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    job_title: Optional[str] = None
    department_id: Optional[int] = None


class ManagerSummary(BaseModel):
    id: int
    first_name: str
    last_name: str
    job_title: Optional[str] = None
    profile_photo_url: Optional[str] = None

    class Config:
        from_attributes = True


class EmployeeProfileOut(EmployeeProfileBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    emergency_contacts: List[EmergencyContactOut] = []
    documents: List[EmployeeDocumentOut] = []
    education_records: List[EducationRecordOut] = []
    experience_records: List[ExperienceRecordOut] = []

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# Full Employee Detail (User + Profile combined)
# ─────────────────────────────────────────────

class DepartmentSummary(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class EmployeeDetail(BaseModel):
    """Combined User + Profile view — used for employee directory listings"""
    id: int
    email: str
    first_name: str
    last_name: str
    job_title: Optional[str] = None
    is_active: bool
    is_superuser: bool
    department: Optional[DepartmentSummary] = None
    profile: Optional[EmployeeProfileOut] = None

    class Config:
        from_attributes = True


class EmployeeSummary(BaseModel):
    """Lightweight summary for org chart / dropdown"""
    id: int
    first_name: str
    last_name: str
    email: str
    job_title: Optional[str] = None
    profile_photo_url: Optional[str] = None
    department: Optional[DepartmentSummary] = None

    class Config:
        from_attributes = True


class OrgNode(BaseModel):
    """Flat node for org chart — frontend builds the tree from this list"""
    user_id: int
    first_name: str
    last_name: str
    email: str
    job_title: Optional[str] = None
    profile_photo_url: Optional[str] = None
    department: Optional[DepartmentSummary] = None
    manager_id: Optional[int] = None   # None = root (CEO / top-level)
    employment_status: Optional[str] = None
    is_active: bool = True

    class Config:
        from_attributes = True
