from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_tenant_db_from_token, get_current_user
from app.modules.core_hr.models import User
from app.modules.asset import models, schemas

router = APIRouter()


# ═══════════════════════════════════════════════════════════
# ASSET CATEGORIES (GET, POST, GET/{id}, PUT, PATCH, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/categories/", response_model=schemas.AssetCategoryOut, status_code=status.HTTP_201_CREATED, summary="Create Asset Category")
async def create_category(
    data: schemas.AssetCategoryCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    existing = await db.execute(select(models.AssetCategory).where(models.AssetCategory.name == data.name))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Asset category with this name already exists")

    cat = models.AssetCategory(**data.model_dump())
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return cat


@router.get("/categories/", response_model=List[schemas.AssetCategoryOut], summary="List Asset Categories")
async def list_categories(
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = select(models.AssetCategory)
    if is_active is not None:
        query = query.where(models.AssetCategory.is_active == is_active)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/categories/{id}", response_model=schemas.AssetCategoryOut, summary="Get Asset Category by ID")
async def get_category(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.AssetCategory).where(models.AssetCategory.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Asset category not found")
    return item


@router.put("/categories/{id}", response_model=schemas.AssetCategoryOut, summary="Update Asset Category (Full)")
async def update_category(
    id: int,
    data: schemas.AssetCategoryCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.AssetCategory).where(models.AssetCategory.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Asset category not found")
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/categories/{id}", response_model=schemas.AssetCategoryOut, summary="Update Asset Category (Partial)")
async def patch_category(
    id: int,
    data: schemas.AssetCategoryUpdate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.AssetCategory).where(models.AssetCategory.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Asset category not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/categories/{id}", status_code=status.HTTP_200_OK, summary="Delete Asset Category")
async def delete_category(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.AssetCategory).where(models.AssetCategory.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Asset category not found")
    await db.delete(item)
    await db.commit()
    return {"detail": "Asset category deleted successfully"}


# ═══════════════════════════════════════════════════════════
# ASSETS (GET, POST, GET/{id}, PUT, PATCH, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/items/", response_model=schemas.AssetOut, status_code=status.HTTP_201_CREATED, summary="Create Asset")
async def create_asset(
    data: schemas.AssetCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    existing = await db.execute(select(models.Asset).where(models.Asset.asset_code == data.asset_code))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Asset with this asset code already exists")

    asset = models.Asset(**data.model_dump())
    db.add(asset)
    await db.commit()
    await db.refresh(asset)

    res = await db.execute(
        select(models.Asset).options(selectinload(models.Asset.category)).where(models.Asset.id == asset.id)
    )
    return res.scalars().first()


@router.get("/items/", response_model=List[schemas.AssetOut], summary="List Assets")
async def list_assets(
    category_id: Optional[int] = None,
    status_filter: Optional[models.AssetStatusEnum] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = select(models.Asset).options(selectinload(models.Asset.category))
    if category_id:
        query = query.where(models.Asset.category_id == category_id)
    if status_filter:
        query = query.where(models.Asset.status == status_filter)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/items/{id}", response_model=schemas.AssetOut, summary="Get Asset by ID")
async def get_asset(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.Asset).options(selectinload(models.Asset.category)).where(models.Asset.id == id)
    )
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Asset not found")
    return item


@router.put("/items/{id}", response_model=schemas.AssetOut, summary="Update Asset (Full)")
async def update_asset(
    id: int,
    data: schemas.AssetCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.Asset).where(models.Asset.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Asset not found")
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    await db.commit()
    res = await db.execute(
        select(models.Asset).options(selectinload(models.Asset.category)).where(models.Asset.id == item.id)
    )
    return res.scalars().first()


@router.patch("/items/{id}", response_model=schemas.AssetOut, summary="Update Asset (Partial)")
async def patch_asset(
    id: int,
    data: schemas.AssetUpdate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.Asset).where(models.Asset.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Asset not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    await db.commit()
    res = await db.execute(
        select(models.Asset).options(selectinload(models.Asset.category)).where(models.Asset.id == item.id)
    )
    return res.scalars().first()


@router.delete("/items/{id}", status_code=status.HTTP_200_OK, summary="Delete Asset")
async def delete_asset(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.Asset).where(models.Asset.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Asset not found")
    await db.delete(item)
    await db.commit()
    return {"detail": "Asset deleted successfully"}


# ═══════════════════════════════════════════════════════════
# ASSET ASSIGNMENTS (GET, POST, GET/my, GET/{id}, PATCH /return, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/assignments/", response_model=schemas.AssetAssignmentOut, status_code=status.HTTP_201_CREATED, summary="Assign Asset to Employee")
async def assign_asset(
    data: schemas.AssetAssignmentCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    asset_res = await db.execute(select(models.Asset).where(models.Asset.id == data.asset_id))
    asset = asset_res.scalars().first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    asset.status = models.AssetStatusEnum.assigned

    assignment = models.AssetAssignment(
        asset_id=data.asset_id,
        employee_id=data.employee_id,
        assigned_date=data.assigned_date,
        condition_on_assignment=data.condition_on_assignment,
        notes=data.notes,
        is_returned=False
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)

    res = await db.execute(
        select(models.AssetAssignment)
        .options(selectinload(models.AssetAssignment.asset).selectinload(models.Asset.category))
        .where(models.AssetAssignment.id == assignment.id)
    )
    return res.scalars().first()


@router.get("/assignments/", response_model=List[schemas.AssetAssignmentOut], summary="List Asset Assignments")
async def list_assignments(
    employee_id: Optional[int] = None,
    asset_id: Optional[int] = None,
    is_returned: Optional[bool] = None,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = select(models.AssetAssignment).options(
        selectinload(models.AssetAssignment.asset).selectinload(models.Asset.category)
    )
    if employee_id:
        query = query.where(models.AssetAssignment.employee_id == employee_id)
    if asset_id:
        query = query.where(models.AssetAssignment.asset_id == asset_id)
    if is_returned is not None:
        query = query.where(models.AssetAssignment.is_returned == is_returned)
    result = await db.execute(query.order_by(models.AssetAssignment.assigned_date.desc()))
    return result.scalars().all()


@router.get("/assignments/my", response_model=List[schemas.AssetAssignmentOut], summary="My Assigned Assets")
async def get_my_assignments(
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.AssetAssignment)
        .options(selectinload(models.AssetAssignment.asset).selectinload(models.Asset.category))
        .where(models.AssetAssignment.employee_id == current_user.id, models.AssetAssignment.is_returned == False)
    )
    return result.scalars().all()


@router.get("/assignments/{id}", response_model=schemas.AssetAssignmentOut, summary="Get Assignment by ID")
async def get_assignment(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.AssetAssignment)
        .options(selectinload(models.AssetAssignment.asset).selectinload(models.Asset.category))
        .where(models.AssetAssignment.id == id)
    )
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Asset assignment not found")
    return item


@router.patch("/assignments/{id}/return", response_model=schemas.AssetAssignmentOut, summary="Process Asset Return")
async def return_asset(
    id: int,
    data: schemas.AssetReturnRequest,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.AssetAssignment)
        .options(selectinload(models.AssetAssignment.asset))
        .where(models.AssetAssignment.id == id)
    )
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Asset assignment not found")

    item.return_date = data.return_date
    item.condition_on_return = data.condition_on_return
    item.notes = (item.notes or "") + f"\nReturn note: {data.notes}" if data.notes else item.notes
    item.is_returned = True

    if item.asset:
        item.asset.status = models.AssetStatusEnum.available

    await db.commit()
    await db.refresh(item)

    res = await db.execute(
        select(models.AssetAssignment)
        .options(selectinload(models.AssetAssignment.asset).selectinload(models.Asset.category))
        .where(models.AssetAssignment.id == item.id)
    )
    return res.scalars().first()


@router.delete("/assignments/{id}", status_code=status.HTTP_200_OK, summary="Delete Assignment Record")
async def delete_assignment(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.AssetAssignment).where(models.AssetAssignment.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Asset assignment record not found")
    await db.delete(item)
    await db.commit()
    return {"detail": "Asset assignment deleted successfully"}
