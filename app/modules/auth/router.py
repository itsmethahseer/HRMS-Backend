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

router = APIRouter()

@router.post("/login", response_model=schemas.Token)
async def login(credentials: schemas.LoginRequest, db: AsyncSession = Depends(get_db)):
    # 1. Find the company (Tenant) in the public schema
    result = await db.execute(select(Tenant).where(Tenant.company_name == credentials.company_name))
    tenant = result.scalars().first()
    
    if not tenant:
        raise HTTPException(status_code=400, detail="Company not found")

    # 2. Open a NEW database session pointed specifically at this company's schema
    from app.db.session import engine
    async with AsyncSessionLocal(bind=engine.execution_options(schema_translate_map={None: tenant.schema_name})) as tenant_db:
        
        # 3. Look up the user inside this tenant's schema
        user_result = await tenant_db.execute(select(User).where(User.email == credentials.email))
        user = user_result.scalars().first()
        
        if not user or not security.verify_password(credentials.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # 4. Generate JWT Token containing both User ID and Schema Name
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": str(user.id), "schema_name": tenant.schema_name},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "schema_name": tenant.schema_name
    }
