from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from app.modules.helpdesk.models import TicketPriorityEnum, TicketStatusEnum, AnnouncementPriorityEnum


# --- TicketCategory Schemas ---
class TicketCategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    default_assignee_id: Optional[int] = None
    is_active: Optional[bool] = True


class TicketCategoryCreate(TicketCategoryBase):
    pass


class TicketCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    default_assignee_id: Optional[int] = None
    is_active: Optional[bool] = None


class TicketCategoryOut(TicketCategoryBase):
    id: int

    class Config:
        from_attributes = True


# --- TicketComment Schemas ---
class TicketCommentBase(BaseModel):
    message: str
    attachment_url: Optional[str] = None
    is_internal: Optional[bool] = False


class TicketCommentCreate(TicketCommentBase):
    pass


class TicketCommentOut(TicketCommentBase):
    id: int
    ticket_id: int
    user_id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- HelpdeskTicket Schemas ---
class HelpdeskTicketBase(BaseModel):
    category_id: int
    priority: Optional[TicketPriorityEnum] = TicketPriorityEnum.medium
    subject: str
    description: str
    attachment_url: Optional[str] = None


class HelpdeskTicketCreate(HelpdeskTicketBase):
    pass


class HelpdeskTicketUpdate(BaseModel):
    category_id: Optional[int] = None
    priority: Optional[TicketPriorityEnum] = None
    subject: Optional[str] = None
    description: Optional[str] = None
    attachment_url: Optional[str] = None
    status: Optional[TicketStatusEnum] = None
    assigned_to: Optional[int] = None
    resolution_notes: Optional[str] = None


class HelpdeskTicketResolve(BaseModel):
    resolution_notes: str
    status: Optional[TicketStatusEnum] = TicketStatusEnum.resolved


class HelpdeskTicketOut(HelpdeskTicketBase):
    id: int
    ticket_number: str
    employee_id: int
    status: TicketStatusEnum
    assigned_to: Optional[int] = None
    resolution_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    category: Optional[TicketCategoryOut] = None
    comments: List[TicketCommentOut] = []

    class Config:
        from_attributes = True


# --- Company Announcement Schemas ---
class CompanyAnnouncementBase(BaseModel):
    title: str
    content: str
    priority: Optional[AnnouncementPriorityEnum] = AnnouncementPriorityEnum.normal
    valid_until: Optional[date] = None
    is_active: Optional[bool] = True


class CompanyAnnouncementCreate(CompanyAnnouncementBase):
    pass


class CompanyAnnouncementUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    priority: Optional[AnnouncementPriorityEnum] = None
    valid_until: Optional[date] = None
    is_active: Optional[bool] = None


class CompanyAnnouncementOut(CompanyAnnouncementBase):
    id: int
    author_id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Pulse Survey Schemas ---
class PulseSurveyBase(BaseModel):
    title: str
    description: Optional[str] = None
    questions_json: str
    start_date: date
    end_date: date
    is_anonymous: Optional[bool] = True
    is_active: Optional[bool] = True


class PulseSurveyCreate(PulseSurveyBase):
    pass


class PulseSurveyUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    questions_json: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_anonymous: Optional[bool] = None
    is_active: Optional[bool] = None


class PulseSurveyOut(PulseSurveyBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SurveyResponseCreate(BaseModel):
    survey_id: int
    answers_json: str


class SurveyResponseOut(BaseModel):
    id: int
    survey_id: int
    employee_id: Optional[int] = None
    answers_json: str
    submitted_at: Optional[datetime] = None

    class Config:
        from_attributes = True
