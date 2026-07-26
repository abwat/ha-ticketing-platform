#!/usr/bin/env python3
"""Prints the Kafka/Redpanda event contract used by the local stack."""

from __future__ import annotations

import json


def main() -> None:
    event_contract = {
        "topic": "ticket-events",
        "key": "ticket_id",
        "schema": {
            "type": "ticket.created | ticket.assigned | ticket.comment_added | ticket.sla_breached",
            "ticket_id": "uuid",
            "occurred_at": "iso-8601 timestamp",
            "details": "string map",
        },
        "local_broker": "redpanda:9092",
        "note": "The app currently uses Redis for local event storage. Redpanda is included as the Kafka-compatible target for a later publisher.",
    }
    print(json.dumps(event_contract, indent=2))


if __name__ == "__main__":
    main()
