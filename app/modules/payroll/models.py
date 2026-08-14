import enum
from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey,
    DateTime, Date, Float, Text, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base


class ComponentTypeEnum(str, enum.Enum):
    earning = "earning"
    deduction = "deduction"


class CalculationTypeEnum(str, enum.Enum):
    fixed = "fixed"
    percentage_of_basic = "percentage_of_basic"
    percentage_of_gross = "percentage_of_gross"


class TaxRegimeEnum(str, enum.Enum):
    new = "new"
    old = "old"


class PayrollStatusEnum(str, enum.Enum):
    draft = "draft"
    processing = "processing"
    approved = "approved"
    paid = "paid"


class DeclarationStatusEnum(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"
    verified = "verified"
    rejected = "rejected"


class LoanStatusEnum(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    active = "active"
    closed = "closed"


class SalaryComponent(Base):
    __tablename__ = "salary_components"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    code = Column(String(30), nullable=False, unique=True)  # BASIC, HRA, SPECIAL, PF, ESI, TDS, PT
    component_type = Column(SAEnum(ComponentTypeEnum, name="componenttypeenum", create_type=False), nullable=False)
    calculation_type = Column(SAEnum(CalculationTypeEnum, name="calculationtypeenum", create_type=False), default=CalculationTypeEnum.fixed)
    default_value = Column(Float, default=0.0)
    is_taxable = Column(Boolean, default=True)
    is_statutory = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)


class SalaryStructure(Base):
    __tablename__ = "salary_structures"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    items = relationship("SalaryStructureItem", back_populates="structure", cascade="all, delete-orphan")


class SalaryStructureItem(Base):
    __tablename__ = "salary_structure_items"

    id = Column(Integer, primary_key=True, index=True)
    structure_id = Column(Integer, ForeignKey("salary_structures.id"), nullable=False)
    component_id = Column(Integer, ForeignKey("salary_components.id"), nullable=False)
    calculation_type = Column(SAEnum(CalculationTypeEnum, name="calcitemtypeenum", create_type=False), default=CalculationTypeEnum.fixed)
    value = Column(Float, default=0.0)

    structure = relationship("SalaryStructure", back_populates="items")
    component = relationship("SalaryComponent")


class EmployeeSalary(Base):
    __tablename__ = "employee_salaries"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    structure_id = Column(Integer, ForeignKey("salary_structures.id"), nullable=True)

    annual_ctc = Column(Float, nullable=False)
    monthly_gross = Column(Float, nullable=False)
    basic_salary = Column(Float, nullable=False)
    effective_from = Column(Date, nullable=False)

    payment_mode = Column(String(30), default="bank_transfer")  # bank_transfer, cheque, cash
    bank_name = Column(String, nullable=True)
    account_number = Column(String(50), nullable=True)
    ifsc_code = Column(String(20), nullable=True)
    pan_number = Column(String(20), nullable=True)
    uan_number = Column(String(30), nullable=True)
    pf_number = Column(String(30), nullable=True)
    tax_regime = Column(SAEnum(TaxRegimeEnum, name="taxregimeenum", create_type=False), default=TaxRegimeEnum.new)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    employee = relationship("User", foreign_keys=[employee_id])
    structure = relationship("SalaryStructure", foreign_keys=[structure_id])


class PayrollRun(Base):
    __tablename__ = "payroll_runs"

    id = Column(Integer, primary_key=True, index=True)
    month = Column(Integer, nullable=False)  # 1 - 12
    year = Column(Integer, nullable=False)   # e.g. 2026
    status = Column(SAEnum(PayrollStatusEnum, name="payrollstatusenum", create_type=False), default=PayrollStatusEnum.draft)

    total_gross = Column(Float, default=0.0)
    total_deductions = Column(Float, default=0.0)
    total_net = Column(Float, default=0.0)

    processed_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)

    payslips = relationship("Payslip", back_populates="payroll_run", cascade="all, delete-orphan")


class Payslip(Base):
    __tablename__ = "payslips"

    id = Column(Integer, primary_key=True, index=True)
    payroll_run_id = Column(Integer, ForeignKey("payroll_runs.id"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)

    worked_days = Column(Float, default=30.0)
    loss_of_pay_days = Column(Float, default=0.0)
    paid_days = Column(Float, default=30.0)

    basic_pay = Column(Float, default=0.0)
    allowances = Column(Float, default=0.0)
    gross_earnings = Column(Float, default=0.0)

    statutory_deductions = Column(Float, default=0.0)
    other_deductions = Column(Float, default=0.0)
    total_deductions = Column(Float, default=0.0)

    net_salary = Column(Float, default=0.0)

    earnings_breakdown = Column(Text, nullable=True)   # JSON string of components
    deductions_breakdown = Column(Text, nullable=True) # JSON string of components

    status = Column(SAEnum(PayrollStatusEnum, name="payslipstatusenum", create_type=False), default=PayrollStatusEnum.draft)
    payment_date = Column(Date, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    payroll_run = relationship("PayrollRun", back_populates="payslips")
    employee = relationship("User", foreign_keys=[employee_id])


class Declaration12BB(Base):
    __tablename__ = "declarations_12bb"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    financial_year = Column(String(10), nullable=False)  # e.g. "2026-2027"

    section_80c = Column(Float, default=0.0)        # PPF, ELSS, Life Insurance (Up to 1.5L)
    section_80d = Column(Float, default=0.0)        # Health Insurance
    section_24_home_loan = Column(Float, default=0.0)# Home loan interest
    hra_rent_paid = Column(Float, default=0.0)      # Annual rent paid
    other_exemptions = Column(Float, default=0.0)
    proofs_url = Column(String, nullable=True)

    status = Column(SAEnum(DeclarationStatusEnum, name="declstatusenum", create_type=False), default=DeclarationStatusEnum.draft)
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    comments = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    employee = relationship("User", foreign_keys=[employee_id])


class SalaryLoan(Base):
    __tablename__ = "salary_loans"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    amount = Column(Float, nullable=False)
    reason = Column(Text, nullable=False)
    emi_amount = Column(Float, nullable=False)
    tenure_months = Column(Integer, nullable=False)
    remaining_amount = Column(Float, nullable=False)

    status = Column(SAEnum(LoanStatusEnum, name="loanstatusenum", create_type=False), default=LoanStatusEnum.pending)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    employee = relationship("User", foreign_keys=[employee_id])
