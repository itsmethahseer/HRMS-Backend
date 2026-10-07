from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class CompanyRegister(BaseModel):
    company_name: str
    admin_email: EmailStr
    admin_first_name: str
    admin_last_name: str
    admin_password: str

class TenantResponse(BaseModel):
    id: int
    company_name: str
    schema_name: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class TenantUpdate(BaseModel):
    company_name: Optional[str] = None
    is_active: Optional[bool] = None

