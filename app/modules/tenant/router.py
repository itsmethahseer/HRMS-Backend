import re
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text

from app.db.session import get_db, engine
from app.db.public_models import Tenant
from app.modules.tenant import schemas
from app.modules.core_hr.models import Base as CoreBase, User, Department, Designation, WorkLocation
import app.modules.employee_profile.models  # noqa: F401
import app.modules.attendance.models  # noqa: F401
import app.modules.leave.models  # noqa: F401
import app.modules.payroll.models  # noqa: F401
import app.modules.expense.models  # noqa: F401
import app.modules.pms.models  # noqa: F401
import app.modules.recruitment.models  # noqa: F401
import app.modules.helpdesk.models  # noqa: F401
import app.modules.asset.models  # noqa: F401
import app.modules.notifications.models  # noqa: F401
from app.core.security import get_password_hash
from app.core.dependencies import get_token_payload

router = APIRouter()

def sanitize_schema_name(name: str) -> str:
    clean_name = re.sub(r'[^a-zA-Z0-9]', '_', name).lower()
    return f"tenant_{clean_name}"


@router.post("/register", response_model=schemas.TenantResponse, status_code=status.HTTP_201_CREATED)
async def register_company(data: schemas.CompanyRegister, db: AsyncSession = Depends(get_db)):
    # 1. Check if company exists in public.tenants
    schema_name = sanitize_schema_name(data.company_name)
    result = await db.execute(select(Tenant).where(Tenant.schema_name == schema_name))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Company already registered")

    # 2. Add to public.tenants
    new_tenant = Tenant(company_name=data.company_name, schema_name=schema_name)
    db.add(new_tenant)
    await db.commit()
    await db.refresh(new_tenant)

    # 3. Create the PostgreSQL Schema physically (if using PostgreSQL)
    import app.db.session as sess_module
    cur_engine = sess_module.engine
    is_postgres = "postgresql" in str(cur_engine.url)
    if is_postgres:
        await db.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
        await db.commit()

    # 4. Create all tables inside the new schema
    async with cur_engine.begin() as conn:
        if is_postgres:
            conn = await conn.execution_options(schema_translate_map={None: schema_name})
        await conn.run_sync(CoreBase.metadata.create_all)
    
    # 5. Insert the Admin user into the new schema's users table
    opts = {"schema_translate_map": {None: schema_name}} if is_postgres else {}
    bind_engine = cur_engine.execution_options(**opts) if opts else cur_engine
    async with sess_module.AsyncSessionLocal(bind=bind_engine) as tenant_session:
        admin_user = User(
            email=data.admin_email,
            hashed_password=get_password_hash(data.admin_password),
            first_name=data.admin_first_name,
            last_name=data.admin_last_name,
            is_superuser=True,
            is_active=True
        )
        tenant_session.add(admin_user)
        await tenant_session.commit()

    return new_tenant


@router.get("/me", response_model=schemas.TenantResponse, summary="Get My Company Profile")
async def get_my_tenant(
    payload: dict = Depends(get_token_payload),
    db: AsyncSession = Depends(get_db)
):
    """Returns the current tenant/company details."""
    schema_name = payload.get("schema_name")
    result = await db.execute(select(Tenant).where(Tenant.schema_name == schema_name))
    tenant = result.scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.patch("/me", response_model=schemas.TenantResponse, summary="Update My Company Name")
async def update_my_tenant(
    data: schemas.TenantUpdate,
    payload: dict = Depends(get_token_payload),
    db: AsyncSession = Depends(get_db)
):
    """Allows a superuser to update the company name."""
    schema_name = payload.get("schema_name")
    result = await db.execute(select(Tenant).where(Tenant.schema_name == schema_name))
    tenant = result.scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if data.company_name:
        # Check uniqueness
        existing = await db.execute(
            select(Tenant).where(Tenant.company_name == data.company_name, Tenant.id != tenant.id)
        )
        if existing.scalars().first():
            raise HTTPException(status_code=400, detail="Company name already taken")
        tenant.company_name = data.company_name

    if data.is_active is not None:
        tenant.is_active = data.is_active

    await db.commit()
    await db.refresh(tenant)
    return tenant

