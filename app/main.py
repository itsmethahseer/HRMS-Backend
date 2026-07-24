from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

from contextlib import asynccontextmanager
from app.db.session import engine, Base
from app.db.public_models import Tenant
from app.modules.core_hr.models import User, Department

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize public tables (like the Tenants directory) on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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
