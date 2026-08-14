from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.dependencies import get_tenant_db_from_token, get_current_user
from app.modules.core_hr.models import User
from app.modules.employee_profile.models import EmployeeProfile
from app.modules.recruitment import models, schemas
from app.core.security import get_password_hash

router = APIRouter()


# ═══════════════════════════════════════════════════════════
# JOB POSTINGS (GET, POST, GET/{id}, PUT, PATCH, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/jobs/", response_model=schemas.JobPostingOut, status_code=status.HTTP_201_CREATED, summary="Create Job Posting")
async def create_job(
    data: schemas.JobPostingCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    job = models.JobPosting(
        **data.model_dump(),
        created_by=current_user.id
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


@router.get("/jobs/", response_model=List[schemas.JobPostingOut], summary="List Job Postings")
async def list_jobs(
    department_id: Optional[int] = None,
    status_filter: Optional[models.JobStatusEnum] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = select(models.JobPosting)
    if department_id:
        query = query.where(models.JobPosting.department_id == department_id)
    if status_filter:
        query = query.where(models.JobPosting.status == status_filter)
    result = await db.execute(query.order_by(models.JobPosting.created_at.desc()).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/jobs/{id}", response_model=schemas.JobPostingOut, summary="Get Job Posting by ID")
async def get_job(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.JobPosting).where(models.JobPosting.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Job posting not found")
    return item


@router.put("/jobs/{id}", response_model=schemas.JobPostingOut, summary="Update Job Posting (Full)")
async def update_job(
    id: int,
    data: schemas.JobPostingCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.JobPosting).where(models.JobPosting.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Job posting not found")
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/jobs/{id}", response_model=schemas.JobPostingOut, summary="Update Job Posting (Partial)")
async def patch_job(
    id: int,
    data: schemas.JobPostingUpdate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.JobPosting).where(models.JobPosting.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Job posting not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/jobs/{id}", status_code=status.HTTP_200_OK, summary="Delete Job Posting")
async def delete_job(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.JobPosting).where(models.JobPosting.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Job posting not found")
    await db.delete(item)
    await db.commit()
    return {"detail": "Job posting deleted successfully"}


# ═══════════════════════════════════════════════════════════
# CANDIDATES (GET, POST, GET/{id}, PUT, PATCH, CONVERT-TO-EMPLOYEE, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/candidates/", response_model=schemas.CandidateOut, status_code=status.HTTP_201_CREATED, summary="Add Candidate")
async def create_candidate(
    data: schemas.CandidateCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    cand = models.Candidate(**data.model_dump())
    db.add(cand)
    await db.commit()
    await db.refresh(cand)
    return cand


@router.get("/candidates/", response_model=List[schemas.CandidateOut], summary="List Candidates")
async def list_candidates(
    job_id: Optional[int] = None,
    status_filter: Optional[models.CandidateStatusEnum] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = select(models.Candidate)
    if job_id:
        query = query.where(models.Candidate.job_id == job_id)
    if status_filter:
        query = query.where(models.Candidate.status == status_filter)
    result = await db.execute(query.order_by(models.Candidate.created_at.desc()).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/candidates/{id}", response_model=schemas.CandidateOut, summary="Get Candidate by ID")
async def get_candidate(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.Candidate).where(models.Candidate.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return item


@router.put("/candidates/{id}", response_model=schemas.CandidateOut, summary="Update Candidate (Full)")
async def update_candidate(
    id: int,
    data: schemas.CandidateCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.Candidate).where(models.Candidate.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Candidate not found")
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/candidates/{id}", response_model=schemas.CandidateOut, summary="Update Candidate Stage / Details (Partial)")
async def patch_candidate(
    id: int,
    data: schemas.CandidateUpdate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.Candidate).where(models.Candidate.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Candidate not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.post("/candidates/{id}/convert-to-employee", summary="Convert Hired Candidate to Employee User")
async def convert_candidate(
    id: int,
    data: schemas.ConvertCandidateRequest,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.Candidate).where(models.Candidate.id == id))
    candidate = result.scalars().first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Check if user with email already exists
    user_res = await db.execute(select(User).where(User.email == candidate.email))
    if user_res.scalars().first():
        raise HTTPException(status_code=400, detail="User with this candidate's email already exists")

    hashed_pw = get_password_hash(data.password)
    user = User(
        email=candidate.email,
        hashed_password=hashed_pw,
        first_name=candidate.first_name,
        last_name=candidate.last_name,
        phone_number=candidate.phone,
        department_id=data.department_id,
        job_title=data.job_title,
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create basic profile
    profile = EmployeeProfile(
        user_id=user.id,
        phone_number=candidate.phone,
        personal_email=candidate.email
    )
    db.add(profile)

    candidate.status = models.CandidateStatusEnum.hired
    await db.commit()

    return {"message": "Candidate successfully converted to Employee", "user_id": user.id, "email": user.email}


@router.delete("/candidates/{id}", status_code=status.HTTP_200_OK, summary="Delete Candidate")
async def delete_candidate(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.Candidate).where(models.Candidate.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Candidate not found")
    await db.delete(item)
    await db.commit()
    return {"detail": "Candidate deleted successfully"}


# ═══════════════════════════════════════════════════════════
# INTERVIEWS (GET, POST, GET/{id}, PATCH FEEDBACK, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/interviews/", response_model=schemas.InterviewOut, status_code=status.HTTP_201_CREATED, summary="Schedule Interview")
async def create_interview(
    data: schemas.InterviewCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    interview = models.Interview(**data.model_dump())
    db.add(interview)
    await db.commit()
    await db.refresh(interview)
    return interview


@router.get("/interviews/", response_model=List[schemas.InterviewOut], summary="List Interviews")
async def list_interviews(
    candidate_id: Optional[int] = None,
    interviewer_id: Optional[int] = None,
    status_filter: Optional[models.InterviewStatusEnum] = None,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = select(models.Interview)
    if candidate_id:
        query = query.where(models.Interview.candidate_id == candidate_id)
    if interviewer_id:
        query = query.where(models.Interview.interviewer_id == interviewer_id)
    if status_filter:
        query = query.where(models.Interview.status == status_filter)
    result = await db.execute(query.order_by(models.Interview.scheduled_time.asc()))
    return result.scalars().all()


@router.get("/interviews/{id}", response_model=schemas.InterviewOut, summary="Get Interview by ID")
async def get_interview(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.Interview).where(models.Interview.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Interview not found")
    return item


@router.patch("/interviews/{id}/feedback", response_model=schemas.InterviewOut, summary="Submit Interview Feedback")
async def submit_interview_feedback(
    id: int,
    data: schemas.InterviewFeedback,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.Interview).where(models.Interview.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Interview not found")

    item.feedback = data.feedback
    item.score = data.score
    item.status = data.status or models.InterviewStatusEnum.completed
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/interviews/{id}", status_code=status.HTTP_200_OK, summary="Delete Interview")
async def delete_interview(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.Interview).where(models.Interview.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Interview not found")
    await db.delete(item)
    await db.commit()
    return {"detail": "Interview deleted successfully"}


# ═══════════════════════════════════════════════════════════
# JOB OFFERS (GET, POST, GET/{id}, PATCH STATUS, DELETE)
# ═══════════════════════════════════════════════════════════

@router.post("/offers/", response_model=schemas.JobOfferOut, status_code=status.HTTP_201_CREATED, summary="Create Job Offer")
async def create_offer(
    data: schemas.JobOfferCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    offer = models.JobOffer(**data.model_dump(), status=models.OfferStatusEnum.draft)
    db.add(offer)
    await db.commit()
    await db.refresh(offer)
    return offer


@router.get("/offers/", response_model=List[schemas.JobOfferOut], summary="List Job Offers")
async def list_offers(
    job_id: Optional[int] = None,
    status_filter: Optional[models.OfferStatusEnum] = None,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    query = select(models.JobOffer)
    if job_id:
        query = query.where(models.JobOffer.job_id == job_id)
    if status_filter:
        query = query.where(models.JobOffer.status == status_filter)
    result = await db.execute(query.order_by(models.JobOffer.created_at.desc()))
    return result.scalars().all()


@router.get("/offers/{id}", response_model=schemas.JobOfferOut, summary="Get Job Offer by ID")
async def get_offer(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.JobOffer).where(models.JobOffer.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Job offer not found")
    return item


@router.patch("/offers/{id}/status", response_model=schemas.JobOfferOut, summary="Update Job Offer Status (Send/Accept/Decline)")
async def update_offer_status(
    id: int,
    data: schemas.JobOfferUpdate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.JobOffer).where(models.JobOffer.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Job offer not found")

    item.status = data.status
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/offers/{id}", status_code=status.HTTP_200_OK, summary="Delete Job Offer")
async def delete_offer(
    id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(models.JobOffer).where(models.JobOffer.id == id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Job offer not found")
    await db.delete(item)
    await db.commit()
    return {"detail": "Job offer deleted successfully"}
