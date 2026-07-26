from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from .events import EventBus
from .models import Priority, Ticket, TicketComment, TicketEvent, TicketStatus
from .repository import TicketRepository


ALLOWED_TRANSITIONS = {
    TicketStatus.OPEN: {TicketStatus.ASSIGNED, TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED},
    TicketStatus.ASSIGNED: {TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED},
    TicketStatus.IN_PROGRESS: {TicketStatus.RESOLVED},
    TicketStatus.RESOLVED: {TicketStatus.CLOSED},
    TicketStatus.CLOSED: set(),
}


class TicketService:
    def __init__(self, repo: TicketRepository, bus: EventBus) -> None:
        self.repo = repo
        self.bus = bus

    def create_ticket(self, title: str, description: str, priority: Priority, requester: str) -> Ticket:
        if not title.strip():
            raise ValueError("title is required")
        if not requester.strip():
            raise ValueError("requester is required")
        ticket = self.repo.save(Ticket.create(title, description, priority, requester))
        self.bus.publish(TicketEvent(type="ticket.created", ticket_id=ticket.id))
        return ticket

    def assign_ticket(self, ticket_id: str, assignee: str) -> Ticket:
        ticket = self._required(ticket_id)
        if not assignee.strip():
            raise ValueError("assignee is required")
        updated = replace(
            ticket,
            assignee=assignee.strip(),
            status=TicketStatus.ASSIGNED,
            updated_at=datetime.now(timezone.utc),
        )
        self.repo.save(updated)
        self.bus.publish(
            TicketEvent(
                type="ticket.assigned",
                ticket_id=ticket_id,
                details={"assignee": assignee.strip()},
            )
        )
        return updated

    def transition(self, ticket_id: str, status: TicketStatus) -> Ticket:
        ticket = self._required(ticket_id)
        if status not in ALLOWED_TRANSITIONS[ticket.status]:
            raise ValueError(f"cannot transition from {ticket.status.value} to {status.value}")
        updated = replace(ticket, status=status, updated_at=datetime.now(timezone.utc))
        self.repo.save(updated)
        self.bus.publish(TicketEvent(type=f"ticket.{status.value}", ticket_id=ticket_id))
        return updated

    def add_comment(self, ticket_id: str, author: str, body: str) -> TicketComment:
        self._required(ticket_id)
        if not author.strip():
            raise ValueError("author is required")
        if not body.strip():
            raise ValueError("comment body is required")
        comment = self.repo.add_comment(TicketComment.create(ticket_id, author, body))
        self.bus.publish(TicketEvent(type="ticket.comment_added", ticket_id=ticket_id))
        return comment

    def overdue_tickets(self) -> list[Ticket]:
        now = datetime.now(timezone.utc)
        return [
            ticket
            for ticket in self.repo.list()
            if ticket.status not in {TicketStatus.RESOLVED, TicketStatus.CLOSED}
            and ticket.due_at < now
        ]

    def publish_sla_breaches(self) -> int:
        count = 0
        for ticket in self.overdue_tickets():
            self.bus.publish(TicketEvent(type="ticket.sla_breached", ticket_id=ticket.id))
            count += 1
        return count

    def _required(self, ticket_id: str) -> Ticket:
        ticket = self.repo.get(ticket_id)
        if not ticket:
            raise LookupError(f"ticket {ticket_id} not found")
        return ticket
