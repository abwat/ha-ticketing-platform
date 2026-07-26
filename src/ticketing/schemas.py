from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from .models import Priority, TicketStatus


class TicketCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=4000)
    priority: Priority = Priority.MEDIUM
    requester: str = Field(min_length=1, max_length=120)


class TicketAssign(BaseModel):
    assignee: str = Field(min_length=1, max_length=120)


class TicketTransition(BaseModel):
    status: TicketStatus


class CommentCreate(BaseModel):
    author: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1, max_length=2000)


class CommentResponse(BaseModel):
    id: str
    ticket_id: str
    author: str
    body: str
    created_at: datetime


class TicketResponse(BaseModel):
    id: str
    title: str
    description: str
    priority: Priority
    status: TicketStatus
    requester: str
    assignee: str | None
    created_at: datetime
    updated_at: datetime
    due_at: datetime


class HealthResponse(BaseModel):
    status: str
    dependencies: dict[str, str]
    pending_events: int
