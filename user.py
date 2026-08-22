from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.models.user import UserRole


class UserCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100, examples=["John Doe"])
    email: EmailStr = Field(..., examples=["john@example.com"])
    password: str = Field(..., min_length=8, max_length=128, examples=["strongpassword123"])
    role: UserRole = Field(default=UserRole.member)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v

    @field_validator("role")
    @classmethod
    def public_registration_role(cls, v: UserRole) -> UserRole:
        if v != UserRole.member:
            raise ValueError("Public registration can only create member accounts")
        return v


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None


class UserAdminUpdate(UserUpdate):
    """Extended update schema for admins (can change role)."""
    role: Optional[UserRole] = None


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UserPublicResponse(BaseModel):
    """Limited user info for non-admin consumers."""
    id: int
    full_name: str
    email: str
    role: UserRole

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., examples=["john@example.com"])
    password: str = Field(..., examples=["strongpassword123"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPublicResponse


class UserFilter(BaseModel):
    """Query filters for listing users."""
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    search: Optional[str] = Field(None, description="Search by name or email")
