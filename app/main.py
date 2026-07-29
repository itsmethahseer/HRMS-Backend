from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

from contextlib import asynccontextmanager
from app.db.session import engine, Base
from app.db.public_models import Tenant
from app.modules.core_hr.models import User, Department

import asyncio
from sqlalchemy.exc import OperationalError, InterfaceError

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize public tables (like the Tenants directory) on startup
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
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

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
