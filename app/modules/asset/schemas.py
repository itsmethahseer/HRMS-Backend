from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from app.modules.asset.models import AssetStatusEnum


# --- Asset Category Schemas ---
class AssetCategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: Optional[bool] = True


class AssetCategoryCreate(AssetCategoryBase):
    pass


class AssetCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class AssetCategoryOut(AssetCategoryBase):
    id: int

    class Config:
        from_attributes = True


# --- Asset Schemas ---
class AssetBase(BaseModel):
    asset_code: str
    name: str
    category_id: int
    serial_number: Optional[str] = None
    model_number: Optional[str] = None
    purchase_date: Optional[date] = None
    purchase_cost: Optional[float] = 0.0
    warranty_expiry: Optional[date] = None
    status: Optional[AssetStatusEnum] = AssetStatusEnum.available


class AssetCreate(AssetBase):
    pass


class AssetUpdate(BaseModel):
    asset_code: Optional[str] = None
    name: Optional[str] = None
    category_id: Optional[int] = None
    serial_number: Optional[str] = None
    model_number: Optional[str] = None
    purchase_date: Optional[date] = None
    purchase_cost: Optional[float] = None
    warranty_expiry: Optional[date] = None
    status: Optional[AssetStatusEnum] = None


class AssetOut(AssetBase):
    id: int
    created_at: Optional[datetime] = None
    category: Optional[AssetCategoryOut] = None

    class Config:
        from_attributes = True


# --- Asset Assignment Schemas ---
class AssetAssignmentBase(BaseModel):
    asset_id: int
    employee_id: int
    assigned_date: date
    condition_on_assignment: Optional[str] = "Good"
    notes: Optional[str] = None


class AssetAssignmentCreate(AssetAssignmentBase):
    pass


class AssetReturnRequest(BaseModel):
    return_date: date
    condition_on_return: Optional[str] = "Returned in Good Condition"
    notes: Optional[str] = None


class AssetAssignmentOut(AssetAssignmentBase):
    id: int
    return_date: Optional[date] = None
    condition_on_return: Optional[str] = None
    is_returned: bool
    created_at: Optional[datetime] = None
    asset: Optional[AssetOut] = None

    class Config:
        from_attributes = True
