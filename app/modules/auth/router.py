from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.session import get_db, AsyncSessionLocal
from app.db.public_models import Tenant
from app.modules.core_hr.models import User
from app.modules.auth import schemas
from app.core import security
from app.core.config import settings

from app.core.dependencies import get_current_user, get_tenant_db_from_token
from app.modules.core_hr import schemas as core_schemas

router = APIRouter()

@router.get("/me", response_model=core_schemas.User, summary="Get currently logged-in user")
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db_from_token)
):
    """Returns the currently authenticated user's data."""
    return current_user


@router.post("/login", response_model=schemas.Token)
async def login(credentials: schemas.LoginRequest, db: AsyncSession = Depends(get_db)):
    # 1. Find the company (Tenant) in the public schema
    result = await db.execute(select(Tenant).where(Tenant.company_name == credentials.company_name))
    tenant = result.scalars().first()
    
    if not tenant:
        raise HTTPException(status_code=400, detail="Company not found")

    # 2. Open a NEW database session pointed specifically at this company's schema
    import app.db.session as sess_module
    cur_engine = sess_module.engine
    is_postgres = "postgresql" in str(cur_engine.url)
    opts = {"schema_translate_map": {None: tenant.schema_name}} if is_postgres else {}
    bind_engine = cur_engine.execution_options(**opts) if opts else cur_engine
    async with sess_module.AsyncSessionLocal(bind=bind_engine) as tenant_db:
        
        # 3. Look up the user inside this tenant's schema
        user_result = await tenant_db.execute(select(User).where(User.email == credentials.email))
        user = user_result.scalars().first()
        
        if not user or not security.verify_password(credentials.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # 4. Generate JWT Token containing both User ID, Schema Name, and role
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={
            "sub": str(user.id),
            "schema_name": tenant.schema_name,
            "is_superuser": user.is_superuser,
            "email": user.email,
        },
        expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "schema_name": tenant.schema_name,
        "user_id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_superuser": user.is_superuser,
    }
