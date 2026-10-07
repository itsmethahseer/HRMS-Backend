import math
from datetime import datetime, date, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_tenant_db_from_token, get_current_user
from app.modules.core_hr.models import User
from app.modules.attendance import models, schemas

router = APIRouter()


# Helper: Haversine distance in meters
def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000  # Radius of earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


# ═══════════════════════════════════════════════════════════
# SHIFTS (GET, POST, GET/{id}, PUT, PATCH, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/shifts/", response_model=schemas.ShiftOut, status_code=status.HTTP_201_CREATED, summary="Create Shift")
async def create_shift(
    data: schemas.ShiftCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    existing = await db.execute(select(models.Shift).where(models.Shift.name == data.name))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Shift with this name already exists")
    
    shift = models.Shift(**data.model_dump())
    db.add(shift)
    await db.commit()
    await db.refresh(shift)
    return shift


@router.get("/shifts/", response_model=List[schemas.ShiftOut], summary="List Shifts")
async def list_shifts(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = select(models.Shift)
    if is_active is not None:
        query = query.where(models.Shift.is_active == is_active)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/shifts/{id}", response_model=schemas.ShiftOut, summary="Get Shift by ID")
async def get_shift(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.Shift).where(models.Shift.id == id))
    shift = result.scalars().first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    return shift


@router.put("/shifts/{id}", response_model=schemas.ShiftOut, summary="Update Shift (Full)")
async def update_shift(
    id: int,
    data: schemas.ShiftCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.Shift).where(models.Shift.id == id))
    shift = result.scalars().first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    for key, value in data.model_dump().items():
        setattr(shift, key, value)
    await db.commit()
    await db.refresh(shift)
    return shift


@router.patch("/shifts/{id}", response_model=schemas.ShiftOut, summary="Update Shift (Partial)")
async def patch_shift(
    id: int,
    data: schemas.ShiftUpdate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.Shift).where(models.Shift.id == id))
    shift = result.scalars().first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(shift, key, value)
    await db.commit()
    await db.refresh(shift)
    return shift


@router.delete("/shifts/{id}", status_code=status.HTTP_200_OK, summary="Delete Shift")
async def delete_shift(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.Shift).where(models.Shift.id == id))
    shift = result.scalars().first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    await db.delete(shift)
    await db.commit()
    return {"detail": "Shift deleted successfully"}


# ═══════════════════════════════════════════════════════════
# GEOFENCE LOCATIONS (GET, POST, GET/{id}, PUT, PATCH, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/geofences/", response_model=schemas.GeofenceOut, status_code=status.HTTP_201_CREATED, summary="Create Geofence Location")
async def create_geofence(
    data: schemas.GeofenceCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    geofence = models.GeofenceLocation(**data.model_dump())
    db.add(geofence)
    await db.commit()
    await db.refresh(geofence)
    return geofence


@router.get("/geofences/", response_model=List[schemas.GeofenceOut], summary="List Geofences")
async def list_geofences(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = select(models.GeofenceLocation)
    if is_active is not None:
        query = query.where(models.GeofenceLocation.is_active == is_active)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/geofences/{id}", response_model=schemas.GeofenceOut, summary="Get Geofence by ID")
async def get_geofence(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.GeofenceLocation).where(models.GeofenceLocation.id == id))
    geofence = result.scalars().first()
    if not geofence:
        raise HTTPException(status_code=404, detail="Geofence location not found")
    return geofence


@router.put("/geofences/{id}", response_model=schemas.GeofenceOut, summary="Update Geofence (Full)")
async def update_geofence(
    id: int,
    data: schemas.GeofenceCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.GeofenceLocation).where(models.GeofenceLocation.id == id))
    geofence = result.scalars().first()
    if not geofence:
        raise HTTPException(status_code=404, detail="Geofence location not found")
    for key, value in data.model_dump().items():
        setattr(geofence, key, value)
    await db.commit()
    await db.refresh(geofence)
    return geofence


@router.patch("/geofences/{id}", response_model=schemas.GeofenceOut, summary="Update Geofence (Partial)")
async def patch_geofence(
    id: int,
    data: schemas.GeofenceUpdate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.GeofenceLocation).where(models.GeofenceLocation.id == id))
    geofence = result.scalars().first()
    if not geofence:
        raise HTTPException(status_code=404, detail="Geofence location not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(geofence, key, value)
    await db.commit()
    await db.refresh(geofence)
    return geofence


@router.delete("/geofences/{id}", status_code=status.HTTP_200_OK, summary="Delete Geofence")
async def delete_geofence(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.GeofenceLocation).where(models.GeofenceLocation.id == id))
    geofence = result.scalars().first()
    if not geofence:
        raise HTTPException(status_code=404, detail="Geofence location not found")
    await db.delete(geofence)
    await db.commit()
    return {"detail": "Geofence deleted successfully"}


# ═══════════════════════════════════════════════════════════
# PUNCH IN / PUNCH OUT (WEB & MOBILE CLOCK-IN)
# ═══════════════════════════════════════════════════════════

@router.post("/punch-in", response_model=schemas.AttendanceLogOut, summary="Web / Mobile Punch In")
async def punch_in(
    data: schemas.PunchInRequest,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    today = date.today()
    client_ip = request.client.host if request.client else None

    # Check if existing log for today
    result = await db.execute(
        select(models.AttendanceLog)
        .where(models.AttendanceLog.employee_id == current_user.id, models.AttendanceLog.date == today)
    )
    log = result.scalars().first()

    now_utc = datetime.now(timezone.utc)

    if log and log.punch_in:
        raise HTTPException(status_code=400, detail="Already punched in for today")

    if not log:
        log = models.AttendanceLog(
            employee_id=current_user.id,
            date=today,
            punch_in=now_utc,
            punch_in_ip=client_ip,
            punch_in_lat=data.latitude,
            punch_in_lng=data.longitude,
            punch_in_note=data.note,
            status=models.AttendanceStatusEnum.present
        )
        db.add(log)
    else:
        log.punch_in = now_utc
        log.punch_in_ip = client_ip
        log.punch_in_lat = data.latitude
        log.punch_in_lng = data.longitude
        log.punch_in_note = data.note

    await db.commit()
    await db.refresh(log)
    return log


@router.post("/punch-out", response_model=schemas.AttendanceLogOut, summary="Web / Mobile Punch Out")
async def punch_out(
    data: schemas.PunchOutRequest,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    today = date.today()
    client_ip = request.client.host if request.client else None

    result = await db.execute(
        select(models.AttendanceLog)
        .where(models.AttendanceLog.employee_id == current_user.id, models.AttendanceLog.date == today)
    )
    log = result.scalars().first()

    if not log or not log.punch_in:
        raise HTTPException(status_code=400, detail="Cannot punch out without punching in first")

    now_utc = datetime.now(timezone.utc)
    log.punch_out = now_utc
    log.punch_out_ip = client_ip
    log.punch_out_lat = data.latitude
    log.punch_out_lng = data.longitude
    log.punch_out_note = data.note

    # Calculate total hours worked
    delta = now_utc - (log.punch_in if log.punch_in.tzinfo else log.punch_in.replace(tzinfo=timezone.utc))
    hours = round(delta.total_seconds() / 3600.0, 2)
    log.total_hours = hours

    if hours < 4.0:
        log.status = models.AttendanceStatusEnum.half_day
    else:
        log.status = models.AttendanceStatusEnum.present

    await db.commit()
    await db.refresh(log)
    return log


# ═══════════════════════════════════════════════════════════
# ATTENDANCE LOGS (CRUD & FILTERS)
# ═══════════════════════════════════════════════════════════

@router.post("/logs/", response_model=schemas.AttendanceLogOut, status_code=status.HTTP_201_CREATED, summary="Create Attendance Log (Manual / HR)")
async def create_attendance_log(
    data: schemas.AttendanceLogCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    log = models.AttendanceLog(**data.model_dump())
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


@router.get("/logs/", response_model=List[schemas.AttendanceLogOut], summary="List Attendance Logs")
async def list_attendance_logs(
    skip: int = 0,
    limit: int = 100,
    employee_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status_filter: Optional[models.AttendanceStatusEnum] = None,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = select(models.AttendanceLog)
    if employee_id:
        query = query.where(models.AttendanceLog.employee_id == employee_id)
    if start_date:
        query = query.where(models.AttendanceLog.date >= start_date)
    if end_date:
        query = query.where(models.AttendanceLog.date <= end_date)
    if status_filter:
        query = query.where(models.AttendanceLog.status == status_filter)

    query = query.order_by(models.AttendanceLog.date.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/logs/my", response_model=List[schemas.AttendanceLogOut], summary="My Attendance Logs")
async def get_my_attendance_logs(
    month: Optional[int] = None,
    year: Optional[int] = None,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = select(models.AttendanceLog).where(models.AttendanceLog.employee_id == current_user.id)
    if year:
        # filter date
        pass
    query = query.order_by(models.AttendanceLog.date.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/logs/{id}", response_model=schemas.AttendanceLogOut, summary="Get Attendance Log by ID")
async def get_attendance_log(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.AttendanceLog).where(models.AttendanceLog.id == id))
    log = result.scalars().first()
    if not log:
        raise HTTPException(status_code=404, detail="Attendance log not found")
    return log


@router.put("/logs/{id}", response_model=schemas.AttendanceLogOut, summary="Update Attendance Log (Full)")
async def update_attendance_log(
    id: int,
    data: schemas.AttendanceLogCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.AttendanceLog).where(models.AttendanceLog.id == id))
    log = result.scalars().first()
    if not log:
        raise HTTPException(status_code=404, detail="Attendance log not found")
    for key, value in data.model_dump().items():
        setattr(log, key, value)
    await db.commit()
    await db.refresh(log)
    return log


@router.patch("/logs/{id}", response_model=schemas.AttendanceLogOut, summary="Update Attendance Log (Partial)")
async def patch_attendance_log(
    id: int,
    data: schemas.AttendanceLogUpdate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.AttendanceLog).where(models.AttendanceLog.id == id))
    log = result.scalars().first()
    if not log:
        raise HTTPException(status_code=404, detail="Attendance log not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(log, key, value)
    await db.commit()
    await db.refresh(log)
    return log


@router.delete("/logs/{id}", status_code=status.HTTP_200_OK, summary="Delete Attendance Log")
async def delete_attendance_log(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.AttendanceLog).where(models.AttendanceLog.id == id))
    log = result.scalars().first()
    if not log:
        raise HTTPException(status_code=404, detail="Attendance log not found")
    await db.delete(log)
    await db.commit()
    return {"detail": "Attendance log deleted successfully"}


# ═══════════════════════════════════════════════════════════
# ATTENDANCE REGULARIZATION (GET, POST, PATCH APPROVE/REJECT, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/regularizations/", response_model=schemas.RegularizationOut, status_code=status.HTTP_201_CREATED, summary="Request Attendance Regularization")
async def create_regularization(
    data: schemas.RegularizationCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    req = models.AttendanceRegularization(
        employee_id=current_user.id,
        attendance_log_id=data.attendance_log_id,
        date=data.date,
        requested_punch_in=data.requested_punch_in,
        requested_punch_out=data.requested_punch_out,
        reason=data.reason,
        status=models.RequestStatusEnum.pending
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return req


@router.get("/regularizations/", response_model=List[schemas.RegularizationOut], summary="List Regularizations")
async def list_regularizations(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[models.RequestStatusEnum] = None,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = select(models.AttendanceRegularization)
    if status_filter:
        query = query.where(models.AttendanceRegularization.status == status_filter)
    result = await db.execute(query.order_by(models.AttendanceRegularization.created_at.desc()).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/regularizations/my", response_model=List[schemas.RegularizationOut], summary="My Regularization Requests")
async def get_my_regularizations(
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.AttendanceRegularization)
        .where(models.AttendanceRegularization.employee_id == current_user.id)
        .order_by(models.AttendanceRegularization.created_at.desc())
    )
    return result.scalars().all()


@router.get("/regularizations/{id}", response_model=schemas.RegularizationOut, summary="Get Regularization Request by ID")
async def get_regularization(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.AttendanceRegularization).where(models.AttendanceRegularization.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Regularization request not found")
    return item


@router.patch("/regularizations/{id}/approve", response_model=schemas.RegularizationOut, summary="Approve Regularization")
async def approve_regularization(
    id: int,
    data: schemas.RegularizationReview,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.AttendanceRegularization).where(models.AttendanceRegularization.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Regularization request not found")

    item.status = models.RequestStatusEnum.approved
    item.approver_id = current_user.id
    item.approver_comment = data.approver_comment

    # Update or create attendance log
    log_res = await db.execute(
        select(models.AttendanceLog).where(
            models.AttendanceLog.employee_id == item.employee_id,
            models.AttendanceLog.date == item.date
        )
    )
    log = log_res.scalars().first()
    if not log:
        log = models.AttendanceLog(
            employee_id=item.employee_id,
            date=item.date,
            punch_in=item.requested_punch_in,
            punch_out=item.requested_punch_out,
            is_regularized=True,
            status=models.AttendanceStatusEnum.present
        )
        db.add(log)
    else:
        if item.requested_punch_in:
            log.punch_in = item.requested_punch_in
        if item.requested_punch_out:
            log.punch_out = item.requested_punch_out
        log.is_regularized = True
        log.status = models.AttendanceStatusEnum.present

    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/regularizations/{id}/reject", response_model=schemas.RegularizationOut, summary="Reject Regularization")
async def reject_regularization(
    id: int,
    data: schemas.RegularizationReview,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.AttendanceRegularization).where(models.AttendanceRegularization.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Regularization request not found")

    item.status = models.RequestStatusEnum.rejected
    item.approver_id = current_user.id
    item.approver_comment = data.approver_comment
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/regularizations/{id}", status_code=status.HTTP_200_OK, summary="Delete Regularization Request")
async def delete_regularization(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.AttendanceRegularization).where(models.AttendanceRegularization.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Regularization request not found")
    await db.delete(item)
    await db.commit()
    return {"detail": "Regularization request deleted successfully"}


# ═══════════════════════════════════════════════════════════
# OVERTIME REQUESTS (GET, POST, PATCH APPROVE/REJECT, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/overtime/", response_model=schemas.OvertimeOut, status_code=status.HTTP_201_CREATED, summary="Create Overtime Request")
async def create_overtime(
    data: schemas.OvertimeCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    req = models.OvertimeRequest(
        employee_id=current_user.id,
        date=data.date,
        overtime_hours=data.overtime_hours,
        reason=data.reason,
        status=models.RequestStatusEnum.pending
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return req


@router.get("/overtime/", response_model=List[schemas.OvertimeOut], summary="List Overtime Requests")
async def list_overtime_requests(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[models.RequestStatusEnum] = None,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = select(models.OvertimeRequest)
    if status_filter:
        query = query.where(models.OvertimeRequest.status == status_filter)
    result = await db.execute(query.order_by(models.OvertimeRequest.created_at.desc()).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/overtime/my", response_model=List[schemas.OvertimeOut], summary="My Overtime Requests")
async def get_my_overtime_requests(
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.OvertimeRequest)
        .where(models.OvertimeRequest.employee_id == current_user.id)
        .order_by(models.OvertimeRequest.created_at.desc())
    )
    return result.scalars().all()


@router.get("/overtime/{id}", response_model=schemas.OvertimeOut, summary="Get Overtime Request by ID")
async def get_overtime_request(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.OvertimeRequest).where(models.OvertimeRequest.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Overtime request not found")
    return item


@router.patch("/overtime/{id}/approve", response_model=schemas.OvertimeOut, summary="Approve Overtime Request")
async def approve_overtime(
    id: int,
    data: schemas.OvertimeReview,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.OvertimeRequest).where(models.OvertimeRequest.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Overtime request not found")

    item.status = models.RequestStatusEnum.approved
    item.approver_id = current_user.id
    item.approver_comment = data.approver_comment
    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/overtime/{id}/reject", response_model=schemas.OvertimeOut, summary="Reject Overtime Request")
async def reject_overtime(
    id: int,
    data: schemas.OvertimeReview,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.OvertimeRequest).where(models.OvertimeRequest.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Overtime request not found")

    item.status = models.RequestStatusEnum.rejected
    item.approver_id = current_user.id
    item.approver_comment = data.approver_comment
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/overtime/{id}", status_code=status.HTTP_200_OK, summary="Delete Overtime Request")
async def delete_overtime(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.OvertimeRequest).where(models.OvertimeRequest.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Overtime request not found")
    await db.delete(item)
    await db.commit()
    return {"detail": "Overtime request deleted successfully"}


# ═══════════════════════════════════════════════════════════
# SHIFT ASSIGNMENTS (POST, GET, GET/my, PATCH, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/shift-assignments/", response_model=schemas.ShiftAssignmentOut, status_code=status.HTTP_201_CREATED, summary="Assign Shift to Employee")
async def create_shift_assignment(
    data: schemas.ShiftAssignmentCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    assignment = models.ShiftAssignment(**data.model_dump())
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    res = await db.execute(
        select(models.ShiftAssignment)
        .options(selectinload(models.ShiftAssignment.shift))
        .where(models.ShiftAssignment.id == assignment.id)
    )
    return res.scalars().first()


@router.get("/shift-assignments/", response_model=List[schemas.ShiftAssignmentOut], summary="List Shift Assignments")
async def list_shift_assignments(
    employee_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = select(models.ShiftAssignment).options(selectinload(models.ShiftAssignment.shift))
    if employee_id:
        query = query.where(models.ShiftAssignment.employee_id == employee_id)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/shift-assignments/my", response_model=List[schemas.ShiftAssignmentOut], summary="My Shift Assignments")
async def my_shift_assignments(
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.ShiftAssignment)
        .options(selectinload(models.ShiftAssignment.shift))
        .where(models.ShiftAssignment.employee_id == current_user.id, models.ShiftAssignment.is_active == True)
    )
    return result.scalars().all()


@router.patch("/shift-assignments/{id}", response_model=schemas.ShiftAssignmentOut, summary="Update Shift Assignment")
async def update_shift_assignment(
    id: int,
    data: schemas.ShiftAssignmentUpdate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.ShiftAssignment).where(models.ShiftAssignment.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Shift assignment not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    await db.commit()
    res = await db.execute(
        select(models.ShiftAssignment).options(selectinload(models.ShiftAssignment.shift)).where(models.ShiftAssignment.id == id)
    )
    return res.scalars().first()


@router.delete("/shift-assignments/{id}", status_code=status.HTTP_200_OK, summary="Delete Shift Assignment")
async def delete_shift_assignment(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.ShiftAssignment).where(models.ShiftAssignment.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Shift assignment not found")
    await db.delete(item)
    await db.commit()
    return {"detail": "Shift assignment deleted successfully"}


# ═══════════════════════════════════════════════════════════
# WFH REQUESTS (POST, GET, GET/my, APPROVE, REJECT, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/wfh-requests/", response_model=schemas.WFHRequestOut, status_code=status.HTTP_201_CREATED, summary="Request Work From Home")
async def create_wfh_request(
    data: schemas.WFHRequestCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    req = models.WFHRequest(
        employee_id=current_user.id,
        date=data.date,
        reason=data.reason,
        status=models.RequestStatusEnum.pending
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return req


@router.get("/wfh-requests/", response_model=List[schemas.WFHRequestOut], summary="List WFH Requests")
async def list_wfh_requests(
    employee_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = select(models.WFHRequest)
    if employee_id:
        query = query.where(models.WFHRequest.employee_id == employee_id)
    result = await db.execute(query.order_by(models.WFHRequest.date.desc()).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/wfh-requests/my", response_model=List[schemas.WFHRequestOut], summary="My WFH Requests")
async def my_wfh_requests(
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.WFHRequest)
        .where(models.WFHRequest.employee_id == current_user.id)
        .order_by(models.WFHRequest.date.desc())
    )
    return result.scalars().all()


@router.patch("/wfh-requests/{id}/approve", response_model=schemas.WFHRequestOut, summary="Approve WFH Request")
async def approve_wfh_request(
    id: int,
    data: schemas.WFHReview,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.WFHRequest).where(models.WFHRequest.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="WFH request not found")
    item.status = models.RequestStatusEnum.approved
    item.approver_id = current_user.id
    item.approver_comment = data.approver_comment
    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/wfh-requests/{id}/reject", response_model=schemas.WFHRequestOut, summary="Reject WFH Request")
async def reject_wfh_request(
    id: int,
    data: schemas.WFHReview,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.WFHRequest).where(models.WFHRequest.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="WFH request not found")
    item.status = models.RequestStatusEnum.rejected
    item.approver_id = current_user.id
    item.approver_comment = data.approver_comment
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/wfh-requests/{id}", status_code=status.HTTP_200_OK, summary="Delete WFH Request")
async def delete_wfh_request(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.WFHRequest).where(models.WFHRequest.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="WFH request not found")
    await db.delete(item)
    await db.commit()
    return {"detail": "WFH request deleted successfully"}


# ═══════════════════════════════════════════════════════════
# ATTENDANCE SUMMARY REPORT
# ═══════════════════════════════════════════════════════════

@router.get("/summary", response_model=schemas.AttendanceSummaryOut, summary="Monthly Attendance Summary for an Employee")
async def attendance_summary(
    employee_id: Optional[int] = None,
    month: int = Query(default=date.today().month, ge=1, le=12),
    year: int = Query(default=date.today().year),
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    """Returns a summary of an employee's attendance for a given month/year."""
    eid = employee_id or current_user.id

    result = await db.execute(
        select(models.AttendanceLog).where(
            models.AttendanceLog.employee_id == eid,
            models.AttendanceLog.date >= date(year, month, 1),
        )
    )
    logs = result.scalars().all()

    import calendar
    total_days = calendar.monthrange(year, month)[1]

    summary = {
        "present": 0, "absent": 0, "late": 0,
        "half_day": 0, "on_leave": 0, "holiday": 0,
        "total_hours": 0.0
    }

    # Filter only this month
    month_logs = [l for l in logs if l.date.month == month and l.date.year == year]

    for log in month_logs:
        s = log.status.value if log.status else "present"
        if s == "present":
            summary["present"] += 1
        elif s == "absent":
            summary["absent"] += 1
        elif s == "late":
            summary["late"] += 1
        elif s == "half_day":
            summary["half_day"] += 1
        elif s == "on_leave":
            summary["on_leave"] += 1
        elif s == "holiday":
            summary["holiday"] += 1
        summary["total_hours"] += log.total_hours or 0.0

    return schemas.AttendanceSummaryOut(
        employee_id=eid,
        month=month,
        year=year,
        total_days=total_days,
        present_days=summary["present"],
        absent_days=summary["absent"],
        late_days=summary["late"],
        half_days=summary["half_day"],
        on_leave_days=summary["on_leave"],
        holiday_days=summary["holiday"],
        total_hours=round(summary["total_hours"], 2),
    )

