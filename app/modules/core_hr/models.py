from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    head_id = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    employees = relationship("User", back_populates="department", foreign_keys="User.department_id")


class Designation(Base):
    __tablename__ = "designations"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    department = relationship("Department")
    employees = relationship("User", back_populates="designation", foreign_keys="User.designation_id")


class WorkLocation(Base):
    __tablename__ = "work_locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    country = Column(String, default="India")
    pincode = Column(String(10), nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    employees = relationship("User", back_populates="work_location", foreign_keys="User.work_location_id")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    phone_number = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    # Employee specific data
    job_title = Column(String, nullable=True)
    employee_code = Column(String, unique=True, index=True, nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    designation_id = Column(Integer, ForeignKey("designations.id"), nullable=True)
    work_location_id = Column(Integer, ForeignKey("work_locations.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    department = relationship("Department", back_populates="employees", foreign_keys=[department_id])
    designation = relationship("Designation", back_populates="employees", foreign_keys=[designation_id])
    work_location = relationship("WorkLocation", back_populates="employees", foreign_keys=[work_location_id])
    profile = relationship(
        "EmployeeProfile",
        back_populates="user",
        foreign_keys="EmployeeProfile.user_id",
        uselist=False,
        cascade="all, delete-orphan"
    )
