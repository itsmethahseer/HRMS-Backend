from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from app.modules.pms.models import (
    GoalCategoryEnum, GoalStatusEnum, ReviewCycleTypeEnum,
    ReviewCycleStatusEnum, ReviewerTypeEnum, ReviewStatusEnum, MeetingStatusEnum
)


# --- KeyResult Schemas ---
class KeyResultBase(BaseModel):
    title: str
    target_value: Optional[float] = 100.0
    current_value: Optional[float] = 0.0
    metric_unit: Optional[str] = "%"
    progress_percentage: Optional[float] = 0.0
    weightage: Optional[float] = 1.0


class KeyResultCreate(KeyResultBase):
    pass


class KeyResultUpdate(BaseModel):
    title: Optional[str] = None
    target_value: Optional[float] = None
    current_value: Optional[float] = None
    metric_unit: Optional[str] = None
    progress_percentage: Optional[float] = None
    weightage: Optional[float] = None


class KeyResultOut(KeyResultBase):
    id: int
    goal_id: int

    class Config:
        from_attributes = True


# --- Goal Schemas ---
class GoalBase(BaseModel):
    title: str
    description: Optional[str] = None
    category: Optional[GoalCategoryEnum] = GoalCategoryEnum.individual
    start_date: date
    due_date: date
    target_value: Optional[float] = 100.0
    current_value: Optional[float] = 0.0
    metric_unit: Optional[str] = "%"
    progress_percentage: Optional[float] = 0.0
    weightage: Optional[float] = 1.0
    status: Optional[GoalStatusEnum] = GoalStatusEnum.not_started


class GoalCreate(GoalBase):
    employee_id: Optional[int] = None
    key_results: Optional[List[KeyResultCreate]] = []


class GoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[GoalCategoryEnum] = None
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    target_value: Optional[float] = None
    current_value: Optional[float] = None
    metric_unit: Optional[str] = None
    progress_percentage: Optional[float] = None
    weightage: Optional[float] = None
    status: Optional[GoalStatusEnum] = None


class GoalOut(GoalBase):
    id: int
    employee_id: int
    created_at: Optional[datetime] = None
    key_results: List[KeyResultOut] = []

    class Config:
        from_attributes = True


# --- Review Cycle Schemas ---
class ReviewCycleBase(BaseModel):
    title: str
    start_date: date
    end_date: date
    review_type: Optional[ReviewCycleTypeEnum] = ReviewCycleTypeEnum.annual
    status: Optional[ReviewCycleStatusEnum] = ReviewCycleStatusEnum.draft


class ReviewCycleCreate(ReviewCycleBase):
    pass


class ReviewCycleUpdate(BaseModel):
    title: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    review_type: Optional[ReviewCycleTypeEnum] = None
    status: Optional[ReviewCycleStatusEnum] = None


class ReviewCycleOut(ReviewCycleBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Performance Review Schemas ---
class PerformanceReviewBase(BaseModel):
    cycle_id: int
    employee_id: int
    reviewer_id: int
    reviewer_type: Optional[ReviewerTypeEnum] = ReviewerTypeEnum.self_eval
    ratings_json: Optional[str] = None
    comments: Optional[str] = None
    strengths: Optional[str] = None
    areas_for_improvement: Optional[str] = None
    overall_score: Optional[float] = 0.0


class PerformanceReviewCreate(PerformanceReviewBase):
    pass


class PerformanceReviewSubmit(BaseModel):
    ratings_json: Optional[str] = None
    comments: Optional[str] = None
    strengths: Optional[str] = None
    areas_for_improvement: Optional[str] = None
    overall_score: float


class PerformanceReviewOut(PerformanceReviewBase):
    id: int
    status: ReviewStatusEnum
    submitted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- 1-on-1 Meeting Schemas ---
class OneOnOneMeetingBase(BaseModel):
    employee_id: int
    scheduled_at: datetime
    duration_minutes: Optional[int] = 30
    agenda: Optional[str] = None
    notes: Optional[str] = None
    action_items: Optional[str] = None


class OneOnOneMeetingCreate(OneOnOneMeetingBase):
    pass


class OneOnOneMeetingUpdate(BaseModel):
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    agenda: Optional[str] = None
    notes: Optional[str] = None
    action_items: Optional[str] = None
    status: Optional[MeetingStatusEnum] = None


class OneOnOneMeetingOut(OneOnOneMeetingBase):
    id: int
    manager_id: int
    status: MeetingStatusEnum
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Peer Appreciation Schemas ---
class PeerAppreciationCreate(BaseModel):
    recipient_id: int
    badge_name: str
    message: str


class PeerAppreciationOut(BaseModel):
    id: int
    sender_id: int
    recipient_id: int
    badge_name: str
    message: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
