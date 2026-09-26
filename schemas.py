from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

TicketPriority = Literal["low", "medium", "high"]
TicketStatus = Literal["open", "in_progress", "resolved", "closed"]


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=5, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: str
    is_active: bool


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class TicketCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=3)
    priority: TicketPriority = "medium"


class TicketUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=3,
        max_length=200,
    )
    description: str | None = Field(default=None, min_length=3)
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    assigned_to_id: int | None = Field(default=None, gt=0)

    @field_validator(
        "title",
        "description",
        "status",
        "priority",
        mode="before",
    )
    @classmethod
    def reject_explicit_null(cls, value):
        # Omitted fields stay unchanged; explicit null is rejected.
        if value is None:
            raise ValueError("This field cannot be null")
        return value


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    status: str
    priority: str
    created_by_id: int
    assigned_to_id: int | None
    created_at: datetime
    updated_at: datetime | None


class CommentCreate(BaseModel):
    body: str = Field(min_length=1)


class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    body: str
    ticket_id: int
    author_id: int
    created_at: datetime