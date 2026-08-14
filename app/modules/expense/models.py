import enum
from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey,
    DateTime, Date, Float, Text, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base


class ExpenseStatusEnum(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"
    approved = "approved"
    rejected = "rejected"
    reimbursed = "reimbursed"


class AdvanceStatusEnum(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    settled = "settled"


class ExpenseCategory(Base):
    __tablename__ = "expense_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    code = Column(String(30), nullable=False, unique=True)  # TRAVEL, FOOD, LODGING, INTERNET, FUEL
    max_limit = Column(Float, default=10000.0)
    requires_receipt = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)


class ExpenseClaim(Base):
    __tablename__ = "expense_claims"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("expense_categories.id"), nullable=False, index=True)

    title = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(5), default="INR")
    expense_date = Column(Date, nullable=False)
    merchant = Column(String, nullable=True)
    receipt_url = Column(String, nullable=True)
    description = Column(Text, nullable=True)

    status = Column(SAEnum(ExpenseStatusEnum, name="expensestatusenum", create_type=False), default=ExpenseStatusEnum.submitted)
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    is_included_in_payroll = Column(Boolean, default=False)
    payroll_run_id = Column(Integer, ForeignKey("payroll_runs.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    employee = relationship("User", foreign_keys=[employee_id])
    category = relationship("ExpenseCategory", foreign_keys=[category_id])
    approver = relationship("User", foreign_keys=[approver_id])


class CashAdvance(Base):
    __tablename__ = "cash_advances"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    amount = Column(Float, nullable=False)
    purpose = Column(Text, nullable=False)
    required_date = Column(Date, nullable=False)

    status = Column(SAEnum(AdvanceStatusEnum, name="advancestatusenum", create_type=False), default=AdvanceStatusEnum.pending)
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    employee = relationship("User", foreign_keys=[employee_id])
    approver = relationship("User", foreign_keys=[approver_id])
