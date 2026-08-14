from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_tenant_db_from_token, get_current_user
from app.modules.core_hr.models import User
from app.modules.pms import models, schemas

router = APIRouter()


# ═══════════════════════════════════════════════════════════
# GOALS & OKRs (GET, POST, GET/{id}, PUT, PATCH, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/goals/", response_model=schemas.GoalOut, status_code=status.HTTP_201_CREATED, summary="Create Goal / OKR")
async def create_goal(
    data: schemas.GoalCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    target_emp_id = data.employee_id or current_user.id
    goal = models.Goal(
        employee_id=target_emp_id,
        title=data.title,
        description=data.description,
        category=data.category,
        start_date=data.start_date,
        due_date=data.due_date,
        target_value=data.target_value,
        current_value=data.current_value,
        metric_unit=data.metric_unit,
        progress_percentage=data.progress_percentage,
        weightage=data.weightage,
        status=data.status
    )
    db.add(goal)
    await db.commit()
    await db.refresh(goal)

    if data.key_results:
        for kr in data.key_results:
            db_kr = models.KeyResult(
                goal_id=goal.id,
                title=kr.title,
                target_value=kr.target_value,
                current_value=kr.current_value,
                metric_unit=kr.metric_unit,
                progress_percentage=kr.progress_percentage,
                weightage=kr.weightage
            )
            db.add(db_kr)
        await db.commit()

    res = await db.execute(
        select(models.Goal).options(selectinload(models.Goal.key_results)).where(models.Goal.id == goal.id)
    )
    return res.scalars().first()


@router.get("/goals/", response_model=List[schemas.GoalOut], summary="List Goals")
async def list_goals(
    employee_id: Optional[int] = None,
    category: Optional[models.GoalCategoryEnum] = None,
    status_filter: Optional[models.GoalStatusEnum] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = select(models.Goal).options(selectinload(models.Goal.key_results))
    if employee_id:
        query = query.where(models.Goal.employee_id == employee_id)
    if category:
        query = query.where(models.Goal.category == category)
    if status_filter:
        query = query.where(models.Goal.status == status_filter)

    result = await db.execute(query.order_by(models.Goal.due_date.asc()).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/goals/my", response_model=List[schemas.GoalOut], summary="My Goals")
async def get_my_goals(
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.Goal)
        .options(selectinload(models.Goal.key_results))
        .where(models.Goal.employee_id == current_user.id)
        .order_by(models.Goal.due_date.asc())
    )
    return result.scalars().all()


@router.get("/goals/{id}", response_model=schemas.GoalOut, summary="Get Goal by ID")
async def get_goal(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.Goal).options(selectinload(models.Goal.key_results)).where(models.Goal.id == id)
    )
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Goal not found")
    return item


@router.put("/goals/{id}", response_model=schemas.GoalOut, summary="Update Goal (Full)")
async def update_goal(
    id: int,
    data: schemas.GoalCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.Goal).where(models.Goal.id == id))
    goal = result.scalars().first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    goal.title = data.title
    goal.description = data.description
    goal.category = data.category
    goal.start_date = data.start_date
    goal.due_date = data.due_date
    goal.target_value = data.target_value
    goal.current_value = data.current_value
    goal.metric_unit = data.metric_unit
    goal.progress_percentage = data.progress_percentage
    goal.weightage = data.weightage
    goal.status = data.status

    await db.commit()
    res = await db.execute(
        select(models.Goal).options(selectinload(models.Goal.key_results)).where(models.Goal.id == id)
    )
    return res.scalars().first()


@router.patch("/goals/{id}", response_model=schemas.GoalOut, summary="Update Goal (Partial)")
async def patch_goal(
    id: int,
    data: schemas.GoalUpdate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.Goal).where(models.Goal.id == id))
    goal = result.scalars().first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(goal, key, value)

    await db.commit()
    res = await db.execute(
        select(models.Goal).options(selectinload(models.Goal.key_results)).where(models.Goal.id == id)
    )
    return res.scalars().first()


@router.delete("/goals/{id}", status_code=status.HTTP_200_OK, summary="Delete Goal")
async def delete_goal(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.Goal).where(models.Goal.id == id))
    goal = result.scalars().first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    await db.delete(goal)
    await db.commit()
    return {"detail": "Goal deleted successfully"}


# ═══════════════════════════════════════════════════════════
# KEY RESULTS (GET, POST, GET/{id}, PUT, PATCH, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/goals/{goal_id}/key-results/", response_model=schemas.KeyResultOut, status_code=status.HTTP_201_CREATED, summary="Add Key Result to Goal")
async def create_key_result(
    goal_id: int,
    data: schemas.KeyResultCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    goal_res = await db.execute(select(models.Goal).where(models.Goal.id == goal_id))
    if not goal_res.scalars().first():
        raise HTTPException(status_code=404, detail="Goal not found")

    kr = models.KeyResult(goal_id=goal_id, **data.model_dump())
    db.add(kr)
    await db.commit()
    await db.refresh(kr)
    return kr


@router.patch("/key-results/{id}", response_model=schemas.KeyResultOut, summary="Update Key Result")
async def patch_key_result(
    id: int,
    data: schemas.KeyResultUpdate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.KeyResult).where(models.KeyResult.id == id))
    kr = result.scalars().first()
    if not kr:
        raise HTTPException(status_code=404, detail="Key result not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(kr, key, value)

    await db.commit()
    await db.refresh(kr)
    return kr


@router.delete("/key-results/{id}", status_code=status.HTTP_200_OK, summary="Delete Key Result")
async def delete_key_result(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.KeyResult).where(models.KeyResult.id == id))
    kr = result.scalars().first()
    if not kr:
        raise HTTPException(status_code=404, detail="Key result not found")
    await db.delete(kr)
    await db.commit()
    return {"detail": "Key result deleted successfully"}


# ═══════════════════════════════════════════════════════════
# REVIEW CYCLES (GET, POST, GET/{id}, PUT, PATCH, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/review-cycles/", response_model=schemas.ReviewCycleOut, status_code=status.HTTP_201_CREATED, summary="Create Review Cycle")
async def create_review_cycle(
    data: schemas.ReviewCycleCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    existing = await db.execute(select(models.ReviewCycle).where(models.ReviewCycle.title == data.title))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Review cycle with this title already exists")

    cycle = models.ReviewCycle(**data.model_dump())
    db.add(cycle)
    await db.commit()
    await db.refresh(cycle)
    return cycle


@router.get("/review-cycles/", response_model=List[schemas.ReviewCycleOut], summary="List Review Cycles")
async def list_review_cycles(
    status_filter: Optional[models.ReviewCycleStatusEnum] = None,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = select(models.ReviewCycle)
    if status_filter:
        query = query.where(models.ReviewCycle.status == status_filter)
    result = await db.execute(query.order_by(models.ReviewCycle.start_date.desc()))
    return result.scalars().all()


@router.get("/review-cycles/{id}", response_model=schemas.ReviewCycleOut, summary="Get Review Cycle by ID")
async def get_review_cycle(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.ReviewCycle).where(models.ReviewCycle.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Review cycle not found")
    return item


@router.put("/review-cycles/{id}", response_model=schemas.ReviewCycleOut, summary="Update Review Cycle (Full)")
async def update_review_cycle(
    id: int,
    data: schemas.ReviewCycleCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.ReviewCycle).where(models.ReviewCycle.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Review cycle not found")
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/review-cycles/{id}", response_model=schemas.ReviewCycleOut, summary="Update Review Cycle (Partial)")
async def patch_review_cycle(
    id: int,
    data: schemas.ReviewCycleUpdate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.ReviewCycle).where(models.ReviewCycle.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Review cycle not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/review-cycles/{id}", status_code=status.HTTP_200_OK, summary="Delete Review Cycle")
async def delete_review_cycle(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.ReviewCycle).where(models.ReviewCycle.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Review cycle not found")
    await db.delete(item)
    await db.commit()
    return {"detail": "Review cycle deleted successfully"}


# ═══════════════════════════════════════════════════════════
# PERFORMANCE REVIEWS (GET, POST, GET/my, GET/assigned-to-me, PATCH /submit, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/reviews/", response_model=schemas.PerformanceReviewOut, status_code=status.HTTP_201_CREATED, summary="Initiate Performance Review")
async def create_review(
    data: schemas.PerformanceReviewCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    review = models.PerformanceReview(**data.model_dump())
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return review


@router.get("/reviews/", response_model=List[schemas.PerformanceReviewOut], summary="List Performance Reviews")
async def list_reviews(
    cycle_id: Optional[int] = None,
    employee_id: Optional[int] = None,
    status_filter: Optional[models.ReviewStatusEnum] = None,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = select(models.PerformanceReview)
    if cycle_id:
        query = query.where(models.PerformanceReview.cycle_id == cycle_id)
    if employee_id:
        query = query.where(models.PerformanceReview.employee_id == employee_id)
    if status_filter:
        query = query.where(models.PerformanceReview.status == status_filter)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/reviews/my", response_model=List[schemas.PerformanceReviewOut], summary="My Performance Reviews (As Subject)")
async def get_my_reviews(
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.PerformanceReview).where(models.PerformanceReview.employee_id == current_user.id)
    )
    return result.scalars().all()


@router.get("/reviews/assigned-to-me", response_model=List[schemas.PerformanceReviewOut], summary="Reviews Assigned to Me (As Evaluator)")
async def get_assigned_reviews(
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.PerformanceReview).where(models.PerformanceReview.reviewer_id == current_user.id)
    )
    return result.scalars().all()


@router.get("/reviews/{id}", response_model=schemas.PerformanceReviewOut, summary="Get Performance Review by ID")
async def get_review(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.PerformanceReview).where(models.PerformanceReview.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Performance review not found")
    return item


@router.patch("/reviews/{id}/submit", response_model=schemas.PerformanceReviewOut, summary="Submit Performance Evaluation")
async def submit_review(
    id: int,
    data: schemas.PerformanceReviewSubmit,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.PerformanceReview).where(models.PerformanceReview.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Performance review not found")

    item.ratings_json = data.ratings_json
    item.comments = data.comments
    item.strengths = data.strengths
    item.areas_for_improvement = data.areas_for_improvement
    item.overall_score = data.overall_score
    item.status = models.ReviewStatusEnum.submitted
    item.submitted_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/reviews/{id}", status_code=status.HTTP_200_OK, summary="Delete Performance Review")
async def delete_review(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.PerformanceReview).where(models.PerformanceReview.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Performance review not found")
    await db.delete(item)
    await db.commit()
    return {"detail": "Performance review deleted successfully"}


# ═══════════════════════════════════════════════════════════
# 1-ON-1 MEETINGS (GET, POST, GET/{id}, PUT, PATCH, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/one-on-ones/", response_model=schemas.OneOnOneMeetingOut, status_code=status.HTTP_201_CREATED, summary="Schedule 1-on-1 Meeting")
async def create_meeting(
    data: schemas.OneOnOneMeetingCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    meeting = models.OneOnOneMeeting(
        manager_id=current_user.id,
        **data.model_dump(),
        status=models.MeetingStatusEnum.scheduled
    )
    db.add(meeting)
    await db.commit()
    await db.refresh(meeting)
    return meeting


@router.get("/one-on-ones/", response_model=List[schemas.OneOnOneMeetingOut], summary="List 1-on-1 Meetings")
async def list_meetings(
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = (
        select(models.OneOnOneMeeting)
        .where((models.OneOnOneMeeting.manager_id == current_user.id) | (models.OneOnOneMeeting.employee_id == current_user.id))
        .order_by(models.OneOnOneMeeting.scheduled_at.desc())
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/one-on-ones/{id}", response_model=schemas.OneOnOneMeetingOut, summary="Get 1-on-1 Meeting by ID")
async def get_meeting(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.OneOnOneMeeting).where(models.OneOnOneMeeting.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="1-on-1 meeting not found")
    return item


@router.patch("/one-on-ones/{id}", response_model=schemas.OneOnOneMeetingOut, summary="Update 1-on-1 Meeting")
async def patch_meeting(
    id: int,
    data: schemas.OneOnOneMeetingUpdate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.OneOnOneMeeting).where(models.OneOnOneMeeting.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="1-on-1 meeting not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)

    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/one-on-ones/{id}", status_code=status.HTTP_200_OK, summary="Delete 1-on-1 Meeting")
async def delete_meeting(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.OneOnOneMeeting).where(models.OneOnOneMeeting.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="1-on-1 meeting not found")
    await db.delete(item)
    await db.commit()
    return {"detail": "1-on-1 meeting deleted successfully"}


# ═══════════════════════════════════════════════════════════
# PEER APPRECIATIONS / BADGES (GET, POST, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/appreciations/", response_model=schemas.PeerAppreciationOut, status_code=status.HTTP_201_CREATED, summary="Give Peer Appreciation / Badge")
async def create_appreciation(
    data: schemas.PeerAppreciationCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    appr = models.PeerAppreciation(
        sender_id=current_user.id,
        recipient_id=data.recipient_id,
        badge_name=data.badge_name,
        message=data.message
    )
    db.add(appr)
    await db.commit()
    await db.refresh(appr)
    return appr


@router.get("/appreciations/", response_model=List[schemas.PeerAppreciationOut], summary="List Peer Appreciations Feed")
async def list_appreciations(
    recipient_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = select(models.PeerAppreciation)
    if recipient_id:
        query = query.where(models.PeerAppreciation.recipient_id == recipient_id)
    query = query.order_by(models.PeerAppreciation.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.delete("/appreciations/{id}", status_code=status.HTTP_200_OK, summary="Delete Appreciation")
async def delete_appreciation(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.PeerAppreciation).where(models.PeerAppreciation.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Appreciation not found")
    await db.delete(item)
    await db.commit()
    return {"detail": "Appreciation deleted successfully"}
