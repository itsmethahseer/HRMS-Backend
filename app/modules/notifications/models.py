import enum
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base


class NotificationTypeEnum(str, enum.Enum):
    leave = "leave"
    attendance = "attendance"
    payroll = "payroll"
    expense = "expense"
    recruitment = "recruitment"
    helpdesk = "helpdesk"
    performance = "performance"
    announcement = "announcement"
    system = "system"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(SAEnum(NotificationTypeEnum, name="notificationtypeenum", create_type=False), default=NotificationTypeEnum.system)

    is_read = Column(Boolean, default=False)
    link = Column(String, nullable=True)  # Frontend route to navigate to

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    recipient = relationship("User", foreign_keys=[recipient_id])
    sender = relationship("User", foreign_keys=[sender_id])
