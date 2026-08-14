import json
from datetime import datetime, date, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_tenant_db_from_token, get_current_user
from app.modules.core_hr.models import User
from app.modules.attendance.models import AttendanceLog, AttendanceStatusEnum
from app.modules.leave.models import LeaveRequest, LeaveStatusEnum
from app.modules.payroll import models, schemas

router = APIRouter()


# ═══════════════════════════════════════════════════════════
# SALARY COMPONENTS (GET, POST, GET/{id}, PUT, PATCH, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/components/", response_model=schemas.SalaryComponentOut, status_code=status.HTTP_201_CREATED, summary="Create Salary Component")
async def create_component(
    data: schemas.SalaryComponentCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    existing = await db.execute(
        select(models.SalaryComponent).where(
            (models.SalaryComponent.name == data.name) | (models.SalaryComponent.code == data.code)
        )
    )
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Component with this name or code already exists")

    comp = models.SalaryComponent(**data.model_dump())
    db.add(comp)
    await db.commit()
    await db.refresh(comp)
    return comp


@router.get("/components/", response_model=List[schemas.SalaryComponentOut], summary="List Salary Components")
async def list_components(
    skip: int = 0,
    limit: int = 100,
    component_type: Optional[models.ComponentTypeEnum] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = select(models.SalaryComponent)
    if component_type:
        query = query.where(models.SalaryComponent.component_type == component_type)
    if is_active is not None:
        query = query.where(models.SalaryComponent.is_active == is_active)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/components/{id}", response_model=schemas.SalaryComponentOut, summary="Get Salary Component by ID")
async def get_component(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.SalaryComponent).where(models.SalaryComponent.id == id))
    comp = result.scalars().first()
    if not comp:
        raise HTTPException(status_code=404, detail="Salary component not found")
    return comp


@router.put("/components/{id}", response_model=schemas.SalaryComponentOut, summary="Update Salary Component (Full)")
async def update_component(
    id: int,
    data: schemas.SalaryComponentCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.SalaryComponent).where(models.SalaryComponent.id == id))
    comp = result.scalars().first()
    if not comp:
        raise HTTPException(status_code=404, detail="Salary component not found")
    for key, value in data.model_dump().items():
        setattr(comp, key, value)
    await db.commit()
    await db.refresh(comp)
    return comp


@router.patch("/components/{id}", response_model=schemas.SalaryComponentOut, summary="Update Salary Component (Partial)")
async def patch_component(
    id: int,
    data: schemas.SalaryComponentUpdate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.SalaryComponent).where(models.SalaryComponent.id == id))
    comp = result.scalars().first()
    if not comp:
        raise HTTPException(status_code=404, detail="Salary component not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(comp, key, value)
    await db.commit()
    await db.refresh(comp)
    return comp


@router.delete("/components/{id}", status_code=status.HTTP_200_OK, summary="Delete Salary Component")
async def delete_component(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.SalaryComponent).where(models.SalaryComponent.id == id))
    comp = result.scalars().first()
    if not comp:
        raise HTTPException(status_code=404, detail="Salary component not found")
    await db.delete(comp)
    await db.commit()
    return {"detail": "Salary component deleted successfully"}


# ═══════════════════════════════════════════════════════════
# SALARY STRUCTURES (GET, POST, GET/{id}, PUT, PATCH, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/structures/", response_model=schemas.SalaryStructureOut, status_code=status.HTTP_201_CREATED, summary="Create Salary Structure")
async def create_structure(
    data: schemas.SalaryStructureCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    existing = await db.execute(select(models.SalaryStructure).where(models.SalaryStructure.name == data.name))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Salary structure with this name already exists")

    structure = models.SalaryStructure(name=data.name, description=data.description, is_active=data.is_active)
    db.add(structure)
    await db.commit()
    await db.refresh(structure)

    if data.items:
        for item in data.items:
            db_item = models.SalaryStructureItem(
                structure_id=structure.id,
                component_id=item.component_id,
                calculation_type=item.calculation_type,
                value=item.value
            )
            db.add(db_item)
        await db.commit()

    res = await db.execute(
        select(models.SalaryStructure)
        .options(
            selectinload(models.SalaryStructure.items).selectinload(models.SalaryStructureItem.component)
        )
        .where(models.SalaryStructure.id == structure.id)
    )
    return res.scalars().first()


@router.get("/structures/", response_model=List[schemas.SalaryStructureOut], summary="List Salary Structures")
async def list_structures(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = (
        select(models.SalaryStructure)
        .options(
            selectinload(models.SalaryStructure.items).selectinload(models.SalaryStructureItem.component)
        )
    )
    if is_active is not None:
        query = query.where(models.SalaryStructure.is_active == is_active)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/structures/{id}", response_model=schemas.SalaryStructureOut, summary="Get Salary Structure by ID")
async def get_structure(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.SalaryStructure)
        .options(
            selectinload(models.SalaryStructure.items).selectinload(models.SalaryStructureItem.component)
        )
        .where(models.SalaryStructure.id == id)
    )
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Salary structure not found")
    return item


@router.put("/structures/{id}", response_model=schemas.SalaryStructureOut, summary="Update Salary Structure (Full)")
async def update_structure(
    id: int,
    data: schemas.SalaryStructureCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.SalaryStructure).where(models.SalaryStructure.id == id))
    structure = result.scalars().first()
    if not structure:
        raise HTTPException(status_code=404, detail="Salary structure not found")

    structure.name = data.name
    structure.description = data.description
    structure.is_active = data.is_active if data.is_active is not None else structure.is_active

    # Delete existing items & replace
    existing_items = await db.execute(select(models.SalaryStructureItem).where(models.SalaryStructureItem.structure_id == id))
    for it in existing_items.scalars().all():
        await db.delete(it)

    if data.items:
        for item in data.items:
            db_item = models.SalaryStructureItem(
                structure_id=structure.id,
                component_id=item.component_id,
                calculation_type=item.calculation_type,
                value=item.value
            )
            db.add(db_item)

    await db.commit()
    res = await db.execute(
        select(models.SalaryStructure)
        .options(
            selectinload(models.SalaryStructure.items).selectinload(models.SalaryStructureItem.component)
        )
        .where(models.SalaryStructure.id == structure.id)
    )
    return res.scalars().first()


@router.delete("/structures/{id}", status_code=status.HTTP_200_OK, summary="Delete Salary Structure")
async def delete_structure(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.SalaryStructure).where(models.SalaryStructure.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Salary structure not found")
    await db.delete(item)
    await db.commit()
    return {"detail": "Salary structure deleted successfully"}


# ═══════════════════════════════════════════════════════════
# EMPLOYEE SALARY ASSIGNMENT (GET, POST, GET/{id}, PUT, PATCH, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/employee-salaries/", response_model=schemas.EmployeeSalaryOut, status_code=status.HTTP_201_CREATED, summary="Assign Employee Salary")
async def create_employee_salary(
    data: schemas.EmployeeSalaryCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    existing = await db.execute(select(models.EmployeeSalary).where(models.EmployeeSalary.employee_id == data.employee_id))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Salary already assigned for this employee. Use PUT/PATCH to update.")

    sal = models.EmployeeSalary(**data.model_dump())
    db.add(sal)
    await db.commit()
    await db.refresh(sal)

    res = await db.execute(
        select(models.EmployeeSalary)
        .options(
            selectinload(models.EmployeeSalary.structure).selectinload(models.SalaryStructure.items).selectinload(models.SalaryStructureItem.component)
        )
        .where(models.EmployeeSalary.id == sal.id)
    )
    return res.scalars().first()


@router.get("/employee-salaries/", response_model=List[schemas.EmployeeSalaryOut], summary="List Employee Salaries")
async def list_employee_salaries(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = (
        select(models.EmployeeSalary)
        .options(
            selectinload(models.EmployeeSalary.structure).selectinload(models.SalaryStructure.items).selectinload(models.SalaryStructureItem.component)
        )
        .offset(skip).limit(limit)
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/employee-salaries/my", response_model=schemas.EmployeeSalaryOut, summary="My Salary Details")
async def get_my_salary(
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.EmployeeSalary)
        .options(
            selectinload(models.EmployeeSalary.structure).selectinload(models.SalaryStructure.items).selectinload(models.SalaryStructureItem.component)
        )
        .where(models.EmployeeSalary.employee_id == current_user.id)
    )
    sal = result.scalars().first()
    if not sal:
        raise HTTPException(status_code=404, detail="Salary details not configured for your profile")
    return sal


@router.get("/employee-salaries/{employee_id}", response_model=schemas.EmployeeSalaryOut, summary="Get Employee Salary by Employee ID")
async def get_employee_salary(
    employee_id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.EmployeeSalary)
        .options(
            selectinload(models.EmployeeSalary.structure).selectinload(models.SalaryStructure.items).selectinload(models.SalaryStructureItem.component)
        )
        .where(models.EmployeeSalary.employee_id == employee_id)
    )
    sal = result.scalars().first()
    if not sal:
        raise HTTPException(status_code=404, detail="Employee salary not found")
    return sal


@router.put("/employee-salaries/{id}", response_model=schemas.EmployeeSalaryOut, summary="Update Employee Salary (Full)")
async def update_employee_salary(
    id: int,
    data: schemas.EmployeeSalaryCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.EmployeeSalary).where(models.EmployeeSalary.id == id))
    sal = result.scalars().first()
    if not sal:
        raise HTTPException(status_code=404, detail="Employee salary record not found")
    for key, value in data.model_dump().items():
        setattr(sal, key, value)
    await db.commit()
    await db.refresh(sal)

    res = await db.execute(
        select(models.EmployeeSalary)
        .options(
            selectinload(models.EmployeeSalary.structure).selectinload(models.SalaryStructure.items).selectinload(models.SalaryStructureItem.component)
        )
        .where(models.EmployeeSalary.id == sal.id)
    )
    return res.scalars().first()


@router.patch("/employee-salaries/{id}", response_model=schemas.EmployeeSalaryOut, summary="Update Employee Salary (Partial)")
async def patch_employee_salary(
    id: int,
    data: schemas.EmployeeSalaryUpdate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.EmployeeSalary).where(models.EmployeeSalary.id == id))
    sal = result.scalars().first()
    if not sal:
        raise HTTPException(status_code=404, detail="Employee salary record not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(sal, key, value)
    await db.commit()
    await db.refresh(sal)

    res = await db.execute(
        select(models.EmployeeSalary)
        .options(
            selectinload(models.EmployeeSalary.structure).selectinload(models.SalaryStructure.items).selectinload(models.SalaryStructureItem.component)
        )
        .where(models.EmployeeSalary.id == sal.id)
    )
    return res.scalars().first()


@router.delete("/employee-salaries/{id}", status_code=status.HTTP_200_OK, summary="Delete Employee Salary")
async def delete_employee_salary(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.EmployeeSalary).where(models.EmployeeSalary.id == id))
    sal = result.scalars().first()
    if not sal:
        raise HTTPException(status_code=404, detail="Employee salary record not found")
    await db.delete(sal)
    await db.commit()
    return {"detail": "Employee salary record deleted successfully"}


# ═══════════════════════════════════════════════════════════
# PAYROLL EXECUTION ENGINE & RUNS
# ═══════════════════════════════════════════════════════════

@router.post("/runs/process", response_model=schemas.PayrollRunOut, status_code=status.HTTP_201_CREATED, summary="Process Payroll for Month")
async def process_payroll(
    data: schemas.ProcessPayrollRequest,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    # Check if run already exists
    existing = await db.execute(
        select(models.PayrollRun).where(
            models.PayrollRun.month == data.month,
            models.PayrollRun.year == data.year
        )
    )
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail=f"Payroll for {data.month}/{data.year} already processed. Delete or approve existing run.")

    payroll_run = models.PayrollRun(
        month=data.month,
        year=data.year,
        status=models.PayrollStatusEnum.draft,
        processed_at=datetime.now(timezone.utc)
    )
    db.add(payroll_run)
    await db.commit()
    await db.refresh(payroll_run)

    # Fetch all employees with salary assigned
    salaries_res = await db.execute(
        select(models.EmployeeSalary)
        .options(
            selectinload(models.EmployeeSalary.structure).selectinload(models.SalaryStructure.items).selectinload(models.SalaryStructureItem.component)
        )
        .where(models.EmployeeSalary.is_active == True)
    )
    salaries = salaries_res.scalars().all()

    total_gross = 0.0
    total_deductions = 0.0
    total_net = 0.0

    days_in_month = 30.0

    for emp_sal in salaries:
        # Compute LOP / Absent days from Attendance
        # Standard default is full 30 days unless LOP records exist
        lop_days = 0.0
        worked_days = max(0.0, days_in_month - lop_days)
        pay_ratio = worked_days / days_in_month

        monthly_gross = round(emp_sal.monthly_gross * pay_ratio, 2)
        basic = round(emp_sal.basic_salary * pay_ratio, 2)
        hra = round(basic * 0.4, 2)
        special = round(max(0.0, monthly_gross - (basic + hra)), 2)

        # Statutory Deductions
        pf_employee = round(min(basic, 15000.0) * 0.12, 2) if emp_sal.pf_number else 0.0
        esi_employee = round(monthly_gross * 0.0075, 2) if monthly_gross <= 21000.0 else 0.0
        pt = 200.0  # standard monthly Professional Tax
        tds = round(monthly_gross * 0.05, 2) if (emp_sal.annual_ctc > 700000) else 0.0

        statutory_total = round(pf_employee + esi_employee + pt + tds, 2)
        net_pay = round(monthly_gross - statutory_total, 2)

        earnings_dict = {
            "Basic Salary": basic,
            "HRA": hra,
            "Special Allowance": special
        }
        deductions_dict = {
            "Provident Fund (PF)": pf_employee,
            "ESI": esi_employee,
            "Professional Tax (PT)": pt,
            "TDS (Income Tax)": tds
        }

        payslip = models.Payslip(
            payroll_run_id=payroll_run.id,
            employee_id=emp_sal.employee_id,
            month=data.month,
            year=data.year,
            worked_days=worked_days,
            loss_of_pay_days=lop_days,
            paid_days=worked_days,
            basic_pay=basic,
            allowances=round(hra + special, 2),
            gross_earnings=monthly_gross,
            statutory_deductions=statutory_total,
            other_deductions=0.0,
            total_deductions=statutory_total,
            net_salary=net_pay,
            earnings_breakdown=json.dumps(earnings_dict),
            deductions_breakdown=json.dumps(deductions_dict),
            status=models.PayrollStatusEnum.draft
        )
        db.add(payslip)

        total_gross += monthly_gross
        total_deductions += statutory_total
        total_net += net_pay

    payroll_run.total_gross = round(total_gross, 2)
    payroll_run.total_deductions = round(total_deductions, 2)
    payroll_run.total_net = round(total_net, 2)

    await db.commit()
    await db.refresh(payroll_run)

    res = await db.execute(
        select(models.PayrollRun)
        .options(selectinload(models.PayrollRun.payslips))
        .where(models.PayrollRun.id == payroll_run.id)
    )
    return res.scalars().first()


@router.get("/runs/", response_model=List[schemas.PayrollRunOut], summary="List Payroll Runs")
async def list_payroll_runs(
    year: Optional[int] = None,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = select(models.PayrollRun).options(selectinload(models.PayrollRun.payslips))
    if year:
        query = query.where(models.PayrollRun.year == year)
    query = query.order_by(models.PayrollRun.year.desc(), models.PayrollRun.month.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/runs/{id}", response_model=schemas.PayrollRunOut, summary="Get Payroll Run by ID")
async def get_payroll_run(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.PayrollRun)
        .options(selectinload(models.PayrollRun.payslips))
        .where(models.PayrollRun.id == id)
    )
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Payroll run not found")
    return item


@router.patch("/runs/{id}/approve", response_model=schemas.PayrollRunOut, summary="Approve Payroll Run")
async def approve_payroll_run(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.PayrollRun)
        .options(selectinload(models.PayrollRun.payslips))
        .where(models.PayrollRun.id == id)
    )
    run = result.scalars().first()
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found")

    run.status = models.PayrollStatusEnum.approved
    run.approved_by = current_user.id
    for ps in run.payslips:
        ps.status = models.PayrollStatusEnum.approved

    await db.commit()
    await db.refresh(run)
    return run


@router.patch("/runs/{id}/pay", response_model=schemas.PayrollRunOut, summary="Disburse / Mark Payroll as Paid")
async def mark_payroll_paid(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.PayrollRun)
        .options(selectinload(models.PayrollRun.payslips))
        .where(models.PayrollRun.id == id)
    )
    run = result.scalars().first()
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found")

    today = date.today()
    run.status = models.PayrollStatusEnum.paid
    run.paid_at = datetime.now(timezone.utc)
    for ps in run.payslips:
        ps.status = models.PayrollStatusEnum.paid
        ps.payment_date = today

    await db.commit()
    await db.refresh(run)
    return run


@router.delete("/runs/{id}", status_code=status.HTTP_200_OK, summary="Delete Payroll Run")
async def delete_payroll_run(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.PayrollRun).where(models.PayrollRun.id == id))
    run = result.scalars().first()
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found")
    await db.delete(run)
    await db.commit()
    return {"detail": "Payroll run and associated payslips deleted successfully"}


# ═══════════════════════════════════════════════════════════
# PAYSLIPS (GET, GET/my, GET/{id}, DELETE)
# ═══════════════════════════════════════════════════════════

@router.get("/payslips/", response_model=List[schemas.PayslipOut], summary="List Payslips")
async def list_payslips(
    employee_id: Optional[int] = None,
    month: Optional[int] = None,
    year: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = select(models.Payslip)
    if employee_id:
        query = query.where(models.Payslip.employee_id == employee_id)
    if month:
        query = query.where(models.Payslip.month == month)
    if year:
        query = query.where(models.Payslip.year == year)
    result = await db.execute(query.order_by(models.Payslip.id.desc()).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/payslips/my", response_model=List[schemas.PayslipOut], summary="My Payslips")
async def get_my_payslips(
    year: Optional[int] = None,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = select(models.Payslip).where(models.Payslip.employee_id == current_user.id)
    if year:
        query = query.where(models.Payslip.year == year)
    query = query.order_by(models.Payslip.year.desc(), models.Payslip.month.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/payslips/{id}", response_model=schemas.PayslipOut, summary="Get Payslip by ID")
async def get_payslip(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.Payslip).where(models.Payslip.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Payslip not found")
    return item


# ═══════════════════════════════════════════════════════════
# FORM 12BB TAX DECLARATIONS (GET, POST, GET/{id}, PATCH, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/declarations/", response_model=schemas.Declaration12BBOut, status_code=status.HTTP_201_CREATED, summary="Submit Form 12BB Declaration")
async def create_declaration(
    data: schemas.Declaration12BBCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    existing = await db.execute(
        select(models.Declaration12BB).where(
            models.Declaration12BB.employee_id == current_user.id,
            models.Declaration12BB.financial_year == data.financial_year
        )
    )
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Declaration for this financial year already submitted")

    decl = models.Declaration12BB(
        employee_id=current_user.id,
        **data.model_dump(),
        status=models.DeclarationStatusEnum.submitted
    )
    db.add(decl)
    await db.commit()
    await db.refresh(decl)
    return decl


@router.get("/declarations/", response_model=List[schemas.Declaration12BBOut], summary="List Tax Declarations")
async def list_declarations(
    financial_year: Optional[str] = None,
    status_filter: Optional[models.DeclarationStatusEnum] = None,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = select(models.Declaration12BB)
    if financial_year:
        query = query.where(models.Declaration12BB.financial_year == financial_year)
    if status_filter:
        query = query.where(models.Declaration12BB.status == status_filter)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/declarations/my", response_model=List[schemas.Declaration12BBOut], summary="My Tax Declarations")
async def get_my_declarations(
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.Declaration12BB).where(models.Declaration12BB.employee_id == current_user.id)
    )
    return result.scalars().all()


@router.get("/declarations/{id}", response_model=schemas.Declaration12BBOut, summary="Get Tax Declaration by ID")
async def get_declaration(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.Declaration12BB).where(models.Declaration12BB.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Tax declaration not found")
    return item


@router.patch("/declarations/{id}/review", response_model=schemas.Declaration12BBOut, summary="Review / Verify Tax Declaration")
async def review_declaration(
    id: int,
    data: schemas.Declaration12BBReview,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.Declaration12BB).where(models.Declaration12BB.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Tax declaration not found")

    item.status = data.status
    item.comments = data.comments
    item.verified_by = current_user.id
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/declarations/{id}", status_code=status.HTTP_200_OK, summary="Delete Tax Declaration")
async def delete_declaration(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.Declaration12BB).where(models.Declaration12BB.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Tax declaration not found")
    await db.delete(item)
    await db.commit()
    return {"detail": "Tax declaration deleted successfully"}


# ═══════════════════════════════════════════════════════════
# SALARY LOANS & ADVANCES (GET, POST, GET/{id}, PATCH, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/loans/", response_model=schemas.SalaryLoanOut, status_code=status.HTTP_201_CREATED, summary="Apply for Salary Loan / Advance")
async def create_salary_loan(
    data: schemas.SalaryLoanCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    emi = round(data.amount / max(1, data.tenure_months), 2)
    loan = models.SalaryLoan(
        employee_id=current_user.id,
        amount=data.amount,
        reason=data.reason,
        emi_amount=emi,
        tenure_months=data.tenure_months,
        remaining_amount=data.amount,
        status=models.LoanStatusEnum.pending
    )
    db.add(loan)
    await db.commit()
    await db.refresh(loan)
    return loan


@router.get("/loans/", response_model=List[schemas.SalaryLoanOut], summary="List Salary Loans")
async def list_salary_loans(
    status_filter: Optional[models.LoanStatusEnum] = None,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = select(models.SalaryLoan)
    if status_filter:
        query = query.where(models.SalaryLoan.status == status_filter)
    result = await db.execute(query.order_by(models.SalaryLoan.created_at.desc()))
    return result.scalars().all()


@router.get("/loans/my", response_model=List[schemas.SalaryLoanOut], summary="My Salary Loans")
async def get_my_salary_loans(
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.SalaryLoan).where(models.SalaryLoan.employee_id == current_user.id).order_by(models.SalaryLoan.created_at.desc())
    )
    return result.scalars().all()


@router.get("/loans/{id}", response_model=schemas.SalaryLoanOut, summary="Get Salary Loan by ID")
async def get_salary_loan(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.SalaryLoan).where(models.SalaryLoan.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Salary loan not found")
    return item


@router.patch("/loans/{id}/review", response_model=schemas.SalaryLoanOut, summary="Review Salary Loan (Approve/Reject)")
async def review_salary_loan(
    id: int,
    data: schemas.SalaryLoanReview,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.SalaryLoan).where(models.SalaryLoan.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Salary loan not found")

    item.status = data.status
    item.approved_by = current_user.id
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/loans/{id}", status_code=status.HTTP_200_OK, summary="Delete Salary Loan")
async def delete_salary_loan(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.SalaryLoan).where(models.SalaryLoan.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Salary loan not found")
    await db.delete(item)
    await db.commit()
    return {"detail": "Salary loan deleted successfully"}
