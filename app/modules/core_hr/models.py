from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String)
    
    # Relationships
    employees = relationship("User", back_populates="department")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    # Employee specific data
    job_title = Column(String)
    department_id = Column(Integer, ForeignKey("departments.id"))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    department = relationship("Department", back_populates="employees")
    profile = relationship(
        "EmployeeProfile",
        back_populates="user",
        foreign_keys="EmployeeProfile.user_id",
        uselist=False,
        cascade="all, delete-orphan"
    )
