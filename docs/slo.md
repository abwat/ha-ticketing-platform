# SLO

## Proposed Service Objectives

- Availability: 99.9% monthly for the ticket API.
- Latency: p95 ticket creation under 250 ms during normal operating load.
- Durability: no acknowledged ticket creation should be lost.
- Recovery: service should restore readiness within 5 minutes after database recovery.

## User Journeys

- Create a ticket.
- Assign a ticket.
- Move a ticket through resolution.
- Detect overdue tickets for operational escalation.

## Error Budget Thinking

The highest-risk dependencies are the primary database and event processor. API availability without persistence is not useful for ticket creation, so readiness should fail closed when the database is unavailable.

