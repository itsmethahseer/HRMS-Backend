from pydantic import BaseModel, EmailStr
from typing import Optional

class LoginRequest(BaseModel):
    company_name: str
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    schema_name: str
    user_id: int
    email: str
    first_name: str
    last_name: str
    is_superuser: bool
