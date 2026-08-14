import enum
from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey,
    DateTime, Date, Float, Text, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base


class LeaveStatusEnum(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"


class HalfDaySessionEnum(str, enum.Enum):
    first_half = "first_half"
    second_half = "second_half"


class LeaveType(Base):
    __tablename__ = "leave_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    code = Column(String(20), nullable=False, unique=True)  # e.g. "CL", "SL", "EL", "LOP"
    description = Column(String, nullable=True)
    default_annual_quota = Column(Float, default=12.0)
    is_carry_forward = Column(Boolean, default=False)
    max_carry_forward_days = Column(Float, default=0.0)
    is_encashable = Column(Boolean, default=False)
    is_paid = Column(Boolean, default=True)
    requires_attachment = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)


class LeaveBalance(Base):
    __tablename__ = "leave_balances"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    leave_type_id = Column(Integer, ForeignKey("leave_types.id"), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)

    opening_balance = Column(Float, default=0.0)
    accrued = Column(Float, default=0.0)
    availed = Column(Float, default=0.0)
    encashed = Column(Float, default=0.0)
    closing_balance = Column(Float, default=0.0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    employee = relationship("User", foreign_keys=[employee_id])
    leave_type = relationship("LeaveType", foreign_keys=[leave_type_id])


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    leave_type_id = Column(Integer, ForeignKey("leave_types.id"), nullable=False, index=True)

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_half_day = Column(Boolean, default=False)
    half_day_session = Column(SAEnum(HalfDaySessionEnum, name="halfdaysessionenum", create_type=False), nullable=True)
    days_count = Column(Float, nullable=False)

    reason = Column(Text, nullable=False)
    document_url = Column(String, nullable=True)

    status = Column(SAEnum(LeaveStatusEnum, name="leavestatusenum", create_type=False), default=LeaveStatusEnum.pending)
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    employee = relationship("User", foreign_keys=[employee_id])
    leave_type = relationship("LeaveType", foreign_keys=[leave_type_id])
    approver = relationship("User", foreign_keys=[approver_id])


class Holiday(Base):
    __tablename__ = "holidays"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    date = Column(Date, nullable=False, index=True)
    is_optional = Column(Boolean, default=False)  # Floating holiday
    description = Column(String, nullable=True)
    applicable_location_id = Column(Integer, ForeignKey("work_locations.id"), nullable=True)

    # Relationships
    location = relationship("WorkLocation", foreign_keys=[applicable_location_id])


class LeaveEncashment(Base):
    __tablename__ = "leave_encashments"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    leave_type_id = Column(Integer, ForeignKey("leave_types.id"), nullable=False, index=True)
    days_requested = Column(Float, nullable=False)
    amount = Column(Float, default=0.0)
    
    status = Column(SAEnum(LeaveStatusEnum, name="leaveencashstatusenum", create_type=False), default=LeaveStatusEnum.pending)
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    comments = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    employee = relationship("User", foreign_keys=[employee_id])
    leave_type = relationship("LeaveType", foreign_keys=[leave_type_id])
    approver = relationship("User", foreign_keys=[approver_id])
