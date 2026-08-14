import enum
from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey,
    DateTime, Date, Time, Float, Text, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base


class AttendanceStatusEnum(str, enum.Enum):
    present = "present"
    absent = "absent"
    half_day = "half_day"
    late = "late"
    on_leave = "on_leave"
    holiday = "holiday"
    weekend = "weekend"


class RequestStatusEnum(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"


class Shift(Base):
    __tablename__ = "shifts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    code = Column(String, nullable=True)  # e.g. "GEN", "NIGHT"
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    grace_period_mins = Column(Integer, default=15)
    late_mark_after_mins = Column(Integer, default=30)
    half_day_after_mins = Column(Integer, default=240)
    is_night_shift = Column(Boolean, default=False)
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)


class GeofenceLocation(Base):
    __tablename__ = "geofence_locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    radius_meters = Column(Float, default=100.0)  # Allowed proximity radius
    is_active = Column(Boolean, default=True)


class AttendanceLog(Base):
    __tablename__ = "attendance_logs"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)

    punch_in = Column(DateTime(timezone=True), nullable=True)
    punch_out = Column(DateTime(timezone=True), nullable=True)

    punch_in_ip = Column(String(50), nullable=True)
    punch_out_ip = Column(String(50), nullable=True)

    punch_in_lat = Column(Float, nullable=True)
    punch_in_lng = Column(Float, nullable=True)
    punch_out_lat = Column(Float, nullable=True)
    punch_out_lng = Column(Float, nullable=True)

    punch_in_note = Column(String, nullable=True)
    punch_out_note = Column(String, nullable=True)

    total_hours = Column(Float, default=0.0)
    status = Column(SAEnum(AttendanceStatusEnum, name="attendancestatusenum", create_type=False), default=AttendanceStatusEnum.present)
    is_regularized = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    employee = relationship("User", foreign_keys=[employee_id])
    regularizations = relationship("AttendanceRegularization", back_populates="attendance_log", cascade="all, delete-orphan")


class AttendanceRegularization(Base):
    __tablename__ = "attendance_regularizations"

    id = Column(Integer, primary_key=True, index=True)
    attendance_log_id = Column(Integer, ForeignKey("attendance_logs.id"), nullable=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    date = Column(Date, nullable=False)
    requested_punch_in = Column(DateTime(timezone=True), nullable=True)
    requested_punch_out = Column(DateTime(timezone=True), nullable=True)
    reason = Column(Text, nullable=False)
    
    status = Column(SAEnum(RequestStatusEnum, name="requeststatusenum", create_type=False), default=RequestStatusEnum.pending)
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approver_comment = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    attendance_log = relationship("AttendanceLog", back_populates="regularizations")
    employee = relationship("User", foreign_keys=[employee_id])
    approver = relationship("User", foreign_keys=[approver_id])


class OvertimeRequest(Base):
    __tablename__ = "overtime_requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False)
    overtime_hours = Column(Float, nullable=False)
    reason = Column(Text, nullable=False)

    status = Column(SAEnum(RequestStatusEnum, name="overtimerequeststatusenum", create_type=False), default=RequestStatusEnum.pending)
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approver_comment = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    employee = relationship("User", foreign_keys=[employee_id])
    approver = relationship("User", foreign_keys=[approver_id])
