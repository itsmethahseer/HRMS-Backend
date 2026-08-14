import enum
from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey,
    DateTime, Date, Text, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base


class TicketPriorityEnum(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class TicketStatusEnum(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"


class AnnouncementPriorityEnum(str, enum.Enum):
    normal = "normal"
    high = "high"
    urgent = "urgent"


class TicketCategory(Base):
    __tablename__ = "ticket_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)  # IT Support, HR Query, Finance/Payroll, Facilities
    description = Column(String, nullable=True)
    default_assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_active = Column(Boolean, default=True)

    default_assignee = relationship("User", foreign_keys=[default_assignee_id])


class HelpdeskTicket(Base):
    __tablename__ = "helpdesk_tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_number = Column(String(30), unique=True, index=True, nullable=False)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("ticket_categories.id"), nullable=False, index=True)

    priority = Column(SAEnum(TicketPriorityEnum, name="ticketpriorityenum", create_type=False), default=TicketPriorityEnum.medium)
    subject = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    attachment_url = Column(String, nullable=True)

    status = Column(SAEnum(TicketStatusEnum, name="ticketstatusenum", create_type=False), default=TicketStatusEnum.open)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    employee = relationship("User", foreign_keys=[employee_id])
    category = relationship("TicketCategory", foreign_keys=[category_id])
    assignee = relationship("User", foreign_keys=[assigned_to])
    comments = relationship("TicketComment", back_populates="ticket", cascade="all, delete-orphan")


class TicketComment(Base):
    __tablename__ = "ticket_comments"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("helpdesk_tickets.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    attachment_url = Column(String, nullable=True)
    is_internal = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    ticket = relationship("HelpdeskTicket", back_populates="comments")
    user = relationship("User", foreign_keys=[user_id])


class CompanyAnnouncement(Base):
    __tablename__ = "company_announcements"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    priority = Column(SAEnum(AnnouncementPriorityEnum, name="announcementpriorityenum", create_type=False), default=AnnouncementPriorityEnum.normal)
    valid_until = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    author = relationship("User", foreign_keys=[author_id])


class PulseSurvey(Base):
    __tablename__ = "pulse_surveys"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    questions_json = Column(Text, nullable=False)  # JSON array of questions
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_anonymous = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    responses = relationship("SurveyResponse", back_populates="survey", cascade="all, delete-orphan")


class SurveyResponse(Base):
    __tablename__ = "survey_responses"

    id = Column(Integer, primary_key=True, index=True)
    survey_id = Column(Integer, ForeignKey("pulse_surveys.id"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Null if anonymous
    answers_json = Column(Text, nullable=False)  # JSON dictionary of question->answer

    submitted_at = Column(DateTime(timezone=True), server_default=func.now())

    survey = relationship("PulseSurvey", back_populates="responses")
    employee = relationship("User", foreign_keys=[employee_id])
