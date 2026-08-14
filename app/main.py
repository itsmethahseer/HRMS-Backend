from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

from contextlib import asynccontextmanager
from app.db.session import engine, Base
from app.db.public_models import Tenant
from app.modules.core_hr.models import User, Department, Designation, WorkLocation  # noqa: F401
import app.modules.employee_profile.models  # noqa: F401
import app.modules.attendance.models  # noqa: F401
import app.modules.leave.models  # noqa: F401
import app.modules.payroll.models  # noqa: F401
import app.modules.expense.models  # noqa: F401
import app.modules.pms.models  # noqa: F401
import app.modules.recruitment.models  # noqa: F401
import app.modules.helpdesk.models  # noqa: F401
import app.modules.asset.models  # noqa: F401

import asyncio
from sqlalchemy.exc import OperationalError, InterfaceError

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Wait for DB + create public schema tables (e.g. tenants)
    retries = 10
    while retries > 0:
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            break
        except (OperationalError, InterfaceError) as e:
            retries -= 1
            if retries == 0:
                raise e
            print(f"Database connection failed, retrying in 2 seconds... ({retries} retries left)")
            await asyncio.sleep(2)

    # 2. Auto-migrate ALL existing tenant schemas
    #    create_all uses IF NOT EXISTS — safe to run every startup.
    #    This ensures new tables (employee_profiles etc.) appear in old schemas.
    from app.db.session import AsyncSessionLocal
    from sqlalchemy.future import select
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Tenant))
            tenants = result.scalars().all()

        for tenant in tenants:
            try:
                async with engine.begin() as conn:
                    conn = await conn.execution_options(
                        schema_translate_map={None: tenant.schema_name}
                    )
                    await conn.run_sync(Base.metadata.create_all)
                print(f"✓ Migrated schema: {tenant.schema_name}")
            except Exception as e:
                print(f"⚠ Could not migrate schema {tenant.schema_name}: {e}")
    except Exception as e:
        print(f"⚠ Tenant auto-migration skipped: {e}")

    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Serve uploaded files (e.g. profile photos)
import os
from fastapi.staticfiles import StaticFiles

UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.abspath("uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to HRMS API"}

from app.api.v1.api import api_router

app.include_router(api_router, prefix=settings.API_V1_STR)
