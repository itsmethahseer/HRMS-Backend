from datetime import datetime, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_tenant_db_from_token, get_current_user
from app.modules.core_hr.models import User
from app.modules.leave import models, schemas

router = APIRouter()


# ═══════════════════════════════════════════════════════════
# LEAVE TYPES (GET, POST, GET/{id}, PUT, PATCH, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/types/", response_model=schemas.LeaveTypeOut, status_code=status.HTTP_201_CREATED, summary="Create Leave Type")
async def create_leave_type(
    data: schemas.LeaveTypeCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    existing = await db.execute(
        select(models.LeaveType).where((models.LeaveType.name == data.name) | (models.LeaveType.code == data.code))
    )
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Leave type with this name or code already exists")
    
    leave_type = models.LeaveType(**data.model_dump())
    db.add(leave_type)
    await db.commit()
    await db.refresh(leave_type)
    return leave_type


@router.get("/types/", response_model=List[schemas.LeaveTypeOut], summary="List Leave Types")
async def list_leave_types(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = select(models.LeaveType)
    if is_active is not None:
        query = query.where(models.LeaveType.is_active == is_active)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/types/{id}", response_model=schemas.LeaveTypeOut, summary="Get Leave Type by ID")
async def get_leave_type(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.LeaveType).where(models.LeaveType.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Leave type not found")
    return item


@router.put("/types/{id}", response_model=schemas.LeaveTypeOut, summary="Update Leave Type (Full)")
async def update_leave_type(
    id: int,
    data: schemas.LeaveTypeCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.LeaveType).where(models.LeaveType.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Leave type not found")
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/types/{id}", response_model=schemas.LeaveTypeOut, summary="Update Leave Type (Partial)")
async def patch_leave_type(
    id: int,
    data: schemas.LeaveTypeUpdate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.LeaveType).where(models.LeaveType.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Leave type not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/types/{id}", status_code=status.HTTP_200_OK, summary="Delete Leave Type")
async def delete_leave_type(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.LeaveType).where(models.LeaveType.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Leave type not found")
    await db.delete(item)
    await db.commit()
    return {"detail": "Leave type deleted successfully"}


# ═══════════════════════════════════════════════════════════
# LEAVE BALANCES (GET, POST, PUT, PATCH, ALLOCATE-ANNUAL)
# ═══════════════════════════════════════════════════════════

@router.post("/balances/allocate-annual", summary="Allocate Annual Quota to Employees")
async def allocate_annual_quota(
    year: int = Query(default=date.today().year),
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    # Fetch all active users and active leave types
    users_res = await db.execute(select(User).where(User.is_active == True))
    users = users_res.scalars().all()

    lt_res = await db.execute(select(models.LeaveType).where(models.LeaveType.is_active == True))
    leave_types = lt_res.scalars().all()

    created_count = 0
    for u in users:
        for lt in leave_types:
            existing = await db.execute(
                select(models.LeaveBalance).where(
                    models.LeaveBalance.employee_id == u.id,
                    models.LeaveBalance.leave_type_id == lt.id,
                    models.LeaveBalance.year == year
                )
            )
            if not existing.scalars().first():
                bal = models.LeaveBalance(
                    employee_id=u.id,
                    leave_type_id=lt.id,
                    year=year,
                    opening_balance=lt.default_annual_quota,
                    accrued=lt.default_annual_quota,
                    availed=0.0,
                    encashed=0.0,
                    closing_balance=lt.default_annual_quota
                )
                db.add(bal)
                created_count += 1

    await db.commit()
    return {"message": f"Successfully allocated leave balances for {created_count} records for year {year}"}


@router.get("/balances/", response_model=List[schemas.LeaveBalanceOut], summary="List Leave Balances")
async def list_leave_balances(
    employee_id: Optional[int] = None,
    year: Optional[int] = Query(default=date.today().year),
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = (
        select(models.LeaveBalance)
        .options(selectinload(models.LeaveBalance.leave_type))
        .where(models.LeaveBalance.year == year)
    )
    if employee_id:
        query = query.where(models.LeaveBalance.employee_id == employee_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/balances/my", response_model=List[schemas.LeaveBalanceOut], summary="My Leave Balances")
async def get_my_leave_balances(
    year: Optional[int] = Query(default=date.today().year),
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.LeaveBalance)
        .options(selectinload(models.LeaveBalance.leave_type))
        .where(
            models.LeaveBalance.employee_id == current_user.id,
            models.LeaveBalance.year == year
        )
    )
    return result.scalars().all()


@router.post("/balances/", response_model=schemas.LeaveBalanceOut, status_code=status.HTTP_201_CREATED, summary="Create/Adjust Leave Balance Manual")
async def create_leave_balance(
    data: schemas.LeaveBalanceCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    bal = models.LeaveBalance(**data.model_dump())
    db.add(bal)
    await db.commit()
    await db.refresh(bal)
    res = await db.execute(
        select(models.LeaveBalance).options(selectinload(models.LeaveBalance.leave_type)).where(models.LeaveBalance.id == bal.id)
    )
    return res.scalars().first()


@router.put("/balances/{id}", response_model=schemas.LeaveBalanceOut, summary="Update Leave Balance (Full)")
async def update_leave_balance(
    id: int,
    data: schemas.LeaveBalanceCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.LeaveBalance).where(models.LeaveBalance.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Leave balance not found")
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    res = await db.execute(
        select(models.LeaveBalance).options(selectinload(models.LeaveBalance.leave_type)).where(models.LeaveBalance.id == item.id)
    )
    return res.scalars().first()


@router.patch("/balances/{id}", response_model=schemas.LeaveBalanceOut, summary="Update Leave Balance (Partial)")
async def patch_leave_balance(
    id: int,
    data: schemas.LeaveBalanceUpdate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.LeaveBalance).where(models.LeaveBalance.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Leave balance not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    res = await db.execute(
        select(models.LeaveBalance).options(selectinload(models.LeaveBalance.leave_type)).where(models.LeaveBalance.id == item.id)
    )
    return res.scalars().first()


# ═══════════════════════════════════════════════════════════
# LEAVE REQUESTS (POST, GET, GET/my, GET/{id}, APPROVE, REJECT, CANCEL, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/requests/", response_model=schemas.LeaveRequestOut, status_code=status.HTTP_201_CREATED, summary="Apply for Leave")
async def create_leave_request(
    data: schemas.LeaveRequestCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    # Verify leave type exists
    lt_res = await db.execute(select(models.LeaveType).where(models.LeaveType.id == data.leave_type_id))
    lt = lt_res.scalars().first()
    if not lt:
        raise HTTPException(status_code=404, detail="Leave type not found")

    # Verify balance if paid leave
    if lt.is_paid and lt.code != "LOP":
        year = data.start_date.year
        bal_res = await db.execute(
            select(models.LeaveBalance).where(
                models.LeaveBalance.employee_id == current_user.id,
                models.LeaveBalance.leave_type_id == lt.id,
                models.LeaveBalance.year == year
            )
        )
        bal = bal_res.scalars().first()
        if bal and bal.closing_balance < data.days_count:
            raise HTTPException(status_code=400, detail=f"Insufficient leave balance. Available: {bal.closing_balance} days")

    req = models.LeaveRequest(
        employee_id=current_user.id,
        leave_type_id=data.leave_type_id,
        start_date=data.start_date,
        end_date=data.end_date,
        is_half_day=data.is_half_day if data.is_half_day is not None else False,
        half_day_session=data.half_day_session,
        days_count=data.days_count,
        reason=data.reason,
        document_url=data.document_url,
        status=models.LeaveStatusEnum.pending
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)

    res = await db.execute(
        select(models.LeaveRequest)
        .options(selectinload(models.LeaveRequest.leave_type))
        .where(models.LeaveRequest.id == req.id)
    )
    return res.scalars().first()


@router.get("/requests/", response_model=List[schemas.LeaveRequestOut], summary="List Leave Requests")
async def list_leave_requests(
    skip: int = 0,
    limit: int = 100,
    employee_id: Optional[int] = None,
    status_filter: Optional[models.LeaveStatusEnum] = None,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = (
        select(models.LeaveRequest)
        .options(selectinload(models.LeaveRequest.leave_type))
    )
    if employee_id:
        query = query.where(models.LeaveRequest.employee_id == employee_id)
    if status_filter:
        query = query.where(models.LeaveRequest.status == status_filter)

    query = query.order_by(models.LeaveRequest.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/requests/my", response_model=List[schemas.LeaveRequestOut], summary="My Leave Requests")
async def get_my_leave_requests(
    status_filter: Optional[models.LeaveStatusEnum] = None,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = (
        select(models.LeaveRequest)
        .options(selectinload(models.LeaveRequest.leave_type))
        .where(models.LeaveRequest.employee_id == current_user.id)
    )
    if status_filter:
        query = query.where(models.LeaveRequest.status == status_filter)
    query = query.order_by(models.LeaveRequest.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/requests/{id}", response_model=schemas.LeaveRequestOut, summary="Get Leave Request by ID")
async def get_leave_request(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.LeaveRequest)
        .options(selectinload(models.LeaveRequest.leave_type))
        .where(models.LeaveRequest.id == id)
    )
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Leave request not found")
    return item


@router.patch("/requests/{id}/approve", response_model=schemas.LeaveRequestOut, summary="Approve Leave Request")
async def approve_leave_request(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.LeaveRequest).where(models.LeaveRequest.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Leave request not found")

    if item.status == models.LeaveStatusEnum.approved:
        raise HTTPException(status_code=400, detail="Leave request is already approved")

    item.status = models.LeaveStatusEnum.approved
    item.approver_id = current_user.id

    # Deduct from Leave Balance
    year = item.start_date.year
    bal_res = await db.execute(
        select(models.LeaveBalance).where(
            models.LeaveBalance.employee_id == item.employee_id,
            models.LeaveBalance.leave_type_id == item.leave_type_id,
            models.LeaveBalance.year == year
        )
    )
    bal = bal_res.scalars().first()
    if bal:
        bal.availed += item.days_count
        bal.closing_balance = bal.accrued - bal.availed - bal.encashed

    await db.commit()
    await db.refresh(item)

    res = await db.execute(
        select(models.LeaveRequest)
        .options(selectinload(models.LeaveRequest.leave_type))
        .where(models.LeaveRequest.id == item.id)
    )
    return res.scalars().first()


@router.patch("/requests/{id}/reject", response_model=schemas.LeaveRequestOut, summary="Reject Leave Request")
async def reject_leave_request(
    id: int,
    data: schemas.LeaveRequestReview,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.LeaveRequest).where(models.LeaveRequest.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Leave request not found")

    item.status = models.LeaveStatusEnum.rejected
    item.approver_id = current_user.id
    item.rejection_reason = data.rejection_reason

    await db.commit()
    await db.refresh(item)

    res = await db.execute(
        select(models.LeaveRequest)
        .options(selectinload(models.LeaveRequest.leave_type))
        .where(models.LeaveRequest.id == item.id)
    )
    return res.scalars().first()


@router.patch("/requests/{id}/cancel", response_model=schemas.LeaveRequestOut, summary="Cancel Leave Request")
async def cancel_leave_request(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.LeaveRequest).where(models.LeaveRequest.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Leave request not found")

    if item.employee_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this request")

    # If it was already approved, refund balance
    if item.status == models.LeaveStatusEnum.approved:
        year = item.start_date.year
        bal_res = await db.execute(
            select(models.LeaveBalance).where(
                models.LeaveBalance.employee_id == item.employee_id,
                models.LeaveBalance.leave_type_id == item.leave_type_id,
                models.LeaveBalance.year == year
            )
        )
        bal = bal_res.scalars().first()
        if bal:
            bal.availed = max(0.0, bal.availed - item.days_count)
            bal.closing_balance = bal.accrued - bal.availed - bal.encashed

    item.status = models.LeaveStatusEnum.cancelled
    await db.commit()
    await db.refresh(item)

    res = await db.execute(
        select(models.LeaveRequest)
        .options(selectinload(models.LeaveRequest.leave_type))
        .where(models.LeaveRequest.id == item.id)
    )
    return res.scalars().first()


@router.delete("/requests/{id}", status_code=status.HTTP_200_OK, summary="Delete Leave Request")
async def delete_leave_request(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.LeaveRequest).where(models.LeaveRequest.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Leave request not found")
    await db.delete(item)
    await db.commit()
    return {"detail": "Leave request deleted successfully"}


# ═══════════════════════════════════════════════════════════
# HOLIDAYS (GET, POST, GET/{id}, PUT, PATCH, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/holidays/", response_model=schemas.HolidayOut, status_code=status.HTTP_201_CREATED, summary="Create Holiday")
async def create_holiday(
    data: schemas.HolidayCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    holiday = models.Holiday(**data.model_dump())
    db.add(holiday)
    await db.commit()
    await db.refresh(holiday)
    return holiday


@router.get("/holidays/", response_model=List[schemas.HolidayOut], summary="List Holidays")
async def list_holidays(
    year: Optional[int] = None,
    location_id: Optional[int] = None,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = select(models.Holiday)
    if location_id:
        query = query.where(
            (models.Holiday.applicable_location_id == location_id) | (models.Holiday.applicable_location_id == None)
        )
    query = query.order_by(models.Holiday.date.asc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/holidays/{id}", response_model=schemas.HolidayOut, summary="Get Holiday by ID")
async def get_holiday(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.Holiday).where(models.Holiday.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Holiday not found")
    return item


@router.put("/holidays/{id}", response_model=schemas.HolidayOut, summary="Update Holiday (Full)")
async def update_holiday(
    id: int,
    data: schemas.HolidayCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.Holiday).where(models.Holiday.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Holiday not found")
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/holidays/{id}", response_model=schemas.HolidayOut, summary="Update Holiday (Partial)")
async def patch_holiday(
    id: int,
    data: schemas.HolidayUpdate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.Holiday).where(models.Holiday.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Holiday not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/holidays/{id}", status_code=status.HTTP_200_OK, summary="Delete Holiday")
async def delete_holiday(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.Holiday).where(models.Holiday.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Holiday not found")
    await db.delete(item)
    await db.commit()
    return {"detail": "Holiday deleted successfully"}


# ═══════════════════════════════════════════════════════════
# LEAVE ENCASHMENTS (GET, POST, APPROVE, REJECT, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/encashments/", response_model=schemas.LeaveEncashmentOut, status_code=status.HTTP_201_CREATED, summary="Request Leave Encashment")
async def request_encashment(
    data: schemas.LeaveEncashmentCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    req = models.LeaveEncashment(
        employee_id=current_user.id,
        leave_type_id=data.leave_type_id,
        days_requested=data.days_requested,
        status=models.LeaveStatusEnum.pending
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return req


@router.get("/encashments/", response_model=List[schemas.LeaveEncashmentOut], summary="List Encashments")
async def list_encashments(
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.LeaveEncashment).order_by(models.LeaveEncashment.created_at.desc()))
    return result.scalars().all()


@router.patch("/encashments/{id}/approve", response_model=schemas.LeaveEncashmentOut, summary="Approve Encashment")
async def approve_encashment(
    id: int,
    data: schemas.LeaveEncashmentReview,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.LeaveEncashment).where(models.LeaveEncashment.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Encashment request not found")

    item.status = models.LeaveStatusEnum.approved
    item.approver_id = current_user.id
    item.amount = data.amount or item.amount
    item.comments = data.comments

    # Deduct from Leave Balance
    year = date.today().year
    bal_res = await db.execute(
        select(models.LeaveBalance).where(
            models.LeaveBalance.employee_id == item.employee_id,
            models.LeaveBalance.leave_type_id == item.leave_type_id,
            models.LeaveBalance.year == year
        )
    )
    bal = bal_res.scalars().first()
    if bal:
        bal.encashed += item.days_requested
        bal.closing_balance = bal.accrued - bal.availed - bal.encashed

    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/encashments/{id}", status_code=status.HTTP_200_OK, summary="Delete Encashment Request")
async def delete_encashment(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.LeaveEncashment).where(models.LeaveEncashment.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Encashment request not found")
    await db.delete(item)
    await db.commit()
    return {"detail": "Encashment request deleted successfully"}
