from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.core.dependencies import get_tenant_db_from_token, get_current_user
from app.modules.core_hr.models import User
from app.modules.notifications import models, schemas

router = APIRouter()


@router.post("/", response_model=schemas.NotificationOut, status_code=status.HTTP_201_CREATED, summary="Create Notification (Admin/System)")
async def create_notification(
    data: schemas.NotificationCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    """Create a notification for a recipient. Usually called internally by other modules."""
    notif = models.Notification(
        recipient_id=data.recipient_id,
        sender_id=current_user.id,
        title=data.title,
        message=data.message,
        notification_type=data.notification_type,
        link=data.link,
    )
    db.add(notif)
    await db.commit()
    await db.refresh(notif)
    return notif


@router.get("/my", response_model=List[schemas.NotificationOut], summary="My Notification Inbox")
async def get_my_notifications(
    unread_only: bool = False,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    """Returns all notifications for the logged-in user."""
    query = select(models.Notification).where(models.Notification.recipient_id == current_user.id)
    if unread_only:
        query = query.where(models.Notification.is_read == False)
    query = query.order_by(models.Notification.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/my/summary", response_model=schemas.NotificationSummary, summary="My Notification Count Summary")
async def get_notification_summary(
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    total_res = await db.execute(
        select(func.count()).where(models.Notification.recipient_id == current_user.id)
    )
    unread_res = await db.execute(
        select(func.count()).where(
            models.Notification.recipient_id == current_user.id,
            models.Notification.is_read == False
        )
    )
    return schemas.NotificationSummary(
        total=total_res.scalar() or 0,
        unread=unread_res.scalar() or 0,
    )


@router.patch("/my/mark-all-read", summary="Mark All My Notifications as Read")
async def mark_all_read(
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.Notification).where(
            models.Notification.recipient_id == current_user.id,
            models.Notification.is_read == False
        )
    )
    for notif in result.scalars().all():
        notif.is_read = True
    await db.commit()
    return {"detail": "All notifications marked as read"}


@router.patch("/{id}/read", response_model=schemas.NotificationOut, summary="Mark Notification as Read")
async def mark_notification_read(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.Notification).where(
            models.Notification.id == id,
            models.Notification.recipient_id == current_user.id
        )
    )
    notif = result.scalars().first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    await db.commit()
    await db.refresh(notif)
    return notif


@router.delete("/{id}", status_code=status.HTTP_200_OK, summary="Delete Notification")
async def delete_notification(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.Notification).where(
            models.Notification.id == id,
            models.Notification.recipient_id == current_user.id
        )
    )
    notif = result.scalars().first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    await db.delete(notif)
    await db.commit()
    return {"detail": "Notification deleted successfully"}
