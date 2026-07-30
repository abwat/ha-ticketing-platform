import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from ticketing.events import EventBus
from ticketing.models import Priority, TicketStatus
from ticketing.repository import TicketRepository
from ticketing.service import TicketService


class TicketServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.NamedTemporaryFile(delete=True)
        self.repo = TicketRepository(self.tmp.name)
        self.bus = EventBus()
        self.service = TicketService(self.repo, self.bus)

    def test_create_ticket_persists_and_publishes_event(self) -> None:
        ticket = self.service.create_ticket(
            "Cannot login",
            "User gets 403 from identity provider",
            Priority.HIGH,
            "sam@example.com",
        )

        saved = self.repo.get(ticket.id)
        self.assertIsNotNone(saved)
        self.assertEqual(saved.status, TicketStatus.OPEN)
        self.assertEqual(self.bus.pending_count(), 1)

    def test_assignment_updates_status(self) -> None:
        ticket = self.service.create_ticket("VPN down", "", Priority.CRITICAL, "ops")
        assigned = self.service.assign_ticket(ticket.id, "alice")

        self.assertEqual(assigned.status, TicketStatus.ASSIGNED)
        self.assertEqual(assigned.assignee, "alice")

    def test_invalid_transition_is_rejected(self) -> None:
        ticket = self.service.create_ticket("Bug", "", Priority.MEDIUM, "qa")

        with self.assertRaises(ValueError):
            self.service.transition(ticket.id, TicketStatus.CLOSED)

    def test_comments_are_persisted(self) -> None:
        ticket = self.service.create_ticket("Bug", "", Priority.MEDIUM, "qa")

        comment = self.service.add_comment(ticket.id, "alice", "Investigating logs.")

        comments = self.repo.list_comments(ticket.id)
        self.assertEqual(comments[0].id, comment.id)
        self.assertEqual(comments[0].body, "Investigating logs.")

    def test_blank_assignee_is_rejected(self) -> None:
        ticket = self.service.create_ticket("VPN down", "", Priority.CRITICAL, "ops")

        with self.assertRaises(ValueError):
            self.service.assign_ticket(ticket.id, "   ")

    def test_overdue_tickets_excludes_resolved_items(self) -> None:
        open_ticket = self.service.create_ticket("Open incident", "", Priority.HIGH, "ops")
        resolved_ticket = self.service.create_ticket("Resolved incident", "", Priority.HIGH, "ops")
        overdue_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        self.repo.save(replace(open_ticket, due_at=overdue_at))
        self.repo.save(
            replace(
                resolved_ticket,
                status=TicketStatus.RESOLVED,
                due_at=overdue_at,
            )
        )

        overdue = self.service.overdue_tickets()

        self.assertEqual([ticket.id for ticket in overdue], [open_ticket.id])


if __name__ == "__main__":
    unittest.main()
