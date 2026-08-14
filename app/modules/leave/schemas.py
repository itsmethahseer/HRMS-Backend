from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from app.modules.leave.models import LeaveStatusEnum, HalfDaySessionEnum


# --- LeaveType Schemas ---
class LeaveTypeBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    default_annual_quota: Optional[float] = 12.0
    is_carry_forward: Optional[bool] = False
    max_carry_forward_days: Optional[float] = 0.0
    is_encashable: Optional[bool] = False
    is_paid: Optional[bool] = True
    requires_attachment: Optional[bool] = False
    is_active: Optional[bool] = True


class LeaveTypeCreate(LeaveTypeBase):
    pass


class LeaveTypeUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    default_annual_quota: Optional[float] = None
    is_carry_forward: Optional[bool] = None
    max_carry_forward_days: Optional[float] = None
    is_encashable: Optional[bool] = None
    is_paid: Optional[bool] = None
    requires_attachment: Optional[bool] = None
    is_active: Optional[bool] = None


class LeaveTypeOut(LeaveTypeBase):
    id: int

    class Config:
        from_attributes = True


# --- LeaveBalance Schemas ---
class LeaveBalanceBase(BaseModel):
    employee_id: int
    leave_type_id: int
    year: int
    opening_balance: Optional[float] = 0.0
    accrued: Optional[float] = 0.0
    availed: Optional[float] = 0.0
    encashed: Optional[float] = 0.0
    closing_balance: Optional[float] = 0.0


class LeaveBalanceCreate(LeaveBalanceBase):
    pass


class LeaveBalanceUpdate(BaseModel):
    opening_balance: Optional[float] = None
    accrued: Optional[float] = None
    availed: Optional[float] = None
    encashed: Optional[float] = None
    closing_balance: Optional[float] = None


class LeaveBalanceOut(LeaveBalanceBase):
    id: int
    leave_type: Optional[LeaveTypeOut] = None

    class Config:
        from_attributes = True


# --- LeaveRequest Schemas ---
class LeaveRequestCreate(BaseModel):
    leave_type_id: int
    start_date: date
    end_date: date
    is_half_day: Optional[bool] = False
    half_day_session: Optional[HalfDaySessionEnum] = None
    days_count: float
    reason: str
    document_url: Optional[str] = None


class LeaveRequestReview(BaseModel):
    rejection_reason: Optional[str] = None


class LeaveRequestOut(BaseModel):
    id: int
    employee_id: int
    leave_type_id: int
    start_date: date
    end_date: date
    is_half_day: bool
    half_day_session: Optional[HalfDaySessionEnum] = None
    days_count: float
    reason: str
    document_url: Optional[str] = None
    status: LeaveStatusEnum
    approver_id: Optional[int] = None
    rejection_reason: Optional[str] = None
    created_at: Optional[datetime] = None
    leave_type: Optional[LeaveTypeOut] = None

    class Config:
        from_attributes = True


# --- Holiday Schemas ---
class HolidayBase(BaseModel):
    name: str
    date: date
    is_optional: Optional[bool] = False
    description: Optional[str] = None
    applicable_location_id: Optional[int] = None


class HolidayCreate(HolidayBase):
    pass


class HolidayUpdate(BaseModel):
    name: Optional[str] = None
    date: Optional[date] = None
    is_optional: Optional[bool] = None
    description: Optional[str] = None
    applicable_location_id: Optional[int] = None


class HolidayOut(HolidayBase):
    id: int

    class Config:
        from_attributes = True


# --- LeaveEncashment Schemas ---
class LeaveEncashmentCreate(BaseModel):
    leave_type_id: int
    days_requested: float


class LeaveEncashmentReview(BaseModel):
    amount: Optional[float] = 0.0
    comments: Optional[str] = None


class LeaveEncashmentOut(BaseModel):
    id: int
    employee_id: int
    leave_type_id: int
    days_requested: float
    amount: float
    status: LeaveStatusEnum
    approver_id: Optional[int] = None
    comments: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
