import enum
from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey,
    DateTime, Date, Float, Text, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base


class JobStatusEnum(str, enum.Enum):
    draft = "draft"
    open = "open"
    closed = "closed"
    on_hold = "on_hold"


class CandidateStatusEnum(str, enum.Enum):
    applied = "applied"
    screening = "screening"
    shortlisted = "shortlisted"
    interviewing = "interviewing"
    offered = "offered"
    hired = "hired"
    rejected = "rejected"


class InterviewTypeEnum(str, enum.Enum):
    screening = "screening"
    technical = "technical"
    hr = "hr"
    managerial = "managerial"


class InterviewStatusEnum(str, enum.Enum):
    scheduled = "scheduled"
    completed = "completed"
    cancelled = "cancelled"


class OfferStatusEnum(str, enum.Enum):
    draft = "draft"
    sent = "sent"
    accepted = "accepted"
    declined = "declined"
    expired = "expired"


class JobPosting(Base):
    __tablename__ = "job_postings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    code = Column(String(30), unique=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    location = Column(String, nullable=True)
    employment_type = Column(String, default="full_time")  # full_time, contract, intern
    experience_level = Column(String, nullable=True)       # Entry, Mid, Senior, Lead
    min_salary = Column(Float, nullable=True)
    max_salary = Column(Float, nullable=True)

    description = Column(Text, nullable=False)
    requirements = Column(Text, nullable=True)
    openings_count = Column(Integer, default=1)

    status = Column(SAEnum(JobStatusEnum, name="jobstatusenum", create_type=False), default=JobStatusEnum.draft)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    department = relationship("Department")
    creator = relationship("User", foreign_keys=[created_by])
    candidates = relationship("Candidate", back_populates="job", cascade="all, delete-orphan")


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("job_postings.id"), nullable=False, index=True)

    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    resume_url = Column(String, nullable=True)
    portfolio_url = Column(String, nullable=True)

    current_company = Column(String, nullable=True)
    current_ctc = Column(Float, nullable=True)
    expected_ctc = Column(Float, nullable=True)
    notice_period_days = Column(Integer, default=30)
    experience_years = Column(Float, default=0.0)

    status = Column(SAEnum(CandidateStatusEnum, name="candidatestatusenum", create_type=False), default=CandidateStatusEnum.applied)
    rejection_reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    job = relationship("JobPosting", back_populates="candidates")
    interviews = relationship("Interview", back_populates="candidate", cascade="all, delete-orphan")
    offers = relationship("JobOffer", back_populates="candidate", cascade="all, delete-orphan")


class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False, index=True)
    interviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    interview_type = Column(SAEnum(InterviewTypeEnum, name="interviewtypeenum", create_type=False), default=InterviewTypeEnum.technical)
    scheduled_time = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer, default=45)
    meeting_link = Column(String, nullable=True)

    feedback = Column(Text, nullable=True)
    score = Column(Float, nullable=True)  # 1-10
    status = Column(SAEnum(InterviewStatusEnum, name="interviewstatusenum", create_type=False), default=InterviewStatusEnum.scheduled)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    candidate = relationship("Candidate", back_populates="interviews")
    interviewer = relationship("User", foreign_keys=[interviewer_id])


class JobOffer(Base):
    __tablename__ = "job_offers"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("job_postings.id"), nullable=False)

    offered_ctc = Column(Float, nullable=False)
    joining_date = Column(Date, nullable=False)
    offer_letter_url = Column(String, nullable=True)
    validity_date = Column(Date, nullable=True)

    status = Column(SAEnum(OfferStatusEnum, name="offerstatusenum", create_type=False), default=OfferStatusEnum.draft)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    candidate = relationship("Candidate", back_populates="offers")
    job = relationship("JobPosting", foreign_keys=[job_id])
