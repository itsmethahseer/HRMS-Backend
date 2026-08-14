from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date, time
from app.modules.attendance.models import AttendanceStatusEnum, RequestStatusEnum


# --- Shift Schemas ---
class ShiftBase(BaseModel):
    name: str
    code: Optional[str] = None
    start_time: time
    end_time: time
    grace_period_mins: Optional[int] = 15
    late_mark_after_mins: Optional[int] = 30
    half_day_after_mins: Optional[int] = 240
    is_night_shift: Optional[bool] = False
    is_default: Optional[bool] = False
    is_active: Optional[bool] = True


class ShiftCreate(ShiftBase):
    pass


class ShiftUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    grace_period_mins: Optional[int] = None
    late_mark_after_mins: Optional[int] = None
    half_day_after_mins: Optional[int] = None
    is_night_shift: Optional[bool] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class ShiftOut(ShiftBase):
    id: int

    class Config:
        from_attributes = True


# --- Geofence Schemas ---
class GeofenceBase(BaseModel):
    name: str
    latitude: float
    longitude: float
    radius_meters: Optional[float] = 100.0
    is_active: Optional[bool] = True


class GeofenceCreate(GeofenceBase):
    pass


class GeofenceUpdate(BaseModel):
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_meters: Optional[float] = None
    is_active: Optional[bool] = None


class GeofenceOut(GeofenceBase):
    id: int

    class Config:
        from_attributes = True


# --- Punch-In / Punch-Out Actions ---
class PunchInRequest(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    note: Optional[str] = None


class PunchOutRequest(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    note: Optional[str] = None


# --- Attendance Log Schemas ---
class AttendanceLogBase(BaseModel):
    employee_id: int
    date: date
    punch_in: Optional[datetime] = None
    punch_out: Optional[datetime] = None
    punch_in_ip: Optional[str] = None
    punch_out_ip: Optional[str] = None
    punch_in_lat: Optional[float] = None
    punch_in_lng: Optional[float] = None
    punch_out_lat: Optional[float] = None
    punch_out_lng: Optional[float] = None
    punch_in_note: Optional[str] = None
    punch_out_note: Optional[str] = None
    total_hours: Optional[float] = 0.0
    status: Optional[AttendanceStatusEnum] = AttendanceStatusEnum.present
    is_regularized: Optional[bool] = False


class AttendanceLogCreate(AttendanceLogBase):
    pass


class AttendanceLogUpdate(BaseModel):
    punch_in: Optional[datetime] = None
    punch_out: Optional[datetime] = None
    punch_in_note: Optional[str] = None
    punch_out_note: Optional[str] = None
    total_hours: Optional[float] = None
    status: Optional[AttendanceStatusEnum] = None
    is_regularized: Optional[bool] = None


class AttendanceLogOut(AttendanceLogBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Attendance Regularization Schemas ---
class RegularizationCreate(BaseModel):
    attendance_log_id: Optional[int] = None
    date: date
    requested_punch_in: Optional[datetime] = None
    requested_punch_out: Optional[datetime] = None
    reason: str


class RegularizationReview(BaseModel):
    approver_comment: Optional[str] = None


class RegularizationOut(BaseModel):
    id: int
    attendance_log_id: Optional[int] = None
    employee_id: int
    date: date
    requested_punch_in: Optional[datetime] = None
    requested_punch_out: Optional[datetime] = None
    reason: str
    status: RequestStatusEnum
    approver_id: Optional[int] = None
    approver_comment: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Overtime Schemas ---
class OvertimeCreate(BaseModel):
    date: date
    overtime_hours: float
    reason: str


class OvertimeReview(BaseModel):
    approver_comment: Optional[str] = None


class OvertimeOut(BaseModel):
    id: int
    employee_id: int
    date: date
    overtime_hours: float
    reason: str
    status: RequestStatusEnum
    approver_id: Optional[int] = None
    approver_comment: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
