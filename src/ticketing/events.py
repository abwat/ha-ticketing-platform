from __future__ import annotations

from collections import deque
from dataclasses import asdict
from datetime import datetime
import json

from .models import TicketEvent


class EventBus:
    def __init__(self) -> None:
        self._events: deque[TicketEvent] = deque()
        self._audit_log: list[TicketEvent] = []

    def publish(self, event: TicketEvent) -> None:
        self._events.append(event)

    def drain(self, limit: int = 100) -> list[TicketEvent]:
        drained: list[TicketEvent] = []
        while self._events and len(drained) < limit:
            event = self._events.popleft()
            self._audit_log.append(event)
            drained.append(event)
        return drained

    def audit_log(self) -> list[TicketEvent]:
        return list(self._audit_log)

    def pending_count(self) -> int:
        return len(self._events)


class RedisEventBus(EventBus):
    def __init__(self, redis_url: str, key: str = "ticketing:events") -> None:
        import redis

        self.client = redis.Redis.from_url(redis_url, decode_responses=True)
        self.key = key
        self.audit_key = f"{key}:audit"

    def publish(self, event: TicketEvent) -> None:
        self.client.lpush(self.key, json.dumps(self._serialize(event)))

    def drain(self, limit: int = 100) -> list[TicketEvent]:
        drained: list[TicketEvent] = []
        for _ in range(limit):
            raw = self.client.rpop(self.key)
            if raw is None:
                break
            self.client.lpush(self.audit_key, raw)
            drained.append(self._deserialize(json.loads(raw)))
        return drained

    def audit_log(self) -> list[TicketEvent]:
        return [
            self._deserialize(json.loads(raw))
            for raw in self.client.lrange(self.audit_key, 0, -1)
        ]

    def pending_count(self) -> int:
        return int(self.client.llen(self.key))

    @staticmethod
    def _serialize(event: TicketEvent) -> dict[str, object]:
        payload = asdict(event)
        payload["occurred_at"] = event.occurred_at.isoformat()
        return payload

    @staticmethod
    def _deserialize(payload: dict[str, object]) -> TicketEvent:
        return TicketEvent(
            type=str(payload["type"]),
            ticket_id=str(payload["ticket_id"]),
            occurred_at=datetime.fromisoformat(str(payload["occurred_at"])),
            details=dict(payload.get("details") or {}),
        )


def build_event_bus(redis_url: str | None) -> EventBus:
    if redis_url:
        return RedisEventBus(redis_url)
    return EventBus()
