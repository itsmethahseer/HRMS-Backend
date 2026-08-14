from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_tenant_db_from_token, get_current_user
from app.modules.core_hr.models import User
from app.modules.helpdesk import models, schemas

router = APIRouter()


async def generate_ticket_number(db: AsyncSession) -> str:
    result = await db.execute(select(models.HelpdeskTicket))
    count = len(result.scalars().all())
    return f"TICK-{(count + 1):05d}"


# ═══════════════════════════════════════════════════════════
# TICKET CATEGORIES (GET, POST, GET/{id}, PUT, PATCH, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/categories/", response_model=schemas.TicketCategoryOut, status_code=status.HTTP_201_CREATED, summary="Create Ticket Category")
async def create_category(
    data: schemas.TicketCategoryCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    existing = await db.execute(select(models.TicketCategory).where(models.TicketCategory.name == data.name))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Ticket category with this name already exists")

    cat = models.TicketCategory(**data.model_dump())
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return cat


@router.get("/categories/", response_model=List[schemas.TicketCategoryOut], summary="List Ticket Categories")
async def list_categories(
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = select(models.TicketCategory)
    if is_active is not None:
        query = query.where(models.TicketCategory.is_active == is_active)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/categories/{id}", response_model=schemas.TicketCategoryOut, summary="Get Ticket Category by ID")
async def get_category(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.TicketCategory).where(models.TicketCategory.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Ticket category not found")
    return item


@router.put("/categories/{id}", response_model=schemas.TicketCategoryOut, summary="Update Ticket Category (Full)")
async def update_category(
    id: int,
    data: schemas.TicketCategoryCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.TicketCategory).where(models.TicketCategory.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Ticket category not found")
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/categories/{id}", response_model=schemas.TicketCategoryOut, summary="Update Ticket Category (Partial)")
async def patch_category(
    id: int,
    data: schemas.TicketCategoryUpdate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.TicketCategory).where(models.TicketCategory.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Ticket category not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/categories/{id}", status_code=status.HTTP_200_OK, summary="Delete Ticket Category")
async def delete_category(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.TicketCategory).where(models.TicketCategory.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Ticket category not found")
    await db.delete(item)
    await db.commit()
    return {"detail": "Ticket category deleted successfully"}


# ═══════════════════════════════════════════════════════════
# HELPDESK TICKETS (GET, POST, GET/my, GET/assigned-to-me, GET/{id}, PUT, PATCH, PATCH /resolve, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/tickets/", response_model=schemas.HelpdeskTicketOut, status_code=status.HTTP_201_CREATED, summary="Create Helpdesk Ticket")
async def create_ticket(
    data: schemas.HelpdeskTicketCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    ticket_no = await generate_ticket_number(db)
    cat_res = await db.execute(select(models.TicketCategory).where(models.TicketCategory.id == data.category_id))
    category = cat_res.scalars().first()

    assigned_to = category.default_assignee_id if category else None

    ticket = models.HelpdeskTicket(
        ticket_number=ticket_no,
        employee_id=current_user.id,
        category_id=data.category_id,
        priority=data.priority,
        subject=data.subject,
        description=data.description,
        attachment_url=data.attachment_url,
        assigned_to=assigned_to,
        status=models.TicketStatusEnum.open
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)

    res = await db.execute(
        select(models.HelpdeskTicket)
        .options(
            selectinload(models.HelpdeskTicket.category),
            selectinload(models.HelpdeskTicket.comments)
        )
        .where(models.HelpdeskTicket.id == ticket.id)
    )
    return res.scalars().first()


@router.get("/tickets/", response_model=List[schemas.HelpdeskTicketOut], summary="List All Tickets")
async def list_tickets(
    category_id: Optional[int] = None,
    priority: Optional[models.TicketPriorityEnum] = None,
    status_filter: Optional[models.TicketStatusEnum] = None,
    assigned_to: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = (
        select(models.HelpdeskTicket)
        .options(
            selectinload(models.HelpdeskTicket.category),
            selectinload(models.HelpdeskTicket.comments)
        )
    )
    if category_id:
        query = query.where(models.HelpdeskTicket.category_id == category_id)
    if priority:
        query = query.where(models.HelpdeskTicket.priority == priority)
    if status_filter:
        query = query.where(models.HelpdeskTicket.status == status_filter)
    if assigned_to:
        query = query.where(models.HelpdeskTicket.assigned_to == assigned_to)

    result = await db.execute(query.order_by(models.HelpdeskTicket.created_at.desc()).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/tickets/my", response_model=List[schemas.HelpdeskTicketOut], summary="My Raised Tickets")
async def get_my_tickets(
    status_filter: Optional[models.TicketStatusEnum] = None,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = (
        select(models.HelpdeskTicket)
        .options(
            selectinload(models.HelpdeskTicket.category),
            selectinload(models.HelpdeskTicket.comments)
        )
        .where(models.HelpdeskTicket.employee_id == current_user.id)
    )
    if status_filter:
        query = query.where(models.HelpdeskTicket.status == status_filter)
    query = query.order_by(models.HelpdeskTicket.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/tickets/assigned-to-me", response_model=List[schemas.HelpdeskTicketOut], summary="Tickets Assigned to Me")
async def get_assigned_tickets(
    status_filter: Optional[models.TicketStatusEnum] = None,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = (
        select(models.HelpdeskTicket)
        .options(
            selectinload(models.HelpdeskTicket.category),
            selectinload(models.HelpdeskTicket.comments)
        )
        .where(models.HelpdeskTicket.assigned_to == current_user.id)
    )
    if status_filter:
        query = query.where(models.HelpdeskTicket.status == status_filter)
    query = query.order_by(models.HelpdeskTicket.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/tickets/{id}", response_model=schemas.HelpdeskTicketOut, summary="Get Ticket by ID")
async def get_ticket(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.HelpdeskTicket)
        .options(
            selectinload(models.HelpdeskTicket.category),
            selectinload(models.HelpdeskTicket.comments)
        )
        .where(models.HelpdeskTicket.id == id)
    )
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return item


@router.put("/tickets/{id}", response_model=schemas.HelpdeskTicketOut, summary="Update Ticket (Full)")
async def update_ticket(
    id: int,
    data: schemas.HelpdeskTicketCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.HelpdeskTicket).where(models.HelpdeskTicket.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Ticket not found")

    for key, value in data.model_dump().items():
        setattr(item, key, value)

    await db.commit()
    res = await db.execute(
        select(models.HelpdeskTicket)
        .options(
            selectinload(models.HelpdeskTicket.category),
            selectinload(models.HelpdeskTicket.comments)
        )
        .where(models.HelpdeskTicket.id == item.id)
    )
    return res.scalars().first()


@router.patch("/tickets/{id}", response_model=schemas.HelpdeskTicketOut, summary="Update Ticket (Partial)")
async def patch_ticket(
    id: int,
    data: schemas.HelpdeskTicketUpdate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.HelpdeskTicket).where(models.HelpdeskTicket.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Ticket not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)

    await db.commit()
    res = await db.execute(
        select(models.HelpdeskTicket)
        .options(
            selectinload(models.HelpdeskTicket.category),
            selectinload(models.HelpdeskTicket.comments)
        )
        .where(models.HelpdeskTicket.id == item.id)
    )
    return res.scalars().first()


@router.patch("/tickets/{id}/resolve", response_model=schemas.HelpdeskTicketOut, summary="Resolve / Close Ticket")
async def resolve_ticket(
    id: int,
    data: schemas.HelpdeskTicketResolve,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.HelpdeskTicket).where(models.HelpdeskTicket.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Ticket not found")

    item.status = data.status or models.TicketStatusEnum.resolved
    item.resolution_notes = data.resolution_notes
    item.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(item)

    res = await db.execute(
        select(models.HelpdeskTicket)
        .options(
            selectinload(models.HelpdeskTicket.category),
            selectinload(models.HelpdeskTicket.comments)
        )
        .where(models.HelpdeskTicket.id == item.id)
    )
    return res.scalars().first()


@router.delete("/tickets/{id}", status_code=status.HTTP_200_OK, summary="Delete Ticket")
async def delete_ticket(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.HelpdeskTicket).where(models.HelpdeskTicket.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Ticket not found")
    await db.delete(item)
    await db.commit()
    return {"detail": "Ticket deleted successfully"}


# ═══════════════════════════════════════════════════════════
# TICKET COMMENTS (POST, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/tickets/{ticket_id}/comments/", response_model=schemas.TicketCommentOut, status_code=status.HTTP_201_CREATED, summary="Add Comment to Ticket")
async def add_comment(
    ticket_id: int,
    data: schemas.TicketCommentCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    ticket_res = await db.execute(select(models.HelpdeskTicket).where(models.HelpdeskTicket.id == ticket_id))
    if not ticket_res.scalars().first():
        raise HTTPException(status_code=404, detail="Ticket not found")

    comment = models.TicketComment(
        ticket_id=ticket_id,
        user_id=current_user.id,
        **data.model_dump()
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment


@router.delete("/comments/{id}", status_code=status.HTTP_200_OK, summary="Delete Ticket Comment")
async def delete_comment(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.TicketComment).where(models.TicketComment.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Comment not found")
    await db.delete(item)
    await db.commit()
    return {"detail": "Comment deleted successfully"}


# ═══════════════════════════════════════════════════════════
# COMPANY ANNOUNCEMENTS (GET, POST, GET/{id}, PUT, PATCH, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/announcements/", response_model=schemas.CompanyAnnouncementOut, status_code=status.HTTP_201_CREATED, summary="Create Announcement")
async def create_announcement(
    data: schemas.CompanyAnnouncementCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    ann = models.CompanyAnnouncement(
        author_id=current_user.id,
        **data.model_dump()
    )
    db.add(ann)
    await db.commit()
    await db.refresh(ann)
    return ann


@router.get("/announcements/", response_model=List[schemas.CompanyAnnouncementOut], summary="List Announcements Feed")
async def list_announcements(
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = select(models.CompanyAnnouncement)
    if is_active is not None:
        query = query.where(models.CompanyAnnouncement.is_active == is_active)
    result = await db.execute(query.order_by(models.CompanyAnnouncement.created_at.desc()).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/announcements/{id}", response_model=schemas.CompanyAnnouncementOut, summary="Get Announcement by ID")
async def get_announcement(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.CompanyAnnouncement).where(models.CompanyAnnouncement.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Announcement not found")
    return item


@router.put("/announcements/{id}", response_model=schemas.CompanyAnnouncementOut, summary="Update Announcement (Full)")
async def update_announcement(
    id: int,
    data: schemas.CompanyAnnouncementCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.CompanyAnnouncement).where(models.CompanyAnnouncement.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Announcement not found")
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/announcements/{id}", response_model=schemas.CompanyAnnouncementOut, summary="Update Announcement (Partial)")
async def patch_announcement(
    id: int,
    data: schemas.CompanyAnnouncementUpdate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.CompanyAnnouncement).where(models.CompanyAnnouncement.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Announcement not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/announcements/{id}", status_code=status.HTTP_200_OK, summary="Delete Announcement")
async def delete_announcement(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.CompanyAnnouncement).where(models.CompanyAnnouncement.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Announcement not found")
    await db.delete(item)
    await db.commit()
    return {"detail": "Announcement deleted successfully"}


# ═══════════════════════════════════════════════════════════
# PULSE SURVEYS & RESPONSES (GET, POST, GET/{id}, PUT, PATCH, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/surveys/", response_model=schemas.PulseSurveyOut, status_code=status.HTTP_201_CREATED, summary="Create Pulse Survey")
async def create_survey(
    data: schemas.PulseSurveyCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    survey = models.PulseSurvey(**data.model_dump())
    db.add(survey)
    await db.commit()
    await db.refresh(survey)
    return survey


@router.get("/surveys/", response_model=List[schemas.PulseSurveyOut], summary="List Pulse Surveys")
async def list_surveys(
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = select(models.PulseSurvey)
    if is_active is not None:
        query = query.where(models.PulseSurvey.is_active == is_active)
    result = await db.execute(query.order_by(models.PulseSurvey.start_date.desc()))
    return result.scalars().all()


@router.get("/surveys/{id}", response_model=schemas.PulseSurveyOut, summary="Get Pulse Survey by ID")
async def get_survey(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.PulseSurvey).where(models.PulseSurvey.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Survey not found")
    return item


@router.put("/surveys/{id}", response_model=schemas.PulseSurveyOut, summary="Update Pulse Survey (Full)")
async def update_survey(
    id: int,
    data: schemas.PulseSurveyCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.PulseSurvey).where(models.PulseSurvey.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Survey not found")
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/surveys/{id}", response_model=schemas.PulseSurveyOut, summary="Update Pulse Survey (Partial)")
async def patch_survey(
    id: int,
    data: schemas.PulseSurveyUpdate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.PulseSurvey).where(models.PulseSurvey.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Survey not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/surveys/{id}", status_code=status.HTTP_200_OK, summary="Delete Pulse Survey")
async def delete_survey(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.PulseSurvey).where(models.PulseSurvey.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Survey not found")
    await db.delete(item)
    await db.commit()
    return {"detail": "Survey deleted successfully"}


@router.post("/surveys/responses/", response_model=schemas.SurveyResponseOut, status_code=status.HTTP_201_CREATED, summary="Submit Survey Response")
async def submit_response(
    data: schemas.SurveyResponseCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    survey_res = await db.execute(select(models.PulseSurvey).where(models.PulseSurvey.id == data.survey_id))
    survey = survey_res.scalars().first()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")

    resp = models.SurveyResponse(
        survey_id=data.survey_id,
        employee_id=None if survey.is_anonymous else current_user.id,
        answers_json=data.answers_json
    )
    db.add(resp)
    await db.commit()
    await db.refresh(resp)
    return resp


@router.get("/surveys/{survey_id}/responses", response_model=List[schemas.SurveyResponseOut], summary="Get Survey Responses")
async def get_survey_responses(
    survey_id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.SurveyResponse).where(models.SurveyResponse.survey_id == survey_id))
    return result.scalars().all()
