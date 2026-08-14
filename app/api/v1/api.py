from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.tenant.router import router as tenant_router
from app.modules.core_hr.router import router as core_hr_router
from app.modules.employee_profile.router import router as employee_profile_router
from app.modules.attendance.router import router as attendance_router
from app.modules.leave.router import router as leave_router
from app.modules.payroll.router import router as payroll_router
from app.modules.expense.router import router as expense_router
from app.modules.pms.router import router as pms_router
from app.modules.recruitment.router import router as recruitment_router
from app.modules.helpdesk.router import router as helpdesk_router
from app.modules.asset.router import router as asset_router
from app.modules.analytics.router import router as analytics_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(tenant_router, prefix="/tenants", tags=["Tenants (SaaS Multi-tenancy)"])
api_router.include_router(core_hr_router, prefix="/core", tags=["Core HR & Organization"])
api_router.include_router(employee_profile_router, prefix="/profiles", tags=["Employee Profiles & Documents"])
api_router.include_router(attendance_router, prefix="/attendance", tags=["Time & Attendance"])
api_router.include_router(leave_router, prefix="/leave", tags=["Leave & Absence Management"])
api_router.include_router(payroll_router, prefix="/payroll", tags=["Payroll & Compensation"])
api_router.include_router(expense_router, prefix="/expenses", tags=["Expense & Reimbursements"])
api_router.include_router(pms_router, prefix="/pms", tags=["Performance & OKRs (PMS)"])
api_router.include_router(recruitment_router, prefix="/recruitment", tags=["Recruitment & ATS"])
api_router.include_router(helpdesk_router, prefix="/helpdesk", tags=["Helpdesk & Engagement"])
api_router.include_router(asset_router, prefix="/assets", tags=["Asset & Inventory Management"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics & Executive Reports"])
