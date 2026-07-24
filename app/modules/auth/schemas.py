from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    company_name: str
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    schema_name: str
