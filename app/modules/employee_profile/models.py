import enum
from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey,
    DateTime, Date, Text, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base


class GenderEnum(str, enum.Enum):
    male = "male"
    female = "female"
    other = "other"
    prefer_not_to_say = "prefer_not_to_say"


class EmploymentTypeEnum(str, enum.Enum):
    full_time = "full_time"
    part_time = "part_time"
    contract = "contract"
    intern = "intern"
    freelance = "freelance"


class EmploymentStatusEnum(str, enum.Enum):
    active = "active"
    on_leave = "on_leave"
    terminated = "terminated"
    resigned = "resigned"
    probation = "probation"


class MaritalStatusEnum(str, enum.Enum):
    single = "single"
    married = "married"
    divorced = "divorced"
    widowed = "widowed"


class EmployeeProfile(Base):
    """Extended profile for each employee user. One-to-one with User."""
    __tablename__ = "employee_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)

    # --- Personal Info ---
    employee_id = Column(String, unique=True, index=True)  # e.g. EMP-001
    date_of_birth = Column(Date, nullable=True)
    gender = Column(SAEnum(GenderEnum, name="genderenum", create_type=False), nullable=True)
    marital_status = Column(SAEnum(MaritalStatusEnum, name="maritalstatusenum", create_type=False), nullable=True)
    nationality = Column(String, nullable=True)
    blood_group = Column(String(5), nullable=True)
    profile_photo_url = Column(String, nullable=True)

    # --- Contact Info ---
    phone_number = Column(String(20), nullable=True)
    alternate_phone = Column(String(20), nullable=True)
    personal_email = Column(String, nullable=True)

    # --- Address ---
    address_line1 = Column(String, nullable=True)
    address_line2 = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    country = Column(String, nullable=True)
    pincode = Column(String(10), nullable=True)

    # --- Employment Info ---
    employment_type = Column(SAEnum(EmploymentTypeEnum, name="employmenttypeenum", create_type=False), nullable=True)
    employment_status = Column(SAEnum(EmploymentStatusEnum, name="employmentstatusenum", create_type=False), default=EmploymentStatusEnum.active)
    date_of_joining = Column(Date, nullable=True)
    date_of_leaving = Column(Date, nullable=True)
    probation_end_date = Column(Date, nullable=True)
    notice_period_days = Column(Integer, default=30)

    # --- Org Info ---
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Reports to
    work_location = Column(String, nullable=True)  # Office / Remote / Hybrid
    shift = Column(String, nullable=True)  # Morning, Night, General

    # --- Additional ---
    bio = Column(Text, nullable=True)
    linkedin_url = Column(String, nullable=True)
    skills = Column(Text, nullable=True)  # Comma-separated or JSON string

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # --- Relationships ---
    user = relationship("User", foreign_keys=[user_id], back_populates="profile")
    manager = relationship("User", foreign_keys=[manager_id])
    emergency_contacts = relationship("EmergencyContact", back_populates="profile", cascade="all, delete-orphan")
    documents = relationship("EmployeeDocument", back_populates="profile", cascade="all, delete-orphan")
    education_records = relationship("EducationRecord", back_populates="profile", cascade="all, delete-orphan")
    experience_records = relationship("ExperienceRecord", back_populates="profile", cascade="all, delete-orphan")


class EmergencyContact(Base):
    """Emergency contacts for an employee."""
    __tablename__ = "emergency_contacts"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("employee_profiles.id"), nullable=False)

    name = Column(String, nullable=False)
    relation_type = Column(String, nullable=False)  # e.g. Spouse, Parent
    phone_number = Column(String(20), nullable=False)
    alternate_phone = Column(String(20), nullable=True)
    email = Column(String, nullable=True)
    address = Column(String, nullable=True)

    profile = relationship("EmployeeProfile", back_populates="emergency_contacts")


class EmployeeDocument(Base):
    """Uploaded documents for an employee (Aadhaar, PAN, Passport, etc.)"""
    __tablename__ = "employee_documents"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("employee_profiles.id"), nullable=False)

    document_type = Column(String, nullable=False)   # e.g. Aadhaar, PAN, Passport
    document_number = Column(String, nullable=True)
    file_url = Column(String, nullable=True)
    expiry_date = Column(Date, nullable=True)
    is_verified = Column(Boolean, default=False)

    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    profile = relationship("EmployeeProfile", back_populates="documents")


class EducationRecord(Base):
    """Educational qualifications for an employee."""
    __tablename__ = "education_records"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("employee_profiles.id"), nullable=False)

    degree = Column(String, nullable=False)          # B.Tech, MBA, etc.
    field_of_study = Column(String, nullable=True)
    institution = Column(String, nullable=False)
    university = Column(String, nullable=True)
    start_year = Column(Integer, nullable=True)
    end_year = Column(Integer, nullable=True)
    grade_or_percentage = Column(String, nullable=True)
    is_highest = Column(Boolean, default=False)

    profile = relationship("EmployeeProfile", back_populates="education_records")


class ExperienceRecord(Base):
    """Past work experience for an employee."""
    __tablename__ = "experience_records"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("employee_profiles.id"), nullable=False)

    company_name = Column(String, nullable=False)
    job_title = Column(String, nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)         # Null if current job
    is_current = Column(Boolean, default=False)
    description = Column(Text, nullable=True)
    location = Column(String, nullable=True)

    profile = relationship("EmployeeProfile", back_populates="experience_records")
