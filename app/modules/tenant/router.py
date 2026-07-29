import re
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text

from app.db.session import get_db, engine
from app.db.public_models import Tenant
from app.modules.tenant import schemas
from app.modules.core_hr.models import Base as CoreBase, User
from passlib.context import CryptContext

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def sanitize_schema_name(name: str) -> str:
    # Convert company name to a valid postgres schema name
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

    # 3. Create the PostgreSQL Schema physically
    await db.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
    await db.commit()

    # 4. Create all tables inside the new schema
    async with engine.begin() as conn:
        # We tell SQLAlchemy to translate the 'None' schema to our new schema
        conn = await conn.execution_options(schema_translate_map={None: schema_name})
        await conn.run_sync(CoreBase.metadata.create_all)
    
    # 5. Insert the Admin user into the new schema's users table
    # We create a new temporary session just for this tenant to insert the admin
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal(bind=engine.execution_options(schema_translate_map={None: schema_name})) as tenant_session:
        admin_user = User(
            email=data.admin_email,
            hashed_password=pwd_context.hash(data.admin_password),
            first_name=data.admin_first_name,
            last_name=data.admin_last_name,
            is_superuser=True, # This is the main admin
            is_active=True
        )
        tenant_session.add(admin_user)
        await tenant_session.commit()

    return new_tenant
