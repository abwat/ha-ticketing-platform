from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from uuid import uuid4


class TicketStatus(str, Enum):
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


SLA_BY_PRIORITY = {
    Priority.LOW: timedelta(hours=72),
    Priority.MEDIUM: timedelta(hours=24),
    Priority.HIGH: timedelta(hours=8),
    Priority.CRITICAL: timedelta(hours=1),
}


@dataclass(frozen=True)
class Ticket:
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

    @classmethod
    def create(
        cls,
        title: str,
        description: str,
        priority: Priority,
        requester: str,
    ) -> "Ticket":
        now = datetime.now(timezone.utc)
        return cls(
            id=str(uuid4()),
            title=title.strip(),
            description=description.strip(),
            priority=priority,
            status=TicketStatus.OPEN,
            requester=requester.strip(),
            assignee=None,
            created_at=now,
            updated_at=now,
            due_at=now + SLA_BY_PRIORITY[priority],
        )


@dataclass(frozen=True)
class TicketComment:
    id: str
    ticket_id: str
    author: str
    body: str
    created_at: datetime

    @classmethod
    def create(cls, ticket_id: str, author: str, body: str) -> "TicketComment":
        return cls(
            id=str(uuid4()),
            ticket_id=ticket_id,
            author=author.strip(),
            body=body.strip(),
            created_at=datetime.now(timezone.utc),
        )


@dataclass(frozen=True)
class TicketEvent:
    type: str
    ticket_id: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: dict[str, str] = field(default_factory=dict)
