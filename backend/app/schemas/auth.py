from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str = Field(min_length=8, max_length=512)
    password: str = Field(min_length=6, max_length=128)


class RefreshIn(BaseModel):
    refresh_token: str


class UserMeOut(BaseModel):
    id: str
    email: EmailStr
    is_admin: bool
