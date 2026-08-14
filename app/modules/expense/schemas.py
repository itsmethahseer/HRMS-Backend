from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from app.modules.expense.models import ExpenseStatusEnum, AdvanceStatusEnum


# --- Expense Category Schemas ---
class ExpenseCategoryBase(BaseModel):
    name: str
    code: str
    max_limit: Optional[float] = 10000.0
    requires_receipt: Optional[bool] = True
    is_active: Optional[bool] = True


class ExpenseCategoryCreate(ExpenseCategoryBase):
    pass


class ExpenseCategoryUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    max_limit: Optional[float] = None
    requires_receipt: Optional[bool] = None
    is_active: Optional[bool] = None


class ExpenseCategoryOut(ExpenseCategoryBase):
    id: int

    class Config:
        from_attributes = True


# --- Expense Claim Schemas ---
class ExpenseClaimBase(BaseModel):
    category_id: int
    title: str
    amount: float
    currency: Optional[str] = "INR"
    expense_date: date
    merchant: Optional[str] = None
    receipt_url: Optional[str] = None
    description: Optional[str] = None


class ExpenseClaimCreate(ExpenseClaimBase):
    pass


class ExpenseClaimUpdate(BaseModel):
    category_id: Optional[int] = None
    title: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    expense_date: Optional[date] = None
    merchant: Optional[str] = None
    receipt_url: Optional[str] = None
    description: Optional[str] = None


class ExpenseClaimReview(BaseModel):
    rejection_reason: Optional[str] = None


class ExpenseClaimOut(ExpenseClaimBase):
    id: int
    employee_id: int
    status: ExpenseStatusEnum
    approver_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    is_included_in_payroll: bool
    payroll_run_id: Optional[int] = None
    created_at: Optional[datetime] = None
    category: Optional[ExpenseCategoryOut] = None

    class Config:
        from_attributes = True


# --- Cash Advance Schemas ---
class CashAdvanceBase(BaseModel):
    amount: float
    purpose: str
    required_date: date


class CashAdvanceCreate(CashAdvanceBase):
    pass


class CashAdvanceReview(BaseModel):
    status: AdvanceStatusEnum
    notes: Optional[str] = None


class CashAdvanceOut(CashAdvanceBase):
    id: int
    employee_id: int
    status: AdvanceStatusEnum
    approver_id: Optional[int] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
