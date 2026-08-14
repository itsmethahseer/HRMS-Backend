from datetime import date
from typing import Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import func

from app.core.dependencies import get_tenant_db_from_token, get_current_user
from app.modules.core_hr.models import User, Department, Designation, WorkLocation
from app.modules.employee_profile.models import EmployeeProfile
from app.modules.attendance.models import AttendanceLog, AttendanceStatusEnum
from app.modules.leave.models import LeaveRequest, LeaveStatusEnum, LeaveBalance, LeaveType
from app.modules.payroll.models import PayrollRun, EmployeeSalary
from app.modules.recruitment.models import JobPosting, Candidate, JobStatusEnum
from app.modules.helpdesk.models import HelpdeskTicket, TicketStatusEnum
from app.modules.asset.models import Asset, AssetStatusEnum

router = APIRouter()


@router.get("/dashboard-summary", summary="Executive HR Dashboard Summary KPIs")
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    today = date.today()

    # Employees count
    emp_res = await db.execute(select(func.count(User.id)))
    total_employees = emp_res.scalar() or 0

    active_emp_res = await db.execute(select(func.count(User.id)).where(User.is_active == True))
    active_employees = active_emp_res.scalar() or 0

    # Departments
    dept_res = await db.execute(select(func.count(Department.id)))
    total_departments = dept_res.scalar() or 0

    # Today's attendance
    att_res = await db.execute(
        select(func.count(AttendanceLog.id)).where(
            AttendanceLog.date == today,
            AttendanceLog.punch_in != None
        )
    )
    present_today = att_res.scalar() or 0

    # Leaves today
    leaves_res = await db.execute(
        select(func.count(LeaveRequest.id)).where(
            LeaveRequest.start_date <= today,
            LeaveRequest.end_date >= today,
            LeaveRequest.status == LeaveStatusEnum.approved
        )
    )
    on_leave_today = leaves_res.scalar() or 0

    # Open Job Postings
    jobs_res = await db.execute(select(func.count(JobPosting.id)).where(JobPosting.status == JobStatusEnum.open))
    open_jobs = jobs_res.scalar() or 0

    # Pending Helpdesk Tickets
    tickets_res = await db.execute(
        select(func.count(HelpdeskTicket.id)).where(
            (HelpdeskTicket.status == TicketStatusEnum.open) | (HelpdeskTicket.status == TicketStatusEnum.in_progress)
        )
    )
    open_tickets = tickets_res.scalar() or 0

    # Assets assigned
    assets_res = await db.execute(select(func.count(Asset.id)).where(Asset.status == AssetStatusEnum.assigned))
    assigned_assets = assets_res.scalar() or 0

    return {
        "total_employees": total_employees,
        "active_employees": active_employees,
        "total_departments": total_departments,
        "present_today": present_today,
        "on_leave_today": on_leave_today,
        "open_job_openings": open_jobs,
        "open_helpdesk_tickets": open_tickets,
        "assigned_assets": assigned_assets
    }


@router.get("/headcount-trends", summary="Department & Gender Workforce Breakdown")
async def get_headcount_trends(
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    # Department breakdown
    depts_res = await db.execute(select(Department))
    depts = depts_res.scalars().all()

    department_data = []
    for d in depts:
        count_res = await db.execute(select(func.count(User.id)).where(User.department_id == d.id))
        count = count_res.scalar() or 0
        department_data.append({"department_id": d.id, "name": d.name, "count": count})

    # Gender breakdown from profiles
    profiles_res = await db.execute(select(EmployeeProfile.gender, func.count(EmployeeProfile.id)).group_by(EmployeeProfile.gender))
    gender_rows = profiles_res.all()
    gender_data = {str(row[0] or "Not Specified"): row[1] for row in gender_rows}

    return {
        "department_distribution": department_data,
        "gender_distribution": gender_data
    }


@router.get("/attendance-overview", summary="Attendance & Punctuality Overview")
async def get_attendance_overview(
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    today = date.today()

    today_logs = await db.execute(select(AttendanceLog).where(AttendanceLog.date == today))
    logs = today_logs.scalars().all()

    present_count = sum(1 for l in logs if l.status == AttendanceStatusEnum.present)
    half_day_count = sum(1 for l in logs if l.status == AttendanceStatusEnum.half_day)
    late_count = sum(1 for l in logs if l.status == AttendanceStatusEnum.late)

    total_hours = sum(l.total_hours for l in logs)
    avg_hours = round(total_hours / len(logs), 2) if logs else 0.0

    return {
        "date": today,
        "total_punches": len(logs),
        "present": present_count,
        "half_day": half_day_count,
        "late": late_count,
        "average_working_hours": avg_hours
    }


@router.get("/leave-utilization", summary="Leave Utilization by Type")
async def get_leave_utilization(
    year: int = date.today().year,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    lt_res = await db.execute(select(LeaveType))
    leave_types = lt_res.scalars().all()

    stats = []
    for lt in leave_types:
        bal_res = await db.execute(
            select(
                func.sum(LeaveBalance.accrued),
                func.sum(LeaveBalance.availed),
                func.sum(LeaveBalance.closing_balance)
            ).where(LeaveBalance.leave_type_id == lt.id, LeaveBalance.year == year)
        )
        row = bal_res.first()
        accrued = row[0] or 0.0
        availed = row[1] or 0.0
        closing = row[2] or 0.0

        stats.append({
            "leave_type_id": lt.id,
            "leave_type_name": lt.name,
            "leave_type_code": lt.code,
            "total_accrued": accrued,
            "total_availed": availed,
            "total_remaining": closing
        })

    return stats


@router.get("/payroll-cost-summary", summary="Payroll Expenditure Overview")
async def get_payroll_cost_summary(
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    # Sum up all active salaries
    sal_res = await db.execute(
        select(
            func.sum(EmployeeSalary.annual_ctc),
            func.sum(EmployeeSalary.monthly_gross),
            func.count(EmployeeSalary.id)
        ).where(EmployeeSalary.is_active == True)
    )
    row = sal_res.first()
    total_ctc = round(row[0] or 0.0, 2)
    monthly_gross = round(row[1] or 0.0, 2)
    active_salaries_count = row[2] or 0

    # Latest completed payroll run
    run_res = await db.execute(select(PayrollRun).order_by(PayrollRun.year.desc(), PayrollRun.month.desc()))
    last_run = run_res.scalars().first()

    return {
        "annual_company_ctc_liability": total_ctc,
        "monthly_gross_liability": monthly_gross,
        "employees_on_payroll": active_salaries_count,
        "last_payroll_run": {
            "id": last_run.id if last_run else None,
            "month": last_run.month if last_run else None,
            "year": last_run.year if last_run else None,
            "total_gross": last_run.total_gross if last_run else 0.0,
            "total_net_payout": last_run.total_net if last_run else 0.0,
            "total_statutory_deductions": last_run.total_deductions if last_run else 0.0,
            "status": last_run.status if last_run else None
        }
    }


@router.get("/recruitment-funnel", summary="Recruitment Stage Funnel Statistics")
async def get_recruitment_funnel(
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    cands_res = await db.execute(select(Candidate.status, func.count(Candidate.id)).group_by(Candidate.status))
    rows = cands_res.all()
    stage_counts = {str(row[0]): row[1] for row in rows}

    return {
        "candidate_pipeline_funnel": stage_counts
    }
