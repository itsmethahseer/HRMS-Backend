from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, date
from app.modules.recruitment.models import (
    JobStatusEnum, CandidateStatusEnum, InterviewTypeEnum,
    InterviewStatusEnum, OfferStatusEnum
)


# --- Job Posting Schemas ---
class JobPostingBase(BaseModel):
    title: str
    code: Optional[str] = None
    department_id: Optional[int] = None
    location: Optional[str] = None
    employment_type: Optional[str] = "full_time"
    experience_level: Optional[str] = None
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None
    description: str
    requirements: Optional[str] = None
    openings_count: Optional[int] = 1
    status: Optional[JobStatusEnum] = JobStatusEnum.draft


class JobPostingCreate(JobPostingBase):
    pass


class JobPostingUpdate(BaseModel):
    title: Optional[str] = None
    code: Optional[str] = None
    department_id: Optional[int] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    experience_level: Optional[str] = None
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    openings_count: Optional[int] = None
    status: Optional[JobStatusEnum] = None


class JobPostingOut(JobPostingBase):
    id: int
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Candidate Schemas ---
class CandidateBase(BaseModel):
    job_id: int
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    resume_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    current_company: Optional[str] = None
    current_ctc: Optional[float] = None
    expected_ctc: Optional[float] = None
    notice_period_days: Optional[int] = 30
    experience_years: Optional[float] = 0.0
    status: Optional[CandidateStatusEnum] = CandidateStatusEnum.applied


class CandidateCreate(CandidateBase):
    pass


class CandidateUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    resume_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    current_company: Optional[str] = None
    current_ctc: Optional[float] = None
    expected_ctc: Optional[float] = None
    notice_period_days: Optional[int] = None
    experience_years: Optional[float] = None
    status: Optional[CandidateStatusEnum] = None
    rejection_reason: Optional[str] = None


class CandidateOut(CandidateBase):
    id: int
    rejection_reason: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Interview Schemas ---
class InterviewBase(BaseModel):
    candidate_id: int
    interviewer_id: int
    interview_type: Optional[InterviewTypeEnum] = InterviewTypeEnum.technical
    scheduled_time: datetime
    duration_minutes: Optional[int] = 45
    meeting_link: Optional[str] = None


class InterviewCreate(InterviewBase):
    pass


class InterviewFeedback(BaseModel):
    feedback: str
    score: float
    status: Optional[InterviewStatusEnum] = InterviewStatusEnum.completed


class InterviewOut(InterviewBase):
    id: int
    feedback: Optional[str] = None
    score: Optional[float] = None
    status: InterviewStatusEnum
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Job Offer Schemas ---
class JobOfferBase(BaseModel):
    candidate_id: int
    job_id: int
    offered_ctc: float
    joining_date: date
    offer_letter_url: Optional[str] = None
    validity_date: Optional[date] = None


class JobOfferCreate(JobOfferBase):
    pass


class JobOfferUpdate(BaseModel):
    status: OfferStatusEnum


class JobOfferOut(JobOfferBase):
    id: int
    status: OfferStatusEnum
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Conversion Schema ---
class ConvertCandidateRequest(BaseModel):
    password: str
    department_id: Optional[int] = None
    job_title: Optional[str] = None
