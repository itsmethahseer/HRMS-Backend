from datetime import datetime, date, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_tenant_db_from_token, get_current_user
from app.modules.core_hr.models import User
from app.modules.expense import models, schemas

router = APIRouter()


# ═══════════════════════════════════════════════════════════
# EXPENSE CATEGORIES (GET, POST, GET/{id}, PUT, PATCH, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/categories/", response_model=schemas.ExpenseCategoryOut, status_code=status.HTTP_201_CREATED, summary="Create Expense Category")
async def create_category(
    data: schemas.ExpenseCategoryCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    existing = await db.execute(
        select(models.ExpenseCategory).where(
            (models.ExpenseCategory.name == data.name) | (models.ExpenseCategory.code == data.code)
        )
    )
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Category with this name or code already exists")

    cat = models.ExpenseCategory(**data.model_dump())
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return cat


@router.get("/categories/", response_model=List[schemas.ExpenseCategoryOut], summary="List Expense Categories")
async def list_categories(
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = select(models.ExpenseCategory)
    if is_active is not None:
        query = query.where(models.ExpenseCategory.is_active == is_active)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/categories/{id}", response_model=schemas.ExpenseCategoryOut, summary="Get Expense Category by ID")
async def get_category(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.ExpenseCategory).where(models.ExpenseCategory.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Expense category not found")
    return item


@router.put("/categories/{id}", response_model=schemas.ExpenseCategoryOut, summary="Update Expense Category (Full)")
async def update_category(
    id: int,
    data: schemas.ExpenseCategoryCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.ExpenseCategory).where(models.ExpenseCategory.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Expense category not found")
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/categories/{id}", response_model=schemas.ExpenseCategoryOut, summary="Update Expense Category (Partial)")
async def patch_category(
    id: int,
    data: schemas.ExpenseCategoryUpdate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.ExpenseCategory).where(models.ExpenseCategory.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Expense category not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/categories/{id}", status_code=status.HTTP_200_OK, summary="Delete Expense Category")
async def delete_category(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.ExpenseCategory).where(models.ExpenseCategory.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Expense category not found")
    await db.delete(item)
    await db.commit()
    return {"detail": "Expense category deleted successfully"}


# ═══════════════════════════════════════════════════════════
# EXPENSE CLAIMS (GET, POST, GET/{id}, PUT, PATCH, APPROVE, REJECT, REIMBURSE, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/claims/", response_model=schemas.ExpenseClaimOut, status_code=status.HTTP_201_CREATED, summary="Submit Expense Claim")
async def create_claim(
    data: schemas.ExpenseClaimCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    claim = models.ExpenseClaim(
        employee_id=current_user.id,
        **data.model_dump(),
        status=models.ExpenseStatusEnum.submitted
    )
    db.add(claim)
    await db.commit()
    await db.refresh(claim)

    res = await db.execute(
        select(models.ExpenseClaim)
        .options(selectinload(models.ExpenseClaim.category))
        .where(models.ExpenseClaim.id == claim.id)
    )
    return res.scalars().first()


@router.get("/claims/", response_model=List[schemas.ExpenseClaimOut], summary="List All Expense Claims")
async def list_claims(
    employee_id: Optional[int] = None,
    status_filter: Optional[models.ExpenseStatusEnum] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = select(models.ExpenseClaim).options(selectinload(models.ExpenseClaim.category))
    if employee_id:
        query = query.where(models.ExpenseClaim.employee_id == employee_id)
    if status_filter:
        query = query.where(models.ExpenseClaim.status == status_filter)
    query = query.order_by(models.ExpenseClaim.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/claims/my", response_model=List[schemas.ExpenseClaimOut], summary="My Expense Claims")
async def get_my_claims(
    status_filter: Optional[models.ExpenseStatusEnum] = None,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = (
        select(models.ExpenseClaim)
        .options(selectinload(models.ExpenseClaim.category))
        .where(models.ExpenseClaim.employee_id == current_user.id)
    )
    if status_filter:
        query = query.where(models.ExpenseClaim.status == status_filter)
    query = query.order_by(models.ExpenseClaim.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/claims/{id}", response_model=schemas.ExpenseClaimOut, summary="Get Expense Claim by ID")
async def get_claim(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.ExpenseClaim)
        .options(selectinload(models.ExpenseClaim.category))
        .where(models.ExpenseClaim.id == id)
    )
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Expense claim not found")
    return item


@router.put("/claims/{id}", response_model=schemas.ExpenseClaimOut, summary="Update Expense Claim (Full)")
async def update_claim(
    id: int,
    data: schemas.ExpenseClaimCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.ExpenseClaim).where(models.ExpenseClaim.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Expense claim not found")

    for key, value in data.model_dump().items():
        setattr(item, key, value)

    await db.commit()
    res = await db.execute(
        select(models.ExpenseClaim)
        .options(selectinload(models.ExpenseClaim.category))
        .where(models.ExpenseClaim.id == item.id)
    )
    return res.scalars().first()


@router.patch("/claims/{id}", response_model=schemas.ExpenseClaimOut, summary="Update Expense Claim (Partial)")
async def patch_claim(
    id: int,
    data: schemas.ExpenseClaimUpdate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.ExpenseClaim).where(models.ExpenseClaim.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Expense claim not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)

    await db.commit()
    res = await db.execute(
        select(models.ExpenseClaim)
        .options(selectinload(models.ExpenseClaim.category))
        .where(models.ExpenseClaim.id == item.id)
    )
    return res.scalars().first()


@router.patch("/claims/{id}/approve", response_model=schemas.ExpenseClaimOut, summary="Approve Expense Claim")
async def approve_claim(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.ExpenseClaim).where(models.ExpenseClaim.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Expense claim not found")

    item.status = models.ExpenseStatusEnum.approved
    item.approver_id = current_user.id
    item.approved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(item)

    res = await db.execute(
        select(models.ExpenseClaim)
        .options(selectinload(models.ExpenseClaim.category))
        .where(models.ExpenseClaim.id == item.id)
    )
    return res.scalars().first()


@router.patch("/claims/{id}/reject", response_model=schemas.ExpenseClaimOut, summary="Reject Expense Claim")
async def reject_claim(
    id: int,
    data: schemas.ExpenseClaimReview,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.ExpenseClaim).where(models.ExpenseClaim.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Expense claim not found")

    item.status = models.ExpenseStatusEnum.rejected
    item.approver_id = current_user.id
    item.rejection_reason = data.rejection_reason
    await db.commit()
    await db.refresh(item)

    res = await db.execute(
        select(models.ExpenseClaim)
        .options(selectinload(models.ExpenseClaim.category))
        .where(models.ExpenseClaim.id == item.id)
    )
    return res.scalars().first()


@router.patch("/claims/{id}/reimburse", response_model=schemas.ExpenseClaimOut, summary="Mark Expense Claim as Reimbursed")
async def reimburse_claim(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.ExpenseClaim).where(models.ExpenseClaim.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Expense claim not found")

    item.status = models.ExpenseStatusEnum.reimbursed
    await db.commit()
    await db.refresh(item)

    res = await db.execute(
        select(models.ExpenseClaim)
        .options(selectinload(models.ExpenseClaim.category))
        .where(models.ExpenseClaim.id == item.id)
    )
    return res.scalars().first()


@router.delete("/claims/{id}", status_code=status.HTTP_200_OK, summary="Delete Expense Claim")
async def delete_claim(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.ExpenseClaim).where(models.ExpenseClaim.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Expense claim not found")
    await db.delete(item)
    await db.commit()
    return {"detail": "Expense claim deleted successfully"}


# ═══════════════════════════════════════════════════════════
# CASH ADVANCES (GET, POST, GET/{id}, PATCH, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/advances/", response_model=schemas.CashAdvanceOut, status_code=status.HTTP_201_CREATED, summary="Request Cash Advance")
async def create_advance(
    data: schemas.CashAdvanceCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    adv = models.CashAdvance(
        employee_id=current_user.id,
        **data.model_dump(),
        status=models.AdvanceStatusEnum.pending
    )
    db.add(adv)
    await db.commit()
    await db.refresh(adv)
    return adv


@router.get("/advances/", response_model=List[schemas.CashAdvanceOut], summary="List Cash Advances")
async def list_advances(
    status_filter: Optional[models.AdvanceStatusEnum] = None,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = select(models.CashAdvance)
    if status_filter:
        query = query.where(models.CashAdvance.status == status_filter)
    result = await db.execute(query.order_by(models.CashAdvance.created_at.desc()))
    return result.scalars().all()


@router.get("/advances/my", response_model=List[schemas.CashAdvanceOut], summary="My Cash Advances")
async def get_my_advances(
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.CashAdvance)
        .where(models.CashAdvance.employee_id == current_user.id)
        .order_by(models.CashAdvance.created_at.desc())
    )
    return result.scalars().all()


@router.get("/advances/{id}", response_model=schemas.CashAdvanceOut, summary="Get Cash Advance by ID")
async def get_advance(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.CashAdvance).where(models.CashAdvance.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Cash advance not found")
    return item


@router.patch("/advances/{id}/review", response_model=schemas.CashAdvanceOut, summary="Review Cash Advance")
async def review_advance(
    id: int,
    data: schemas.CashAdvanceReview,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.CashAdvance).where(models.CashAdvance.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Cash advance not found")

    item.status = data.status
    item.notes = data.notes
    item.approver_id = current_user.id
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/advances/{id}", status_code=status.HTTP_200_OK, summary="Delete Cash Advance")
async def delete_advance(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.CashAdvance).where(models.CashAdvance.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Cash advance not found")
    await db.delete(item)
    await db.commit()
    return {"detail": "Cash advance deleted successfully"}
