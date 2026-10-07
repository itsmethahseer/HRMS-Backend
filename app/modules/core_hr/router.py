from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import date

from app.core.dependencies import get_tenant_db_from_token, get_current_user
from app.modules.core_hr import models, schemas
from app.core.security import get_password_hash

router = APIRouter()


# ═══════════════════════════════════════════════════════════
# ROLES (GET, POST, GET/{id}, PUT, PATCH, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/roles/", response_model=schemas.RoleOut, status_code=status.HTTP_201_CREATED, summary="Create Role")
async def create_role(
    data: schemas.RoleCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    existing = await db.execute(select(models.Role).where(models.Role.name == data.name))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Role already exists")

    role = models.Role(name=data.name, description=data.description, is_active=data.is_active)
    db.add(role)
    await db.flush()

    for perm_id in (data.permission_ids or []):
        rp = models.RolePermission(role_id=role.id, permission_id=perm_id)
        db.add(rp)

    await db.commit()
    res = await db.execute(
        select(models.Role).options(
            selectinload(models.Role.permissions).selectinload(models.RolePermission.permission)
        ).where(models.Role.id == role.id)
    )
    return res.scalars().first()


@router.get("/roles/", response_model=List[schemas.RoleOut], summary="List Roles")
async def list_roles(
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.Role)
        .options(selectinload(models.Role.permissions).selectinload(models.RolePermission.permission))
        .offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.get("/roles/{id}", response_model=schemas.RoleOut, summary="Get Role by ID")
async def get_role(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.Role)
        .options(selectinload(models.Role.permissions).selectinload(models.RolePermission.permission))
        .where(models.Role.id == id)
    )
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Role not found")
    return item


@router.put("/roles/{id}", response_model=schemas.RoleOut, summary="Update Role (Full)")
async def update_role(
    id: int,
    data: schemas.RoleCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(select(models.Role).where(models.Role.id == id))
    role = result.scalars().first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    role.name = data.name
    role.description = data.description
    role.is_active = data.is_active if data.is_active is not None else role.is_active

    # Replace permissions
    existing_rps = await db.execute(select(models.RolePermission).where(models.RolePermission.role_id == id))
    for rp in existing_rps.scalars().all():
        await db.delete(rp)
    for perm_id in (data.permission_ids or []):
        db.add(models.RolePermission(role_id=id, permission_id=perm_id))

    await db.commit()
    res = await db.execute(
        select(models.Role)
        .options(selectinload(models.Role.permissions).selectinload(models.RolePermission.permission))
        .where(models.Role.id == id)
    )
    return res.scalars().first()


@router.patch("/roles/{id}", response_model=schemas.RoleOut, summary="Update Role (Partial)")
async def patch_role(
    id: int,
    data: schemas.RoleUpdate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(select(models.Role).where(models.Role.id == id))
    role = result.scalars().first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    update_data = data.model_dump(exclude_unset=True)
    perm_ids = update_data.pop("permission_ids", None)

    for key, value in update_data.items():
        setattr(role, key, value)

    if perm_ids is not None:
        existing_rps = await db.execute(select(models.RolePermission).where(models.RolePermission.role_id == id))
        for rp in existing_rps.scalars().all():
            await db.delete(rp)
        for perm_id in perm_ids:
            db.add(models.RolePermission(role_id=id, permission_id=perm_id))

    await db.commit()
    res = await db.execute(
        select(models.Role)
        .options(selectinload(models.Role.permissions).selectinload(models.RolePermission.permission))
        .where(models.Role.id == id)
    )
    return res.scalars().first()


@router.delete("/roles/{id}", status_code=status.HTTP_200_OK, summary="Delete Role")
async def delete_role(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(select(models.Role).where(models.Role.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Role not found")
    await db.delete(item)
    await db.commit()
    return {"detail": "Role deleted successfully"}


# ═══════════════════════════════════════════════════════════
# PERMISSIONS (GET, POST, GET/{id}, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/permissions/", response_model=schemas.PermissionOut, status_code=status.HTTP_201_CREATED, summary="Create Permission")
async def create_permission(
    data: schemas.PermissionCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    existing = await db.execute(select(models.Permission).where(models.Permission.name == data.name))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Permission already exists")
    perm = models.Permission(**data.model_dump())
    db.add(perm)
    await db.commit()
    await db.refresh(perm)
    return perm


@router.get("/permissions/", response_model=List[schemas.PermissionOut], summary="List Permissions")
async def list_permissions(
    resource: Optional[str] = None,
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    query = select(models.Permission)
    if resource:
        query = query.where(models.Permission.resource == resource)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/permissions/{id}", response_model=schemas.PermissionOut, summary="Get Permission by ID")
async def get_permission(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(select(models.Permission).where(models.Permission.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Permission not found")
    return item


@router.delete("/permissions/{id}", status_code=status.HTTP_200_OK, summary="Delete Permission")
async def delete_permission(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(select(models.Permission).where(models.Permission.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Permission not found")
    await db.delete(item)
    await db.commit()
    return {"detail": "Permission deleted successfully"}


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

def _user_load_options():
    return [
        selectinload(models.User.department),
        selectinload(models.User.designation),
        selectinload(models.User.work_location),
        selectinload(models.User.role).selectinload(models.Role.permissions).selectinload(models.RolePermission.permission),
    ]


@router.post("/employees/", response_model=schemas.User, status_code=status.HTTP_201_CREATED, summary="Create Employee")
async def create_employee(
    user: schemas.UserCreate, 
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(select(models.User).where(models.User.email == user.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    data = user.model_dump(exclude={"password"})
    db_user = models.User(**data, hashed_password=get_password_hash(user.password))
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    result = await db.execute(
        select(models.User).options(*_user_load_options()).where(models.User.id == db_user.id)
    )
    return result.scalars().first()


@router.get("/employees/directory", response_model=List[schemas.EmployeeDirectoryItem], summary="Employee Directory (Lightweight)")
async def employee_directory(
    department_id: Optional[int] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 200,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    """Public-facing lightweight employee directory (no sensitive data)."""
    query = (
        select(models.User)
        .options(
            selectinload(models.User.department),
            selectinload(models.User.designation),
            selectinload(models.User.work_location),
        )
        .where(models.User.is_active == True)
    )
    if department_id:
        query = query.where(models.User.department_id == department_id)
    if search:
        query = query.where(
            (models.User.first_name.ilike(f"%{search}%")) |
            (models.User.last_name.ilike(f"%{search}%")) |
            (models.User.job_title.ilike(f"%{search}%"))
        )
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


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
    query = select(models.User).options(*_user_load_options())
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


@router.get("/employees/{user_id}/team", response_model=List[schemas.EmployeeDirectoryItem], summary="Get Employee's Direct Reports (Team)")
async def get_employee_team(
    user_id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    """Returns all employees who report directly to the given user."""
    result = await db.execute(
        select(models.User)
        .options(
            selectinload(models.User.department),
            selectinload(models.User.designation),
            selectinload(models.User.work_location),
        )
        .where(models.User.manager_id == user_id, models.User.is_active == True)
    )
    return result.scalars().all()


@router.post("/employees/{user_id}/initiate-exit", summary="Initiate Employee Exit / Offboarding")
async def initiate_exit(
    user_id: int,
    data: schemas.InitiateExitRequest,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    """Marks an employee's exit with date, reason, and type."""
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Employee not found")

    user.exit_date = data.exit_date
    user.exit_reason = data.exit_reason
    user.exit_type = data.exit_type
    await db.commit()
    return {"detail": f"Exit initiated for employee {user_id}. Exit date: {data.exit_date}"}


@router.patch("/employees/{user_id}/complete-exit", summary="Complete Employee Exit (Deactivate)")
async def complete_exit(
    user_id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    """Deactivates the employee account after completing offboarding."""
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Employee not found")
    if not user.exit_date:
        raise HTTPException(status_code=400, detail="Exit must be initiated first via /initiate-exit")

    user.is_active = False
    await db.commit()
    return {"detail": f"Employee {user_id} has been deactivated. Offboarding complete."}


@router.get("/employees/{user_id}", response_model=schemas.User, summary="Get Employee by ID")
async def get_employee(
    user_id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.User).options(*_user_load_options()).where(models.User.id == user_id)
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
    
    update_dict = data.model_dump(exclude={"password"})
    for key, value in update_dict.items():
        setattr(user, key, value)
    if data.password:
        user.hashed_password = get_password_hash(data.password)

    await db.commit()
    await db.refresh(user)

    result = await db.execute(
        select(models.User).options(*_user_load_options()).where(models.User.id == user.id)
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
        select(models.User).options(*_user_load_options()).where(models.User.id == user.id)
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


# ═══════════════════════════════════════════════════════════
# ORG CHART
# ═══════════════════════════════════════════════════════════

@router.get("/org-chart", response_model=List[schemas.OrgChartNode], summary="Get Organisation Chart")
async def get_org_chart(
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: models.User = Depends(get_current_user)
):
    """
    Returns all active employees with their manager relationships.
    The frontend can render this as a hierarchical org chart.
    """
    result = await db.execute(
        select(models.User)
        .options(selectinload(models.User.department))
        .where(models.User.is_active == True)
    )
    users = result.scalars().all()
    return [
        schemas.OrgChartNode(
            id=u.id,
            name=f"{u.first_name} {u.last_name}",
            job_title=u.job_title,
            department=u.department.name if u.department else None,
            manager_id=u.manager_id,
        )
        for u in users
    ]
