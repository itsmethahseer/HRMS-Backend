import enum
from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey,
    DateTime, Date, Float, Text, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base


class GoalCategoryEnum(str, enum.Enum):
    individual = "individual"
    department = "department"
    company = "company"


class GoalStatusEnum(str, enum.Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"
    deferred = "deferred"


class ReviewCycleTypeEnum(str, enum.Enum):
    quarterly = "quarterly"
    semi_annual = "semi_annual"
    annual = "annual"
    probation = "probation"


class ReviewCycleStatusEnum(str, enum.Enum):
    draft = "draft"
    active = "active"
    evaluation = "evaluation"
    closed = "closed"


class ReviewerTypeEnum(str, enum.Enum):
    self_eval = "self"
    manager = "manager"
    peer = "peer"
    subordinate = "subordinate"


class ReviewStatusEnum(str, enum.Enum):
    pending = "pending"
    submitted = "submitted"
    finalized = "finalized"


class MeetingStatusEnum(str, enum.Enum):
    scheduled = "scheduled"
    completed = "completed"
    cancelled = "cancelled"


class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(SAEnum(GoalCategoryEnum, name="goalcategoryenum", create_type=False), default=GoalCategoryEnum.individual)

    start_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)

    target_value = Column(Float, default=100.0)
    current_value = Column(Float, default=0.0)
    metric_unit = Column(String(20), default="%")  # %, score, units, revenue
    progress_percentage = Column(Float, default=0.0)
    weightage = Column(Float, default=1.0)

    status = Column(SAEnum(GoalStatusEnum, name="goalstatusenum", create_type=False), default=GoalStatusEnum.not_started)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    employee = relationship("User", foreign_keys=[employee_id])
    key_results = relationship("KeyResult", back_populates="goal", cascade="all, delete-orphan")


class KeyResult(Base):
    __tablename__ = "key_results"

    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey("goals.id"), nullable=False, index=True)

    title = Column(String, nullable=False)
    target_value = Column(Float, default=100.0)
    current_value = Column(Float, default=0.0)
    metric_unit = Column(String(20), default="%")
    progress_percentage = Column(Float, default=0.0)
    weightage = Column(Float, default=1.0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    goal = relationship("Goal", back_populates="key_results")


class ReviewCycle(Base):
    __tablename__ = "review_cycles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, unique=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    review_type = Column(SAEnum(ReviewCycleTypeEnum, name="reviewcycletypeenum", create_type=False), default=ReviewCycleTypeEnum.annual)
    status = Column(SAEnum(ReviewCycleStatusEnum, name="reviewcyclestatusenum", create_type=False), default=ReviewCycleStatusEnum.draft)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    reviews = relationship("PerformanceReview", back_populates="cycle", cascade="all, delete-orphan")


class PerformanceReview(Base):
    __tablename__ = "performance_reviews"

    id = Column(Integer, primary_key=True, index=True)
    cycle_id = Column(Integer, ForeignKey("review_cycles.id"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    reviewer_type = Column(SAEnum(ReviewerTypeEnum, name="reviewertypeenum", create_type=False), default=ReviewerTypeEnum.self_eval)
    ratings_json = Column(Text, nullable=True)  # JSON rating metrics
    comments = Column(Text, nullable=True)
    strengths = Column(Text, nullable=True)
    areas_for_improvement = Column(Text, nullable=True)
    overall_score = Column(Float, default=0.0)  # 1.0 to 5.0 scale

    status = Column(SAEnum(ReviewStatusEnum, name="reviewstatusenum", create_type=False), default=ReviewStatusEnum.pending)

    submitted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    cycle = relationship("ReviewCycle", back_populates="reviews")
    employee = relationship("User", foreign_keys=[employee_id])
    reviewer = relationship("User", foreign_keys=[reviewer_id])


class OneOnOneMeeting(Base):
    __tablename__ = "one_on_one_meetings"

    id = Column(Integer, primary_key=True, index=True)
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer, default=30)
    agenda = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    action_items = Column(Text, nullable=True)

    status = Column(SAEnum(MeetingStatusEnum, name="meetingstatusenum", create_type=False), default=MeetingStatusEnum.scheduled)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    manager = relationship("User", foreign_keys=[manager_id])
    employee = relationship("User", foreign_keys=[employee_id])


class PeerAppreciation(Base):
    __tablename__ = "peer_appreciations"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    badge_name = Column(String(50), nullable=False)  # "Team Player", "Problem Solver", "Innovator", "Rockstar"
    message = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    sender = relationship("User", foreign_keys=[sender_id])
    recipient = relationship("User", foreign_keys=[recipient_id])
