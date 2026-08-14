from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List, Optional

from app.core.dependencies import get_tenant_db_from_token, get_current_user
from app.modules.core_hr import models, schemas
from app.core.security import get_password_hash

router = APIRouter()


# ═══════════════════════════════════════════════════════════
# DEPARTMENTS (GET, POST, GET/{id}, PUT, PATCH, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/departments/", response_model=schemas.Department, status_code=status.HTTP_201_CREATED, summary="Create Department")
async def create_department(
    dept: schemas.DepartmentCreate, 
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(select(models.Department).where(models.Department.name == dept.name))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Department with this name already exists")
    
    db_dept = models.Department(**dept.model_dump())
    db.add(db_dept)
    await db.commit()
    await db.refresh(db_dept)
    return db_dept


@router.get("/departments/", response_model=List[schemas.Department], summary="List Departments")
async def read_departments(
    skip: int = 0, 
    limit: int = 100, 
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    query = select(models.Department)
    if is_active is not None:
        query = query.where(models.Department.is_active == is_active)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/departments/{dept_id}", response_model=schemas.Department, summary="Get Department by ID")
async def get_department(
    dept_id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(select(models.Department).where(models.Department.id == dept_id))
    dept = result.scalars().first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    return dept


@router.put("/departments/{dept_id}", response_model=schemas.Department, summary="Update Department (Full)")
async def update_department(
    dept_id: int,
    data: schemas.DepartmentCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(select(models.Department).where(models.Department.id == dept_id))
    dept = result.scalars().first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    
    for key, value in data.model_dump().items():
        setattr(dept, key, value)
    
    await db.commit()
    await db.refresh(dept)
    return dept


@router.patch("/departments/{dept_id}", response_model=schemas.Department, summary="Update Department (Partial)")
async def patch_department(
    dept_id: int,
    data: schemas.DepartmentUpdate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(select(models.Department).where(models.Department.id == dept_id))
    dept = result.scalars().first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(dept, key, value)
    
    await db.commit()
    await db.refresh(dept)
    return dept


@router.delete("/departments/{dept_id}", status_code=status.HTTP_200_OK, summary="Delete Department")
async def delete_department(
    dept_id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(select(models.Department).where(models.Department.id == dept_id))
    dept = result.scalars().first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    
    await db.delete(dept)
    await db.commit()
    return {"detail": "Department deleted successfully"}


# ═══════════════════════════════════════════════════════════
# DESIGNATIONS (GET, POST, GET/{id}, PUT, PATCH, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/designations/", response_model=schemas.Designation, status_code=status.HTTP_201_CREATED, summary="Create Designation")
async def create_designation(
    data: schemas.DesignationCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(select(models.Designation).where(models.Designation.title == data.title))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Designation already exists")
    
    designation = models.Designation(**data.model_dump())
    db.add(designation)
    await db.commit()
    await db.refresh(designation)
    return designation


@router.get("/designations/", response_model=List[schemas.Designation], summary="List Designations")
async def read_designations(
    skip: int = 0,
    limit: int = 100,
    department_id: Optional[int] = None,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    query = select(models.Designation)
    if department_id:
        query = query.where(models.Designation.department_id == department_id)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/designations/{id}", response_model=schemas.Designation, summary="Get Designation by ID")
async def get_designation(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(select(models.Designation).where(models.Designation.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Designation not found")
    return item


@router.put("/designations/{id}", response_model=schemas.Designation, summary="Update Designation (Full)")
async def update_designation(
    id: int,
    data: schemas.DesignationCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(select(models.Designation).where(models.Designation.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Designation not found")
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/designations/{id}", response_model=schemas.Designation, summary="Update Designation (Partial)")
async def patch_designation(
    id: int,
    data: schemas.DesignationUpdate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(select(models.Designation).where(models.Designation.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Designation not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/designations/{id}", status_code=status.HTTP_200_OK, summary="Delete Designation")
async def delete_designation(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(select(models.Designation).where(models.Designation.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Designation not found")
    await db.delete(item)
    await db.commit()
    return {"detail": "Designation deleted successfully"}


# ═══════════════════════════════════════════════════════════
# WORK LOCATIONS (GET, POST, GET/{id}, PUT, PATCH, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/locations/", response_model=schemas.WorkLocation, status_code=status.HTTP_201_CREATED, summary="Create Work Location")
async def create_location(
    data: schemas.WorkLocationCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(select(models.WorkLocation).where(models.WorkLocation.name == data.name))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Work location already exists")
    location = models.WorkLocation(**data.model_dump())
    db.add(location)
    await db.commit()
    await db.refresh(location)
    return location


@router.get("/locations/", response_model=List[schemas.WorkLocation], summary="List Work Locations")
async def read_locations(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    query = select(models.WorkLocation)
    if is_active is not None:
        query = query.where(models.WorkLocation.is_active == is_active)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/locations/{id}", response_model=schemas.WorkLocation, summary="Get Work Location by ID")
async def get_location(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(select(models.WorkLocation).where(models.WorkLocation.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Work location not found")
    return item


@router.put("/locations/{id}", response_model=schemas.WorkLocation, summary="Update Work Location (Full)")
async def update_location(
    id: int,
    data: schemas.WorkLocationCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(select(models.WorkLocation).where(models.WorkLocation.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Work location not found")
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/locations/{id}", response_model=schemas.WorkLocation, summary="Update Work Location (Partial)")
async def patch_location(
    id: int,
    data: schemas.WorkLocationUpdate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(select(models.WorkLocation).where(models.WorkLocation.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Work location not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/locations/{id}", status_code=status.HTTP_200_OK, summary="Delete Work Location")
async def delete_location(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(select(models.WorkLocation).where(models.WorkLocation.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Work location not found")
    await db.delete(item)
    await db.commit()
    return {"detail": "Work location deleted successfully"}


# ═══════════════════════════════════════════════════════════
# EMPLOYEES / USERS (GET, POST, GET/{id}, PUT, PATCH, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/employees/", response_model=schemas.User, status_code=status.HTTP_201_CREATED, summary="Create Employee")
async def create_employee(
    user: schemas.UserCreate, 
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(select(models.User).where(models.User.email == user.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    db_user = models.User(
        email=user.email,
        hashed_password=get_password_hash(user.password),
        first_name=user.first_name,
        last_name=user.last_name,
        phone_number=user.phone_number,
        job_title=user.job_title,
        employee_code=user.employee_code,
        department_id=user.department_id,
        designation_id=user.designation_id,
        work_location_id=user.work_location_id,
        is_active=user.is_active if user.is_active is not None else True,
        is_superuser=user.is_superuser if user.is_superuser is not None else False
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    result = await db.execute(
        select(models.User)
        .options(
            selectinload(models.User.department),
            selectinload(models.User.designation),
            selectinload(models.User.work_location)
        )
        .where(models.User.id == db_user.id)
    )
    return result.scalars().first()


@router.get("/employees/", response_model=List[schemas.User], summary="List Employees")
async def read_employees(
    skip: int = 0, 
    limit: int = 100, 
    department_id: Optional[int] = None,
    designation_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    query = (
        select(models.User)
        .options(
            selectinload(models.User.department),
            selectinload(models.User.designation),
            selectinload(models.User.work_location)
        )
    )
    if department_id:
        query = query.where(models.User.department_id == department_id)
    if designation_id:
        query = query.where(models.User.designation_id == designation_id)
    if is_active is not None:
        query = query.where(models.User.is_active == is_active)
    if search:
        query = query.where(
            (models.User.first_name.ilike(f"%{search}%")) |
            (models.User.last_name.ilike(f"%{search}%")) |
            (models.User.email.ilike(f"%{search}%")) |
            (models.User.employee_code.ilike(f"%{search}%"))
        )
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/employees/{user_id}", response_model=schemas.User, summary="Get Employee by ID")
async def get_employee(
    user_id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.User)
        .options(
            selectinload(models.User.department),
            selectinload(models.User.designation),
            selectinload(models.User.work_location)
        )
        .where(models.User.id == user_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Employee not found")
    return user


@router.put("/employees/{user_id}", response_model=schemas.User, summary="Update Employee (Full)")
async def update_employee(
    user_id: int,
    data: schemas.UserCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    user.email = data.email
    user.first_name = data.first_name
    user.last_name = data.last_name
    user.phone_number = data.phone_number
    user.job_title = data.job_title
    user.employee_code = data.employee_code
    user.department_id = data.department_id
    user.designation_id = data.designation_id
    user.work_location_id = data.work_location_id
    user.is_active = data.is_active if data.is_active is not None else user.is_active
    user.is_superuser = data.is_superuser if data.is_superuser is not None else user.is_superuser
    if data.password:
        user.hashed_password = get_password_hash(data.password)

    await db.commit()
    await db.refresh(user)

    result = await db.execute(
        select(models.User)
        .options(
            selectinload(models.User.department),
            selectinload(models.User.designation),
            selectinload(models.User.work_location)
        )
        .where(models.User.id == user.id)
    )
    return result.scalars().first()


@router.patch("/employees/{user_id}", response_model=schemas.User, summary="Update Employee (Partial)")
async def patch_employee(
    user_id: int,
    data: schemas.UserUpdate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    update_data = data.model_dump(exclude_unset=True)
    if "password" in update_data and update_data["password"]:
        user.hashed_password = get_password_hash(update_data.pop("password"))
    
    for key, value in update_data.items():
        setattr(user, key, value)

    await db.commit()
    await db.refresh(user)

    result = await db.execute(
        select(models.User)
        .options(
            selectinload(models.User.department),
            selectinload(models.User.designation),
            selectinload(models.User.work_location)
        )
        .where(models.User.id == user.id)
    )
    return result.scalars().first()


@router.delete("/employees/{user_id}", status_code=status.HTTP_200_OK, summary="Delete Employee")
async def delete_employee(
    user_id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    await db.delete(user)
    await db.commit()
    return {"detail": "Employee deleted successfully"}
