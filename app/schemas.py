"""
Pydantic request/response schemas for auth, canvas, and admin endpoints.
"""

import re
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

_PASSWORD_PATTERN = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]).{10,}$"
)

PASSWORD_RULES = (
    "Password must be at least 10 characters and include uppercase, "
    "lowercase, digit, and special character."
)


class RegisterRequest(BaseModel):
    email: EmailStr
    display_name: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=10, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        if not _PASSWORD_PATTERN.match(v):
            raise ValueError(PASSWORD_RULES)
        return v

    @field_validator("display_name")
    @classmethod
    def sanitize_display_name(cls, v: str) -> str:
        return v.strip()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class AuthResponse(BaseModel):
    token: str
    user: "UserPublic"
    must_change_password: bool = False


class UserPublic(BaseModel):
    id: UUID
    email: str
    display_name: str
    status: str
    is_admin: bool
    must_change_password: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Canvas
# ---------------------------------------------------------------------------

class CanvasSaveRequest(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    job_description: Optional[str] = Field(default=None, max_length=5000)
    pain_points: Optional[List[str]] = None
    gain_points: Optional[List[str]] = None
    wizard_step: Optional[int] = Field(default=None, ge=0, le=4)
    job_validated: Optional[bool] = None
    pains_validated: Optional[bool] = None
    gains_validated: Optional[bool] = None


class CanvasResponse(BaseModel):
    id: UUID
    title: str
    job_description: str
    pain_points: List[str]
    gain_points: List[str]
    wizard_step: int
    job_validated: bool
    pains_validated: bool
    gains_validated: bool
    is_current: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CanvasListResponse(BaseModel):
    canvases: List[CanvasResponse]


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

class AdminUserListItem(BaseModel):
    id: UUID
    email: str
    display_name: str
    status: str
    is_admin: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None
    canvas_count: int = 0

    model_config = {"from_attributes": True}


class AdminUserDetail(AdminUserListItem):
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    must_change_password: bool = False


class StatusUpdateRequest(BaseModel):
    status: str = Field(..., pattern=r"^(active|paused|declined)$")


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=10, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        if not _PASSWORD_PATTERN.match(v):
            raise ValueError(PASSWORD_RULES)
        return v


class AdminResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=10, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        if not _PASSWORD_PATTERN.match(v):
            raise ValueError(PASSWORD_RULES)
        return v


class AdminStatsResponse(BaseModel):
    total_users: int
    pending_users: int
    active_users: int
    paused_users: int
    declined_users: int
    total_canvases: int
