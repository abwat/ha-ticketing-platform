from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Response

from .events import build_event_bus
from .models import TicketStatus
from .observability import configure_observability
from .repository import build_repository
from .schemas import (
    CommentCreate,
    CommentResponse,
    HealthResponse,
    TicketAssign,
    TicketCreate,
    TicketResponse,
    TicketTransition,
)
from .service import TicketService


def build_app() -> FastAPI:
    db_path = os.getenv("TICKETING_DB", "ticketing.sqlite")
    repo = build_repository(os.getenv("DATABASE_URL"), db_path)
    bus = build_event_bus(os.getenv("REDIS_URL"))
    service = TicketService(repo, bus)

    app = FastAPI(title="HA Ticketing Platform", version="0.1.0")
    app.state.repo = repo
    app.state.bus = bus
    app.state.service = service
    configure_observability(app, "ha-ticketing-platform")

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            dependencies={"api": "ok"},
            pending_events=bus.pending_count(),
        )

    @app.get("/ready", response_model=HealthResponse)
    def ready() -> HealthResponse:
        try:
            if not os.getenv("DATABASE_URL"):
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            repo.list()
            db_status = "ok"
            status = "ready"
        except Exception:
            db_status = "failed"
            status = "degraded"
        return HealthResponse(
            status=status,
            dependencies={"database": db_status, "event_bus": "ok"},
            pending_events=bus.pending_count(),
        )

    @app.post("/tickets", response_model=TicketResponse, status_code=201)
    def create_ticket(payload: TicketCreate) -> TicketResponse:
        try:
            return TicketResponse.model_validate(
                service.create_ticket(
                    payload.title,
                    payload.description,
                    payload.priority,
                    payload.requester,
                ).__dict__
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/tickets", response_model=list[TicketResponse])
    def list_tickets(status: TicketStatus | None = Query(default=None)) -> list[TicketResponse]:
        return [TicketResponse.model_validate(ticket.__dict__) for ticket in repo.list(status)]

    @app.get("/tickets/{ticket_id}", response_model=TicketResponse)
    def get_ticket(ticket_id: str) -> TicketResponse:
        ticket = repo.get(ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail="ticket not found")
        return TicketResponse.model_validate(ticket.__dict__)

    @app.post("/tickets/{ticket_id}/assign", response_model=TicketResponse)
    def assign_ticket(ticket_id: str, payload: TicketAssign) -> TicketResponse:
        try:
            return TicketResponse.model_validate(
                service.assign_ticket(ticket_id, payload.assignee).__dict__
            )
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/tickets/{ticket_id}/transition", response_model=TicketResponse)
    def transition_ticket(ticket_id: str, payload: TicketTransition) -> TicketResponse:
        try:
            return TicketResponse.model_validate(
                service.transition(ticket_id, payload.status).__dict__
            )
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/tickets/{ticket_id}/comments", response_model=CommentResponse, status_code=201)
    def add_comment(ticket_id: str, payload: CommentCreate) -> CommentResponse:
        try:
            return CommentResponse.model_validate(
                service.add_comment(ticket_id, payload.author, payload.body).__dict__
            )
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/tickets/{ticket_id}/comments", response_model=list[CommentResponse])
    def list_comments(ticket_id: str) -> list[CommentResponse]:
        if not repo.get(ticket_id):
            raise HTTPException(status_code=404, detail="ticket not found")
        return [
            CommentResponse.model_validate(comment.__dict__)
            for comment in repo.list_comments(ticket_id)
        ]

    @app.post("/events/drain")
    def drain_events() -> dict[str, int]:
        drained = bus.drain()
        return {"processed": len(drained), "pending": bus.pending_count()}

    @app.get("/slo/overdue", response_model=list[TicketResponse])
    def overdue() -> list[TicketResponse]:
        return [TicketResponse.model_validate(ticket.__dict__) for ticket in service.overdue_tickets()]

    @app.post("/slo/scan")
    def scan_slos() -> dict[str, int]:
        return {"sla_breach_events": service.publish_sla_breaches()}

    @app.get("/metrics")
    def metrics() -> Response:
        tickets = repo.list()
        by_status = {status.value: 0 for status in TicketStatus}
        for ticket in tickets:
            by_status[ticket.status.value] += 1
        lines = [
            "# HELP ticketing_tickets_total Total tickets by status.",
            "# TYPE ticketing_tickets_total gauge",
        ]
        lines.extend(
            f'ticketing_tickets_total{{status="{status}"}} {count}'
            for status, count in by_status.items()
        )
        lines.extend(
            [
                "# HELP ticketing_pending_events Pending in-process events.",
                "# TYPE ticketing_pending_events gauge",
                f"ticketing_pending_events {bus.pending_count()}",
                "# HELP ticketing_overdue_tickets Tickets past SLA due time.",
                "# TYPE ticketing_overdue_tickets gauge",
                f"ticketing_overdue_tickets {len(service.overdue_tickets())}",
            ]
        )
        return Response("\n".join(lines) + "\n", media_type="text/plain")

    return app


app = build_app()
