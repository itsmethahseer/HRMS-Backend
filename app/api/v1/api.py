from fastapi import APIRouter
from app.modules.core_hr.router import router as core_hr_router
from app.modules.tenant.router import router as tenant_router
from app.modules.auth.router import router as auth_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(tenant_router, prefix="/tenants", tags=["Tenants (SaaS)"])
api_router.include_router(core_hr_router, prefix="/core", tags=["Core HR"])
# We will include attendance, payroll routers here in the future
