"""
Pydantic request/response schemas for auth, canvas, and admin endpoints.
"""

import html
import re
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from .sanitization import sanitize_input


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

PASSWORD_MIN_LENGTH = 10

_PASSWORD_PATTERN = re.compile(
    rf"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{{}};':\"\\|,.<>\/?]).{{{PASSWORD_MIN_LENGTH},}}$"
)

PASSWORD_RULES = (
    f"Password must be at least {PASSWORD_MIN_LENGTH} characters and include uppercase, "
    "lowercase, digit, and special character."
)


class RegisterRequest(BaseModel):
    email: EmailStr
    display_name: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=PASSWORD_MIN_LENGTH, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        if not _PASSWORD_PATTERN.match(v):
            raise ValueError(PASSWORD_RULES)
        return v

    @field_validator("display_name")
    @classmethod
    def sanitize_display_name(cls, v: str) -> str:
        v = v.strip()
        # Must contain at least one alphanumeric character
        if not re.search(r'[a-zA-Z0-9]', v):
            raise ValueError("Display name must contain at least one alphanumeric character.")
        return sanitize_input(v)


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

    @field_validator("title")
    @classmethod
    def sanitize_title(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return sanitize_input(v.strip()) if v.strip() else v

    @field_validator("job_description")
    @classmethod
    def sanitize_job_description(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return sanitize_input(v.strip()) if v.strip() else v

    @field_validator("pain_points")
    @classmethod
    def sanitize_pain_points(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        if len(v) > 50:
            raise ValueError("Cannot have more than 50 pain points")
        result = []
        for item in v:
            if len(item) > 2000:
                raise ValueError("Each pain point must be 2000 characters or fewer")
            result.append(sanitize_input(item.strip()) if item.strip() else item)
        return result

    @field_validator("gain_points")
    @classmethod
    def sanitize_gain_points(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        if len(v) > 50:
            raise ValueError("Cannot have more than 50 gain points")
        result = []
        for item in v:
            if len(item) > 2000:
                raise ValueError("Each gain point must be 2000 characters or fewer")
            result.append(sanitize_input(item.strip()) if item.strip() else item)
        return result


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
    new_password: str = Field(..., min_length=PASSWORD_MIN_LENGTH, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        if not _PASSWORD_PATTERN.match(v):
            raise ValueError(PASSWORD_RULES)
        return v


class AdminResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=PASSWORD_MIN_LENGTH, max_length=128)

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


# ---------------------------------------------------------------------------
# Share Links
# ---------------------------------------------------------------------------

class CreateShareLinkRequest(BaseModel):
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)
    expires_in_hours: Optional[int] = Field(default=None, ge=1, le=8760)


class SharePasswordRequest(BaseModel):
    password: str = Field(..., min_length=1, max_length=128)


class ShareLinkResponse(BaseModel):
    id: UUID
    share_token: str
    has_password: bool
    created_at: datetime
    expires_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SharedCanvasResponse(BaseModel):
    title: str
    job_description: str
    pain_points: List[str]
    gain_points: List[str]
    created_at: datetime


# ---------------------------------------------------------------------------
# JSON Import / Export
# ---------------------------------------------------------------------------

class CanvasExportJSON(BaseModel):
    version: str = "1.0"
    exported_at: datetime
    title: str
    job_description: str
    pain_points: List[str]
    gain_points: List[str]



# ---------------------------------------------------------------------------
# BYOK (Bring Your Own Key)
# ---------------------------------------------------------------------------

class SaveOpenAIKeyRequest(BaseModel):
    openai_api_key: str = Field(..., min_length=20, max_length=256)

    @field_validator("openai_api_key")
    @classmethod
    def validate_key_format(cls, v: str) -> str:
        if not v.startswith("sk-"):
            raise ValueError("OpenAI API key must start with 'sk-'")
        return v


class OpenAIKeyStatusResponse(BaseModel):
    has_key: bool
    key_hint: str = ""
    key_valid: bool = False


class OpenAIKeyTestResponse(BaseModel):
    valid: bool
    message: str


class CanvasImportRequest(BaseModel):
    version: str = Field(default="1.0", pattern=r"^\d+\.\d+$")
    title: Optional[str] = Field(default="Imported Canvas", max_length=200)
    job_description: Optional[str] = Field(default="", max_length=5000)
    pain_points: Optional[List[str]] = Field(default_factory=list)
    gain_points: Optional[List[str]] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def sanitize_title(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return sanitize_input(v.strip()) if v.strip() else v

    @field_validator("job_description")
    @classmethod
    def sanitize_job_description(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return sanitize_input(v.strip()) if v.strip() else v

    @field_validator("pain_points")
    @classmethod
    def validate_pain_points(cls, v: Optional[List[str]]) -> List[str]:
        if v is None:
            return []
        if len(v) > 50:
            raise ValueError("Cannot import more than 50 pain points")
        result = []
        for item in v:
            if len(item) > 2000:
                raise ValueError("Each pain point must be 2000 characters or fewer")
            result.append(sanitize_input(item.strip()) if item.strip() else item)
        return result

    @field_validator("gain_points")
    @classmethod
    def validate_gain_points(cls, v: Optional[List[str]]) -> List[str]:
        if v is None:
            return []
        if len(v) > 50:
            raise ValueError("Cannot import more than 50 gain points")
        result = []
        for item in v:
            if len(item) > 2000:
                raise ValueError("Each gain point must be 2000 characters or fewer")
            result.append(sanitize_input(item.strip()) if item.strip() else item)
        return result
