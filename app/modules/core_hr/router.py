from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List

from app.core.dependencies import get_tenant_db_from_token, get_current_user
from app.modules.core_hr import models, schemas
from passlib.context import CryptContext

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

# --- Departments Routes ---
@router.post("/departments/", response_model=schemas.Department, status_code=status.HTTP_201_CREATED)
async def create_department(
    dept: schemas.DepartmentCreate, 
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(select(models.Department).where(models.Department.name == dept.name))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Department already exists")
    
    db_dept = models.Department(name=dept.name, description=dept.description)
    db.add(db_dept)
    await db.commit()
    await db.refresh(db_dept)
    return db_dept

@router.get("/departments/", response_model=List[schemas.Department])
async def read_departments(
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(select(models.Department).offset(skip).limit(limit))
    return result.scalars().all()

# --- Employees Routes ---
@router.post("/employees/", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
async def create_employee(
    user: schemas.UserCreate, 
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    # Only superusers or HR admins should create employees (placeholder check)
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized to create employees")

    result = await db.execute(select(models.User).where(models.User.email == user.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    db_user = models.User(
        email=user.email,
        hashed_password=get_password_hash(user.password),
        first_name=user.first_name,
        last_name=user.last_name,
        job_title=user.job_title,
        department_id=user.department_id,
        is_active=user.is_active,
        is_superuser=user.is_superuser
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    result = await db.execute(
        select(models.User)
        .options(selectinload(models.User.department))
        .where(models.User.id == db_user.id)
    )
    return result.scalars().first()

@router.get("/employees/", response_model=List[schemas.User])
async def read_employees(
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.User)
        .options(selectinload(models.User.department))
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()
