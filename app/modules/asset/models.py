import enum
from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey,
    DateTime, Date, Float, Text, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base


class AssetStatusEnum(str, enum.Enum):
    available = "available"
    assigned = "assigned"
    maintenance = "maintenance"
    retired = "retired"


class AssetCategory(Base):
    __tablename__ = "asset_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)  # Laptop, Monitor, Phone, Peripheral, Furniture
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    assets = relationship("Asset", back_populates="category", cascade="all, delete-orphan")


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    asset_code = Column(String(50), unique=True, index=True, nullable=False)  # e.g. AST-0012
    name = Column(String, nullable=False)                                      # MacBook Pro M2 16"
    category_id = Column(Integer, ForeignKey("asset_categories.id"), nullable=False, index=True)

    serial_number = Column(String(100), unique=True, nullable=True)
    model_number = Column(String(100), nullable=True)
    purchase_date = Column(Date, nullable=True)
    purchase_cost = Column(Float, default=0.0)
    warranty_expiry = Column(Date, nullable=True)

    status = Column(SAEnum(AssetStatusEnum, name="assetstatusenum", create_type=False), default=AssetStatusEnum.available)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    category = relationship("AssetCategory", back_populates="assets")
    assignments = relationship("AssetAssignment", back_populates="asset", cascade="all, delete-orphan")


class AssetAssignment(Base):
    __tablename__ = "asset_assignments"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    assigned_date = Column(Date, nullable=False)
    return_date = Column(Date, nullable=True)
    condition_on_assignment = Column(String, default="New / Good")
    condition_on_return = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    is_returned = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    asset = relationship("Asset", back_populates="assignments")
    employee = relationship("User", foreign_keys=[employee_id])
