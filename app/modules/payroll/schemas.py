from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from app.modules.payroll.models import (
    ComponentTypeEnum, CalculationTypeEnum, TaxRegimeEnum,
    PayrollStatusEnum, DeclarationStatusEnum, LoanStatusEnum
)


# --- SalaryComponent Schemas ---
class SalaryComponentBase(BaseModel):
    name: str
    code: str
    component_type: ComponentTypeEnum
    calculation_type: Optional[CalculationTypeEnum] = CalculationTypeEnum.fixed
    default_value: Optional[float] = 0.0
    is_taxable: Optional[bool] = True
    is_statutory: Optional[bool] = False
    is_active: Optional[bool] = True


class SalaryComponentCreate(SalaryComponentBase):
    pass


class SalaryComponentUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    component_type: Optional[ComponentTypeEnum] = None
    calculation_type: Optional[CalculationTypeEnum] = None
    default_value: Optional[float] = None
    is_taxable: Optional[bool] = None
    is_statutory: Optional[bool] = None
    is_active: Optional[bool] = None


class SalaryComponentOut(SalaryComponentBase):
    id: int

    class Config:
        from_attributes = True


# --- SalaryStructure Schemas ---
class StructureItemInput(BaseModel):
    component_id: int
    calculation_type: Optional[CalculationTypeEnum] = CalculationTypeEnum.fixed
    value: float


class StructureItemOut(BaseModel):
    id: int
    component_id: int
    calculation_type: CalculationTypeEnum
    value: float
    component: Optional[SalaryComponentOut] = None

    class Config:
        from_attributes = True


class SalaryStructureBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: Optional[bool] = True


class SalaryStructureCreate(SalaryStructureBase):
    items: Optional[List[StructureItemInput]] = []


class SalaryStructureUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    items: Optional[List[StructureItemInput]] = None


class SalaryStructureOut(SalaryStructureBase):
    id: int
    items: List[StructureItemOut] = []

    class Config:
        from_attributes = True


# --- EmployeeSalary Schemas ---
class EmployeeSalaryBase(BaseModel):
    employee_id: int
    structure_id: Optional[int] = None
    annual_ctc: float
    monthly_gross: float
    basic_salary: float
    effective_from: date
    payment_mode: Optional[str] = "bank_transfer"
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    pan_number: Optional[str] = None
    uan_number: Optional[str] = None
    pf_number: Optional[str] = None
    tax_regime: Optional[TaxRegimeEnum] = TaxRegimeEnum.new
    is_active: Optional[bool] = True


class EmployeeSalaryCreate(EmployeeSalaryBase):
    pass


class EmployeeSalaryUpdate(BaseModel):
    structure_id: Optional[int] = None
    annual_ctc: Optional[float] = None
    monthly_gross: Optional[float] = None
    basic_salary: Optional[float] = None
    effective_from: Optional[date] = None
    payment_mode: Optional[str] = None
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    pan_number: Optional[str] = None
    uan_number: Optional[str] = None
    pf_number: Optional[str] = None
    tax_regime: Optional[TaxRegimeEnum] = None
    is_active: Optional[bool] = None


class EmployeeSalaryOut(EmployeeSalaryBase):
    id: int
    structure: Optional[SalaryStructureOut] = None

    class Config:
        from_attributes = True


# --- Payroll Run & Payslip Schemas ---
class ProcessPayrollRequest(BaseModel):
    month: int
    year: int


class PayslipOut(BaseModel):
    id: int
    payroll_run_id: int
    employee_id: int
    month: int
    year: int
    worked_days: float
    loss_of_pay_days: float
    paid_days: float
    basic_pay: float
    allowances: float
    gross_earnings: float
    statutory_deductions: float
    other_deductions: float
    total_deductions: float
    net_salary: float
    earnings_breakdown: Optional[str] = None
    deductions_breakdown: Optional[str] = None
    status: PayrollStatusEnum
    payment_date: Optional[date] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PayrollRunOut(BaseModel):
    id: int
    month: int
    year: int
    status: PayrollStatusEnum
    total_gross: float
    total_deductions: float
    total_net: float
    processed_at: Optional[datetime] = None
    approved_by: Optional[int] = None
    paid_at: Optional[datetime] = None
    payslips: List[PayslipOut] = []

    class Config:
        from_attributes = True


# --- Form 12BB Declaration Schemas ---
class Declaration12BBCreate(BaseModel):
    financial_year: str
    section_80c: Optional[float] = 0.0
    section_80d: Optional[float] = 0.0
    section_24_home_loan: Optional[float] = 0.0
    hra_rent_paid: Optional[float] = 0.0
    other_exemptions: Optional[float] = 0.0
    proofs_url: Optional[str] = None


class Declaration12BBUpdate(BaseModel):
    section_80c: Optional[float] = None
    section_80d: Optional[float] = None
    section_24_home_loan: Optional[float] = None
    hra_rent_paid: Optional[float] = None
    other_exemptions: Optional[float] = None
    proofs_url: Optional[str] = None


class Declaration12BBReview(BaseModel):
    status: DeclarationStatusEnum
    comments: Optional[str] = None


class Declaration12BBOut(BaseModel):
    id: int
    employee_id: int
    financial_year: str
    section_80c: float
    section_80d: float
    section_24_home_loan: float
    hra_rent_paid: float
    other_exemptions: float
    proofs_url: Optional[str] = None
    status: DeclarationStatusEnum
    verified_by: Optional[int] = None
    comments: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Salary Loan Schemas ---
class SalaryLoanCreate(BaseModel):
    amount: float
    reason: str
    tenure_months: int


class SalaryLoanReview(BaseModel):
    status: LoanStatusEnum


class SalaryLoanOut(BaseModel):
    id: int
    employee_id: int
    amount: float
    reason: str
    emi_amount: float
    tenure_months: int
    remaining_amount: float
    status: LoanStatusEnum
    approved_by: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
